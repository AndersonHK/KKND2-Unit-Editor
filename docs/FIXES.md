# Behavior fixes

The **Fixes** tab contains four independent toggles. All default to **Off**, preserving stock KWIPv3 behavior. Each row has a name and two description lines, plus the current toggle, stock default, change from default and saved value. The shared toolbar and Undo, Redo, Revert saved, Reset defaults and Different from defaults work as on Overrides.

Save creates `fixes.cfg` beside the launchers unless another location is selected with Open, Folder or `--fixes-file`. Launch game saves and applies it with the other tabs. Files are UTF-8 JSON, atomically replaced with external-change detection and no `.bak` files. Personal settings are ignored by Git. See [the complete stock example](../examples/fixes.example.cfg). The schema is `kknd2-editor-fixes`, version 2; all four keys are required and accept only JSON `true` or `false`, not 0/1 or strings.

Version 1 files import automatically with Acquisition Range off. They are upgraded only on Save.

## Acquisition Range

Idle ground combat units try the normal firing-range search first. If no eligible target is found, they search another **96 world pixels (three tiles)**, capped by sight and the existing visibility/line-of-sight, alliance, minimum-range and weapon checks. An out-of-range acquisition now enters the native temporary pursuit state: the unit requests a path toward the target and switches to firing when it reaches the original weapon range. Actual firing range stays unchanged. Buildings and defenses keep their original search.

With damage priority enabled, classes are ranked separately inside each pass: any eligible in-range target wins before a stronger class in the extra three tiles. The original tie-breaking still applies within a pass. Existing targets and explicit attack orders are not continually replaced. This is acquisition assistance, not attack-move or a complete rewrite of pursuit. Idle acquisition uses the native staggered scan schedule and does not interrupt Move, Hold, Guard or special orders. Aircraft retain their separate native flight/order states. Firing-only scans retain their original radius so a turret cannot become stuck aiming at a target it cannot reach. Fight keeps its native sight-wide fallback, including passive buildings; the 96-pixel automatic-acquisition radius does not restrict an explicit Fight command.

## Shift build

Hold Shift **at the moment you place** a building or defense to keep the same placement action selected. Each additional placement needs another click. Placing without Shift exits normally. Right-click and the game's other cancellation paths still work; releasing Shift alone does not cancel a preview already retained.

After each accepted Shift placement, the fix calls the same native per-building count check as normal successful-placement cleanup. That check includes the newly submitted building and reads the configured cap. Reaching the cap removes its menu icon and exits placement; below the cap, the preview remains, the click edge is consumed and the original input/placement loop continues. Right-click cancellation, disabled producers, terrain and command handling remain native.

Version 0.2.0 only rechecked the menu, without performing the success-time cap check that removes its icon. That stale icon allowed repeated Shift placements above the cap. Version 0.2.1 corrects that omission and clears the active menu-item pointer after native removal, preventing cleanup from using the deleted item twice.

The native check is `0x4078B5` (calling `0x40772A`), also used by normal cleanup at `0x40A9F6`. Tests execute the original count comparison with cap 1, 4, 8 and 20 across factions and several building types. They check cap-minus-one, cap and already-over-cap states, preserved counts and safe subsequent cleanup. Network command latency and complete matches still need manual testing.

## Zero damage acts as a target filter

The game normally checks range, target identity and attack compatibility without treating zero damage as a forbidden target type. This toggle rejects unit/building targets whose class has **exactly zero raw damage** in the attacker's current weapon table. The five classes are infantry, vehicles, beasts, buildings and aircraft. Destructible map-wall targets use building damage.

The rule applies to automatic acquisition, Fight (F), manual attack orders and the attack cursor. Hovering a unit/building shows the unavailable cursor when no selected armed unit can damage it, and clicking does not enqueue that attack. In a mixed selection, capable units can accept the order while zero-damage recipients reject it individually. The separate native pursuit-compatibility check also rejects zero-damage targets, so an out-of-range invalid target does not become a reason to walk toward it. Explicit attack-ground, repair/transport orders and other special actions retain their native behavior. Units with no ordinary weapon table retain their special simulation behavior; unarmed support units alone do not enable the attack cursor.

Fight had two paths missing from the initial fix: a last-resort whole-unit-list search which bypassed the firing validator, and callers that inspected a failed search's output buffer rather than its return value. All wrapped failed searches now clear that buffer. Fight's fallback filters candidates individually, retains native distance selection among eligible candidates, and checks attack compatibility and visibility. Fight may pursue eligible targets within its native sight search regardless of Acquisition Range. Its broad fallback is retained because the nearby scanner deliberately skips many passive buildings. Zero-damage, compatibility and visibility filtering still apply to that fallback.

This is based on the **raw damage field**, not damage after armor, splash, health, damage-per-second or other combat effects. A positive raw value remains eligible even if it would be ineffective after those effects.

## Prioritize target types by damage

During automatic acquisition, search target classes in descending order of the attacker's current raw weapon damage. With infantry 10, vehicles 20 and beasts 30, an eligible beast wins over vehicles and infantry. If no eligible beast exists, try vehicles, then infantry. Buildings and aircraft participate according to their own damage values. Equal-damage classes are considered together using the game's existing selection rules.

The nearby, broader and Fight fallback selectors are wrapped. Each pass keeps the original range, minimum range, visibility, alliance and attack-compatibility checks. A more damaging class outside the native valid range does not win over a valid target in range. The original broader selector searches ground targets; this fix does not add aircraft to that selector. The nearby selector retains its ground/air scanning capability. Turret weapons use their own damage table, and values are read from the running game after the selected UCONFIG has loaded.

An explicit target order is not replaced by this ranking. Existing targets are not continually interrupted simply because another target enters range; ranking applies when the game acquires a target. Damage priority alone does not expand the acquisition radius or rewrite Fight mode movement; enable Acquisition Range separately for the extra three tiles. Enable the zero-damage toggle too if zero-damage types must be excluded entirely; priority alone leaves them as the last available class.

Targeting fixes affect **every player, including AI**. Network participants need the same gameplay settings/module. Multiplayer, save/load and sustained large-army gameplay still need manual testing.

## Native implementation

The launcher still patches only its own freshly created, suspended process. No executable on disk changes. Starting KWIPv3 outside this launcher uses the original behavior. The supported SHA-256 is the same as the other launch features:

`ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44`

Business rules live in [native/fixes.cpp](../native/fixes.cpp), with the verified unit/weapon layout in [native/kwip_abi.h](../native/kwip_abi.h). This is compiled x86 C++, with no CRT, imports, entry point, heap allocations, background thread or Python polling. The build creates a small DLL in a temporary folder and extracts its sections, exports and relocations into the shipped `fixes_native.json`. The launcher maps that constrained artifact; it does not implement a general-purpose DLL loader or require a compiler on a player's machine. Code pages become read/execute; mutable context stays read/write and non-executable.

| Hook | Verified address | Bridge |
| --- | --- | --- |
| Ground idle acquisition | `0x4CC43E` | Six-byte prologue; staggered acquisition hands the target to native temporary pursuit `0x4CE727`, whose update `0x4CE7C6` requests pathfinding and transitions to firing |
| Temporary pursuit / path result | `0x4CE7C6`, `0x4CEC3E` | Typed wrappers retain native path/fire logic and return orderless idle units safely after a lost target or failed path |
| Nearby target selector | `0x4A1893` | Nine-byte whole-instruction prologue; fastcall unit/target |
| Broader ground target selector | `0x4A2039` | Six-byte whole-instruction prologue; fastcall unit/target |
| Shared target validator | `0x4A265E` | Nine-byte prologue; fastcall plus two callee-cleaned stack arguments |
| Fight fallback selector | `0x4A2455` | Six-byte prologue; fastcall unit/target |
| Fight fallback candidate | `0x4A24C1` | Replace the verified alliance call; retain alliance, filter damage class and check visibility/compatibility |
| Pursuit compatibility | `0x4A9B40` | Six-byte prologue; fastcall unit/target; false rejects pursuit |
| Cursor selection | `0x461A90` | Six-byte prologue; fastcall controller/cursor |
| Manual object order | `0x46319E` | Six-byte prologue; fastcall controller/command plus target stack argument |
| Per-recipient command delivery | `0x45BC10` | Six-byte prologue; filter only attack command 6 inside unit group event `0x30` |
| Accepted building placement | `0x466D01` | Six-byte pending-command store; preserve registers/flags and return to `0x46677E` only with Shift held and below the instance cap |

`fixes_patch.py` is the small version-specific bridge. Every enabled hook is checked against original bytes **before any feature writes process memory**. Copied prologues contain no relative instructions. Entry hooks call typed C++ functions; the placement mid-function adapter preserves the original store and CPU state. The Shift flag is `0x10` in the game's modifier snapshot at `0x565438`: the native key mapping connects scan code `0x2A` to that flag. The input loop refreshes this snapshot, so the fix needs no OS keyboard polling.

Priority uses at most five native scans, one per distinct damage value, and stops on the first successful class group. Equal damage classes cost one scan together. Filtering uses a stack-scoped context restored after the synchronous native selector returns; these routines do not yield. No Python scan, persistent unit-pointer cache or separate target-list allocation is introduced. The cursor checks selected units in the native unit list and stops at the first capable attacker; Fight retains its existing native list traversal. Large-army performance is a manual-test item.

## Rebuilding and testing

Use MSVC's **x86 Native Tools Command Prompt** (Visual Studio Build Tools 2017 or later):

```powershell
python native/build.py
```

Alternatively pass `--compiler` with the path to an x86-targeting `cl.exe`; `link.exe` must be beside it. The module needs no Windows SDK headers or libraries. Compilation treats warnings as errors. Commit the source and regenerated JSON together when a change is ready; a test verifies their source digest. Build intermediates are temporary, and ordinary `.dll`, `.obj`, `.lib`, `.exp` and `.pdb` files stay ignored.

The normal suite covers schema/type rejection, defaults, undo/redo, atomic saves without backups, external edits, shared toolbar/toggle UI, source/payload consistency and refusal before writes. Optional `unicorn` and `pefile` tests with `KKND2_TEST_EXE` execute the compiled module and original selector/validator instructions in synthetic worlds. Tests cover live damage values, turret weapons, independent toggle combinations, all five damage classes, equal-value ties, range/minimum range, alliances, hidden targets, stale generation IDs, manual cursor/click agreement, mixed-group delivery, native pursuit cancellation, Fight fallback/failed-search output, real passive-building flags, idle-to-pathfinding-to-firing transitions, and Shift adapter register/flag/stack preservation and availability rechecks. These are not full gameplay tests.

For a manual match, test mixed infantry/vehicle/beast formations with different damage values, a zero-damage target outside range, explicit orders, turret/anti-air units, and repeated Shift placement through a building limit. Try right-click cancellation and releasing Shift before the next placement. Check a large battle before treating the new targeting policy as final.

The same compiled payload also supplies the two AI income-building ceiling comparisons described in [Buildings and campaign](BUILDINGS_AND_CAMPAIGN.md). Those follow Building Limits and are independent of the four Fixes toggles.
