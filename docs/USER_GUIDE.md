# KKND2 Unit Editor

A small Windows GUI for editing **KKND2: Krossfire** unit configurations without damaging their mixed text encodings. It also offers per-building instance limits, raw research/oil/placement overrides, projectile speeds and expiration, faction-specific tech unlock levels, and opt-in targeting/Shift-build fixes for one verified **KWIPv3** executable, applied when launching the game.

The editor uses Python and Tkinter, with no third-party Python packages. It includes English names for all three factions, field limits and units, comparisons with stock defaults, undo/redo, and a layout that scales with Windows DPI and updates while resizing.

For the standalone download and short installation steps, start with the [project README](../README.md). The source checkout requires Python; the release EXE bundles it.

## Requirements

- Windows and Python **3.9 or newer**, with **Tcl/Tk and IDLE** enabled in the Python installer. For the optional VBS launcher, install the Windows Python launcher or add Python to PATH.
- Your own KKND2: Krossfire installation and its original-format `UCONFIG` files.
- **KWIPv3.exe** is required to apply the launcher's extended Burst Count, building limits, overrides, projectile settings, tech unlocks, and behavior fixes. Editing native unit configurations does not require it.
- Write access to the configuration folders and this checkout, where the editor stores its separate settings files by default.

Game executables, art, and personal configurations are not included. The embedded unit-stat baseline is a fixed reference snapshot; it is not taken from your current modded files. The UI and unit names are currently English only.

## Quick start

1. Download the repository ZIP using **Code → Download ZIP**, then extract the entire folder. Alternatively, clone the repository. Do not run files from inside the ZIP.
2. Put the extracted editor folder directly inside your KKND2 game folder for automatic discovery. Keep `src` beside the launchers.
3. Double-click **Launch Editor.pyw**. If `.pyw` files are not associated with Python, use **Launch Editor.vbs**. Both start the GUI without a command-prompt window.
4. The editor opens `UCONFIG_02.cfg` if available, otherwise the first `.cfg` in the detected `UCONFIG` folder. Check the **Configuration** selector before editing.
5. Choose a unit, enter values, and click **Save** or press **Ctrl+S**. In the game's multiplayer lobby, select that same unit configuration.

You can keep the editor anywhere. On the **Unit editor** tab, **Folder…** selects the game's `UCONFIG` folder and **Open…** opens an individual configuration. If no installation is detected, the editor opens without a unit configuration so you can select one.

Close the game's own unit editor before saving changes here, to avoid it overwriting them with an older copy.

### Alternate locations and command-line options

Run these commands from the extracted repository folder. Paths below are relative examples; replace them with your own paths as needed.

```powershell
python "Launch Editor.pyw" --help
pythonw "Launch Editor.pyw" --game-dir "..\KKND2 Krossfire"
pythonw "Launch Editor.pyw" --folder "..\KKND2 Krossfire\UCONFIG"
pythonw "Launch Editor.pyw" "..\KKND2 Krossfire\UCONFIG\UCONFIG_02.cfg"
pythonw "Launch Editor.pyw" --limits-file ".\my-limits.cfg"
pythonw "Launch Editor.pyw" --overrides-file ".\my-overrides.cfg"
pythonw "Launch Editor.pyw" --unlocks-file ".\my-unlocks.cfg"
pythonw "Launch Editor.pyw" --projectiles-file ".\my-projectiles.cfg"
pythonw "Launch Editor.pyw" --upgrades-file ".\my-upgrades.cfg"
pythonw "Launch Editor.pyw" --fixes-file ".\my-fixes.cfg"
```

`--game-dir` explicitly chooses the installation used by Launch game. Otherwise, launch uses the selected unit configuration's parent game folder, then `KKND2_GAME_DIR`, then an installation beside/containing the checkout or in the current working directory. Discovery looks for `UCONFIG` or `KWIPv3.exe`; it does not scan your drives. `--folder` chooses the configuration directory; an explicit file takes precedence for the file opened.

For a persistent location without editing source, set the Windows user environment variable **KKND2_GAME_DIR** to your game folder and restart the editor. No installation path is stored in the source. The VBS launcher tries `.venv\Scripts\pythonw.exe`, then `pyw.exe -3`, then `pythonw.exe` on PATH.

## Editing and reviewing changes

The shared top toolbar stays in the same place on all seven tabs. **Save**, **Unsaved**, **Defaults**, **Open…**, and **Folder…** act on the selected tab.

On the unit tab, search by English name or internal game ID, filter by faction, and select a unit or building. Each stat shows its stored unit and editor maximum. A `-` means the field is unavailable and cannot be edited. Title text and internal identifiers are preserved.

| Column or indicator | Meaning |
| --- | --- |
| Value | Current editable value; blue indicates an unsaved edit |
| Default | Fixed stock reference value, unaffected by saving |
| Delta | Current minus default; nonzero differences appear in gold |
| Saved | Value when the file was opened or last saved |
| `*` in the unit list | Unit has unsaved changes |
| `~` in the unit list | Unit differs from the stock baseline |

**Unsaved** reviews pending changes across the current configuration. **Defaults** reviews all differences from the baseline, including edits saved in earlier sessions. **Different from defaults** filters the list. Unknown units show `n/a` for defaults rather than an invented baseline.

**Undo / Ctrl+Z** and **Redo / Ctrl+Y** operate on edit groups. Unit edits are committed to the in-memory model when leaving a unit, reviewing, or saving. **Revert saved** discards pending edits for the selected unit, while **Reset defaults** restores that unit's reference values. On Projectiles, Revert saved and Reset defaults affect the selected projectile. On Building limits, Overrides, Tech unlocks, and Fixes these actions apply to the selected tab's entire configuration. Resetting defaults is undoable and does not save until you click Save. Switching files or closing with pending edits prompts to save, discard, or cancel. **Ctrl+F** focuses unit search.

New unit values above the displayed editor caps are rejected. These match the native editor except for **cost, extended from 5,000 to 10,000**, and **reload time, extended from 250 to 600** (nominally 10 seconds at normal speed, before firing-cycle effects). Existing out-of-range values are preserved when unrelated fields are edited; they are never silently clamped. Newly edited build times must be at least 1. See [the stat reference](STAT_REFERENCE.md) for all caps, timing/range units, and the evidence behind them. Movement speed remains a raw rate because its physical conversion has not been verified.

**Burst Count** is an additional row for supported vehicle turrets, saved in `UCONFIG_nn_ext.cfg` beside the selected preset. It has the same editing/review controls and uses a 1–127 shot range. The Anaconda's stock value is 2; its legacy Bullet Count remains 0. Click **Launch game** to apply the selected extension for that session, and relaunch to switch presets. Companions have a compatibility title header and are excluded from the configuration dropdown; open the original CFG to edit both. See [extended unit settings](UNIT_EXTENSIONS.md) for supported weapons and the versioned schema.

## Building limits

The **Building limits** tab shows 49 building records across the factions, including towers and walls, with 48 editable limits. Values count instances **per player and building type**. These settings are independent of unit statistics and do not belong in a game `UCONFIG` file.

| Building category | Editor bounds |
| --- | --- |
| Machine shops and faction equivalents | 1–4 |
| Barracks and faction equivalents | 1–7 |
| Other ordinary records, including walls | 1–100 |
| Altar of the Scourge | Original 0; read-only because of special game logic |

Production buildings retain tighter bounds because of production-menu constraints. The general maximum of 100 is an editor policy, not a proven safe engine maximum for every building or map. Building limits do not alter global unit caps or add auto-attack. Unlock requirements and tanker settings have their own tabs. Extended in-match behavior has not been exhaustively tested. Network players should use matching modifications.

Limits are stored in **building_limits.cfg** at the checkout root by default. A missing file starts with stock KWIPv3 values and is created when saved. **Open…** selects another building settings file; **Folder…** selects that folder's `building_limits.cfg`. Subsequent saves and launches use the selected file. The versioned UTF-8 JSON schema is `kknd2-editor-building-limits`, version `1`, with a `limits` mapping from internal IDs to integer values. All 49 known keys are required; unknown/duplicate keys and invalid values are rejected. [The example file](../examples/building_limits.example.cfg) contains the complete stock schema, not personal settings.

Building settings are saved using a flushed temporary file and atomic replacement, with external-change detection. They do **not** create timestamped `.bak` files. Keep a separate copy yourself if you want multiple presets.

## Overrides

The **Overrides** tab groups ten absolute raw values beneath **Research**, **Oil and Tankers**, and **Building Placement** headers, with explanations before the rows. Research has editable base cost/time and lower-tier cost/time steps. The formulas are `base + (5 − tier index) × step`; a zero step removes that surcharge. Tanker capacity counts raw oil, while loading/unloading controls replace the native integer coefficients.

Stock defaults are 250 base cost, 20 base time, steps 20 and 1, capacity 400, loading coefficient 32,768, unloading coefficient 4,096, solar-class income 7 RU/payout, thermal-class income 21 RU/payout, and building placement reach 5 tile cells. These absolute settings apply even when the game's own research options differ. The income values apply across all three factions. Placement reach 5 permits up to four clear tiles between footprints; advanced walls retain their extra allowance. These controls do not change extraction or refining yield. See [Raw engine overrides](OVERRIDES.md) for tier examples, transfer formulas, bounds, and validation details.

Settings use **overrides.cfg**, schema `kknd2-editor-overrides`, version `2`, with an `overrides` mapping. All ten keys are required. Existing version-1 files load their original seven values unchanged, add stock defaults for the new fields, and upgrade on Save without a backup. The [stock example](../examples/overrides.example.cfg) is included. Missing files start with embedded defaults and are created when saved. Open… and Folder… choose another file/location. Saves detect external changes and replace atomically, without `.bak` files. Personal settings are ignored by Git.

## Tech unlocks

The **Tech unlocks** tab shows 106 unit/building entries with their required production building and independently editable levels for each faction. Values **0–5** are the producer's required research level; zero needs no research. For example, changing the Survivors Laser Rifleman from 5 to 2 unlocks it from Barracks level 2 without changing other factions' equivalents.

Drill Rigs unlock through their Mobile Drill Rigs, and the Scourge Demon uses the Altar's special behavior; those four records have no independent tier field. Other prerequisites and scenario restrictions remain. See [Tech unlock levels](TECH_UNLOCKS.md) for the producer mapping, special cases, and native table details.

Settings use **tech_unlocks.cfg**, schema `kknd2-editor-tech-unlocks`, version `1`, with an `unlocks` mapping containing all 106 IDs. The [complete stock example](../examples/tech_unlocks.example.cfg) is included. Missing files, preset selection, defaults/deltas, undo/redo, atomic saves, and Git ignores work like the other settings tabs, with no `.bak` files.

## Projectiles

The **Projectiles** tab provides a searchable faction-filtered browser, with speed and expiration fields, stock defaults, deltas, saved values and undo/redo. It lists 58 buildable-unit weapon definitions, with 33 verified speed controls and seven independently editable homing missile timers. Specialized effects remain visible with an explanation when they have no generic travel-speed or fixed-expiration setting.

Speed is the native velocity magnitude: **256 equals one world pixel per velocity step**, before game-speed scaling. Homing expiration defaults to **34 updates**, independently of the unit firing range. Other projectile types calculate arrival or impact instead of using this fixed timer. Increasing unit range alone can cause missiles to expire before reaching the target. See [Projectiles](PROJECTILES.md) for supported bounds, limitations and examples.

Settings use **projectiles.cfg**, schema `kknd2-editor-projectiles`, version 1, with a `projectiles` mapping. Missing files start with embedded defaults and are created on Save/Launch. The [stock example](../examples/projectiles.example.cfg) shows every required key. Personal settings are ignored by Git; saves are atomic with no `.bak` files.

The launcher also corrects a research progress-bar denominator mismatch. See [gameplay findings](GAMEPLAY_FINDINGS.md) for the evidence, zero-damage targeting behavior, Shift-placement feasibility and asset/footprint considerations.

## Fixes

The **Fixes** tab offers four independent toggles, each with two description lines and comparisons with default and saved values:

- **Acquisition Range:** idle ground units search three tiles beyond weapon range, within sight, after trying in-range targets, then move in to shoot. Fight keeps its wider search for passive buildings. Actual firing range is unchanged.
- **Shift build:** hold Shift while placing to keep the same building selected for the next click. Native availability and placement restrictions still apply.
- **Zero damage acts as a target filter:** reject target classes with zero raw weapon damage, including checks on targets outside firing range.
- **Prioritize target types by damage:** during automatic acquisition, prefer the highest-damage eligible class. Equal values keep the native selection rules; explicit target orders are not replaced by the ranking.

All four default to **Off**. Enable the zero-damage filter alongside damage priority if zero-damage classes should never be considered. These settings use **fixes.cfg**, schema `kknd2-editor-fixes`, version 2, with four boolean values in a `fixes` mapping. The [stock example](../examples/fixes.example.cfg) is included; personal files are ignored and saves produce no backups.

A small compiled C++ module handles these rules inside the game, with no Python polling or compiler requirement for players. The launcher verifies the supported game before applying it. Targeting changes affect AI as well as human players. See [Behavior fixes](FIXES.md) for exact scope, native implementation, rebuilding and manual test cases. Acquisition Range adds a three-tile search margin and native pursuit for idle ground units within sight. It preserves explicit Move/Hold/Guard orders and aircraft flight states; it does not change firing range or add attack-move.

## Upgrades

The **Upgrades** tab has six columns for tech levels 0–5. Edit oil yield, repair/healing rate, production speed for four producer classes, and the cost/time multiplier for upgrading the research lab itself. Research base/step settings stay in Overrides. Each row uses a two-line name/units label. Defaults, comparisons, history, filtering and atomic saves work as on the other tabs. See [Upgrades](UPGRADES.md) for units, stock curves, examples and limits.

## Launching KWIPv3

Click **Launch game** at the bottom right to save **all seven tabs** and launch `KWIPv3.exe` with the selected building limits, raw overrides, projectile settings, unlock levels, and fixes. In the multiplayer lobby, **select the unit configuration you edited**: the launcher does not choose it automatically. Successfully saved settings remain saved even if launch fails.

The launcher verifies the executable's SHA-256, starts a suspended process, validates all expected original values/instructions/tables, writes and verifies the selected changes, then resumes it. The compiled fixes module and small native helpers handle the behavior toggles and changed transfer/research-step calculations and per-weapon homing expiration; replacement unlock lists retain faction and producer membership. These run inside the game, without a Python polling loop. A validation/patch failure terminates the newly created child process. It never patches the executable on disk. Starting the game outside this editor therefore uses its original building limits, research/oil/placement rules, projectile settings, tech unlocks, and targeting/placement behavior. Saving settings does not alter an already running game. The new overrides, unlocks and fixes still need manual gameplay testing, including AI progression, save/load, and consecutive matches.

Only this KWIPv3 SHA-256 is supported:

```text
ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44
```

Other builds, including executables modified by another patcher, are rejected. Renaming another executable to `KWIPv3.exe` will not make it compatible. Original KKND2 and Carnage are not supported launch targets.

## Unit-file preservation and recovery

Original UCONFIG files mix a 120-byte UTF-16LE title and UTF-16LE column headings with ASCII numeric records. Treating the entire file as one text encoding can corrupt it.

The editor retains the original byte buffer and replaces only explicitly edited numeric field spans within their existing widths. It preserves the title, header, IDs, row order, tabs, unrelated padding, line endings, and file size, and never adds a BOM. It rejects unrecognized columns or malformed records. An unchanged unit save writes nothing.

Before a changed unit save, the editor verifies a timestamped copy in **UCONFIG\backups**, validates the replacement, flushes a temporary file beside the original, and atomically replaces the original. If the source changed externally, a backup cannot be made, or replacement fails, an error is shown and pending edits remain available.

To recover a unit configuration, close both editors, choose the matching filename and timestamp in `UCONFIG\backups`, and copy it back into `UCONFIG` under the original `.cfg` name. Keep the backup intact. These unit backups are separate from the six application settings files, which have no automatic backups.

## Window scaling and troubleshooting

The initial window is 1140 × 1000 logical pixels, approximately 2280 × 2000 at 200% DPI, capped to the screen's available work area. Two-line labels and row spacing are retained. Columns expand with the window; toolbars wrap and panels scroll. Narrow windows switch between the unit list and stats. Tab navigation scrolls focused fields into view. Mouse wheel scrolls vertically; Shift+wheel scrolls horizontally. Resizing remains live during dragging.

- **Double-click does nothing or opens source:** try the other launcher, or run `python "Launch Editor.pyw"` from PowerShell to diagnose the Python installation. Ensure Tcl/Tk is installed.
- **No configurations listed:** select the game's `UCONFIG` folder using Folder…, or supply `--folder`. A JSON application settings file cannot be opened as a unit configuration.
- **Cannot find KWIPv3:** use `--game-dir` or `KKND2_GAME_DIR`. KWIPv3 must be installed separately in the selected game folder.
- **Unsupported executable:** compare its SHA-256 with the supported value above. Do not bypass the check; patch addresses are specific to that build.
- **Cannot save / file changed externally:** check folder permissions, close other editors, and reopen the file after preserving any pending edits you need.
- **Text looks soft after moving between different-DPI monitors:** restart the editor on the target monitor. Tk uses system DPI awareness; scaling across monitors depends on Windows and the installed Tk version.

## Development and tests

```text
Launch Editor.pyw             Windowed Python entry point
Launch Editor.vbs             Optional Windows interpreter discovery
src/kknd2_editor/
    app.py                   Unit format, defaults, and main Tkinter UI
    building_limits.py       Settings schema and verified patch metadata
    limits_ui.py             Shared settings page and building limits UI
    overrides.py             Raw override schema and embedded defaults
    overrides_ui.py          Grouped override explanations and controls
    overrides_patch.py       Verified instruction patches and native helpers
    tech_unlocks.py          Unlock schema and replacement table builder
    unlock_data.py           Stock faction tiers and verified native table bytes
    unlocks_ui.py            Tech unlock page
    projectile_data.py       Stock weapon catalog and native metadata
    projectiles.py           Projectile schema and numeric bounds
    projectiles_ui.py        Searchable projectile browser and controls
    projectiles_patch.py     Per-weapon speed/lifetime patching
    fixes.py                 Boolean fixes schema and stock defaults
    fixes_ui.py              Toggle list using shared settings actions
    fixes_patch.py           Verified bridge to the compiled native module
    fixes_native.json        Generated x86 code/data/relocations (shipped)
    game_launcher.py         Validated Windows process patching
    paths.py                 Portable game/settings discovery
native/                      C++ behavior rules, verified ABI and build script
tests/                       Parser, save, GUI, launch, and path regressions
docs/STAT_REFERENCE.md        Field units, maxima, and analysis notes
examples/                    Stock limits, overrides, projectiles, unlocks and fixes examples
```

From the repository root, run:

```powershell
python -m unittest discover -s tests -v
```

Optional native instruction tests use `unicorn`. To also execute the actual placement/targeting routines against synthetic world fixtures, install `pefile` and set `KKND2_TEST_EXE` to your supported KWIPv3 executable before running the suite. This reads the file into an emulator; it does not launch the game or modify the executable.

Tests require Tk and an interactive desktop. They generate original-format fixtures from the embedded stock values, write only to temporary directories, and mock game launch. No game installation or proprietary config fixture is required. Optional x86 helper execution tests use Unicorn (`python -m pip install unicorn`); those tests skip when it is absent. Unicorn is not a runtime editor dependency. Coverage includes byte-preserving edits, malformed inputs, failures/external changes, defaults and undo/redo, DPI and live resize behavior, shared toolbar positions, settings, patch validation, and portable paths.

For an optional real-file integration run, set `KKND2_TEST_FILE` to a configuration file before running the same command. That source is read once into a temporary copy; it is never edited.

Personal `.cfg` files, backups, game binaries, caches, environments, and local IDE files are ignored by Git. Only stock example configurations are included. Keep game files and personal presets out of contributions.

See [override and combat-order research](OVERRIDES_RESEARCH.md) and the [engine extension backlog](ENGINE_EXTENSION_BACKLOG.md) for proposed features, source-project findings, and outstanding validation. The research notes are historical; the Overrides and Tech unlocks guides describe the implemented controls. Attack-move, further targeting controls, additional projectile controls, and physics extensions remain exploratory. Native fixes are implemented in C++; see [the build guide](FIXES.md#rebuilding-and-testing) if changing their behavior.

## Campaign unit configurations

Select a preset on Unit editor, enable **Use in campaign** beside the configuration selector and click **Launch game**. Engine settings and Fixes still apply. This checkbox starts off when the editor opens and applies to the selected configuration at launch. It does not select the multiplayer lobby preset.

The selected file must be in this game's UCONFIG folder, numbered 00 through 29, with a unique internal preset name. Ambiguous names are rejected before creating the process. Start a new mission for testing: pre-existing units in saved games may carry saved state. See [details and gameplay findings](BUILDINGS_AND_CAMPAIGN.md).
