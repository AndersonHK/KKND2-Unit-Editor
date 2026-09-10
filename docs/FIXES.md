# Behavior fixes

The **Fixes** tab contains three independent toggles. All default to **Off**, preserving stock KWIPv3 behavior. Each row has a name and two description lines, plus the current toggle, stock default, change from default and saved value. The shared toolbar and Undo, Redo, Revert saved, Reset defaults and Different from defaults work as on Overrides.

Save creates `fixes.cfg` beside the launchers unless another location is selected with Open, Folder or `--fixes-file`. Launch game saves and applies it with the other tabs. Files are UTF-8 JSON, atomically replaced with external-change detection and no `.bak` files. Personal settings are ignored by Git. See [the complete stock example](../examples/fixes.example.cfg). The schema is `kknd2-editor-fixes`, version 1; all three keys are required and accept only JSON `true` or `false`, not 0/1 or strings.

## Shift build

Hold Shift **at the moment you place** a building or defense to keep the same placement action selected. Each additional placement needs another click. Placing without Shift exits normally. Right-click and the game's other cancellation paths still work; releasing Shift alone does not cancel a preview already retained.

After each accepted placement, the fix retains the placement loop instead of discarding its preview. It consumes the click edge, updates input and lets the original loop recheck the production menu and placement rules. If the building disappears from the available menu or the production category becomes disabled, the loop exits normally. Terrain, funds, ownership, building instance limits and pending-command limits remain native checks. This does not create free buildings or an automatic construction queue.

## Zero damage acts as a target filter

The game normally checks range, target identity and attack compatibility without treating zero damage as a forbidden target type. This toggle rejects unit/building targets whose class has **exactly zero raw damage** in the attacker's current weapon table. The five classes are infantry, vehicles, beasts, buildings and aircraft. Destructible map-wall targets use building damage.

The rule applies to the shared attack validator, including automatic acquisition and checks on explicitly ordered attacks. An out-of-range zero-damage target is rejected as invalid rather than remaining a reason to pursue. The fix does not change the command cursor or suppress the initial click/order animation. Explicit attack-ground and other special coordinate actions retain their native behavior. Units with no ordinary weapon table retain their special behavior rather than receiving invented damage values.

This is based on the **raw damage field**, not damage after armor, splash, health, damage-per-second or other combat effects. A positive raw value remains eligible even if it would be ineffective after those effects.

## Prioritize target types by damage

During automatic acquisition, search target classes in descending order of the attacker's current raw weapon damage. With infantry 10, vehicles 20 and beasts 30, an eligible beast wins over vehicles and infantry. If no eligible beast exists, try vehicles, then infantry. Buildings and aircraft participate according to their own damage values. Equal-damage classes are considered together using the game's existing selection rules.

Both the nearby and broader native selectors are wrapped. Each pass keeps the original range, minimum range, visibility, alliance and attack-compatibility checks. A more damaging class outside the native valid range does not win over a valid target in range. The original broader selector searches ground targets; this fix does not add aircraft to that selector. The nearby selector retains its ground/air scanning capability. Turret weapons use their own damage table, and values are read from the running game after the selected UCONFIG has loaded.

An explicit target order is not replaced by this ranking. Existing targets are not continually interrupted simply because another target enters range; ranking applies when the game acquires a target. This is not attack-move, an expanded acquisition radius, or a rewrite of Fight mode's movement logic. Enable the zero-damage toggle too if zero-damage types must be excluded entirely; priority alone leaves them as the last available class.

Targeting fixes affect **every player, including AI**. Network participants need the same gameplay settings/module. Multiplayer, save/load and sustained large-army gameplay still need manual testing.

## Native implementation

The launcher still patches only its own freshly created, suspended process. No executable on disk changes. Starting KWIPv3 outside this launcher uses the original behavior. The supported SHA-256 is the same as the other launch features:

`ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44`

Business rules live in [native/fixes.cpp](../native/fixes.cpp), with the verified unit/weapon layout in [native/kwip_abi.h](../native/kwip_abi.h). This is compiled x86 C++, with no CRT, imports, entry point, heap allocations, background thread or Python polling. The build creates a small DLL in a temporary folder and extracts its sections, exports and relocations into the shipped `fixes_native.json`. The launcher maps that constrained artifact; it does not implement a general-purpose DLL loader or require a compiler on a player's machine. Code pages become read/execute; mutable context stays read/write and non-executable.

| Hook | Verified address | Bridge |
| --- | --- | --- |
| Nearby target selector | `0x4A1893` | Nine-byte whole-instruction prologue; fastcall unit/target |
| Broader ground target selector | `0x4A2039` | Six-byte whole-instruction prologue; fastcall unit/target |
| Shared target validator | `0x4A265E` | Nine-byte prologue; fastcall plus two callee-cleaned stack arguments |
| Accepted building placement | `0x466D01` | Six-byte pending-command store; preserve registers/flags and return to `0x46677E` only with Shift held |

`fixes_patch.py` is the small version-specific bridge. Every enabled hook is checked against original bytes **before any feature writes process memory**. Copied prologues contain no relative instructions. Entry hooks call typed C++ functions; the sole mid-function adapter preserves the original store and CPU state. The Shift flag is `0x10` in the game's modifier snapshot at `0x565438`: the native key mapping connects scan code `0x2A` to that flag. The input loop refreshes this snapshot, so the fix needs no OS keyboard polling.

Priority uses at most five native scans, one per distinct damage value, and stops on the first successful class group. Equal damage classes cost one scan together. Filtering uses a stack-scoped context restored after the synchronous native selector returns; these routines do not yield. No full-world Python scan, persistent unit-pointer cache or separate target-list allocation is introduced. Large-army performance is a manual-test item.

## Rebuilding and testing

Use MSVC's **x86 Native Tools Command Prompt** (Visual Studio Build Tools 2017 or later):

```powershell
python native/build.py
```

Alternatively pass `--compiler` with the path to an x86-targeting `cl.exe`; `link.exe` must be beside it. The module needs no Windows SDK headers or libraries. Compilation treats warnings as errors. Commit the source and regenerated JSON together when a change is ready; a test verifies their source digest. Build intermediates are temporary, and ordinary `.dll`, `.obj`, `.lib`, `.exp` and `.pdb` files stay ignored.

The normal suite covers schema/type rejection, defaults, undo/redo, atomic saves without backups, external edits, shared toolbar/toggle UI, source/payload consistency and refusal before writes. Optional `unicorn` and `pefile` tests with `KKND2_TEST_EXE` execute the compiled module and original selector/validator instructions in synthetic worlds. Tests cover live damage values, turret weapons, independent toggle combinations, all five damage classes, equal-value ties, range/minimum range, alliances, hidden targets, stale generation IDs, and Shift adapter register/flag/stack preservation and availability rechecks. These are not full gameplay tests.

For a manual match, test mixed infantry/vehicle/beast formations with different damage values, a zero-damage target outside range, explicit orders, turret/anti-air units, and repeated Shift placement through a building limit. Try right-click cancellation and releasing Shift before the next placement. Check a large battle before treating the new targeting policy as final.
