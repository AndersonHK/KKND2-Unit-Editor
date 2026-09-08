# KKND2 Unit Editor

A small Windows GUI for editing **KKND2: Krossfire** unit configurations without damaging their mixed text encodings. It also offers per-building instance limits for one verified **KWIPv3** executable, applied when launching the game.

The editor uses Python and Tkinter, with no third-party Python packages. It includes English names for all three factions, field limits and units, comparisons with stock defaults, undo/redo, and a layout that scales with Windows DPI and updates while resizing.

## Requirements

- Windows and Python **3.9 or newer**, with **Tcl/Tk and IDLE** enabled in the Python installer. For the optional VBS launcher, install the Windows Python launcher or add Python to PATH.
- Your own KKND2: Krossfire installation and its original-format `UCONFIG` files.
- **KWIPv3.exe** is required only for the **Launch game** button and its building-limit modifications. Editing unit configurations does not require it.
- Write access to the configuration folders and this checkout, where the editor stores building-limit settings by default.

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
```

`--game-dir` explicitly chooses the installation used by Launch game. Otherwise, launch uses the selected unit configuration's parent game folder, then `KKND2_GAME_DIR`, then an installation beside/containing the checkout or in the current working directory. Discovery looks for `UCONFIG` or `KWIPv3.exe`; it does not scan your drives. `--folder` chooses the configuration directory; an explicit file takes precedence for the file opened.

For a persistent location without editing source, set the Windows user environment variable **KKND2_GAME_DIR** to your game folder and restart the editor. No installation path is stored in the source. The VBS launcher tries `.venv\Scripts\pythonw.exe`, then `pyw.exe -3`, then `pythonw.exe` on PATH.

## Editing and reviewing changes

The shared top toolbar stays in the same place on both tabs. **Save**, **Unsaved**, **Defaults**, **Open…**, and **Folder…** act on the selected tab.

On the unit tab, search by English name or internal game ID, filter by faction, and select a unit or building. Each stat shows its stored unit and native editor maximum. A `-` means the field is unavailable and cannot be edited. Title text and internal identifiers are preserved.

| Column or indicator | Meaning |
| --- | --- |
| Value | Current editable value; blue indicates an unsaved edit |
| Default | Fixed stock reference value, unaffected by saving |
| Delta | Current minus default; nonzero differences appear in gold |
| Saved | Value when the file was opened or last saved |
| `*` in the unit list | Unit has unsaved changes |
| `~` in the unit list | Unit differs from the stock baseline |

**Unsaved** reviews pending changes across the current configuration. **Defaults** reviews all differences from the baseline, including edits saved in earlier sessions. **Different from defaults** filters the list. Unknown units show `n/a` for defaults rather than an invented baseline.

**Undo / Ctrl+Z** and **Redo / Ctrl+Y** operate on edit groups. Unit edits are committed to the in-memory model when leaving a unit, reviewing, or saving. **Revert saved** discards pending edits for the selected unit, while **Reset defaults** restores that unit's reference values. On the building tab these actions apply to its limit configuration. Resetting defaults is undoable and does not save until you click Save. Switching files or closing with pending edits prompts to save, discard, or cancel. **Ctrl+F** focuses unit search.

New unit values above the native editor caps are rejected. Existing out-of-range values are preserved when unrelated fields are edited; they are never silently clamped. Newly edited build times must be at least 1. See [the stat reference](docs/STAT_REFERENCE.md) for all caps, timing/range units, and the evidence behind them. Movement speed remains a raw rate because its physical conversion has not been verified.

## Building limits and launching KWIPv3

The **Building limits** tab shows 49 building records across the factions, including towers and walls, with 48 editable limits. Values count instances **per player and building type**. These settings are independent of unit statistics and do not belong in a game `UCONFIG` file.

| Building category | Editor bounds |
| --- | --- |
| Machine shops and faction equivalents | 1–4 |
| Barracks and faction equivalents | 1–7 |
| Other ordinary records, including walls | 1–100 |
| Altar of the Scourge | Original 0; read-only because of special game logic |

Production buildings retain tighter bounds because of production-menu constraints. The general maximum of 100 is an editor policy, not a proven safe engine maximum for every building or map. Limits do not unlock buildings, alter global unit caps, or add auto-attack or tanker features. Extended in-match behavior has not been exhaustively tested. Network players should use matching modifications.

Limits are stored in **building_limits.cfg** at the checkout root by default. A missing file starts with stock KWIPv3 values and is created when saved. **Open…** selects another building settings file; **Folder…** selects that folder's `building_limits.cfg`. Subsequent saves and launches use the selected file. The versioned UTF-8 JSON schema is `kknd2-editor-building-limits`, version `1`, with a `limits` mapping from internal IDs to integer values. All 49 known keys are required; unknown/duplicate keys and invalid values are rejected. [The example file](examples/building_limits.example.cfg) contains the complete stock schema, not personal settings.

Building settings are saved using a flushed temporary file and atomic replacement, with external-change detection. They do **not** create timestamped `.bak` files. Keep a separate copy yourself if you want multiple presets.

Click **Launch game** at the bottom right to save **both tabs** and launch `KWIPv3.exe` with the selected building limits. In the multiplayer lobby, **select the unit configuration you edited**: the launcher does not choose it automatically. Successfully saved settings remain saved even if launch fails.

The launcher verifies the executable's SHA-256, starts a suspended process, validates all original building-limit values, writes and verifies changed two-byte values, then resumes it. A validation/patch failure terminates the newly created child process. It never patches the executable on disk. Starting the game outside this editor therefore uses its original building limits.

Only this KWIPv3 SHA-256 is supported:

```text
ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44
```

Other builds, including executables modified by another patcher, are rejected. Renaming another executable to `KWIPv3.exe` will not make it compatible. Original KKND2 and Carnage are not supported launch targets.

## Unit-file preservation and recovery

Original UCONFIG files mix a 120-byte UTF-16LE title and UTF-16LE column headings with ASCII numeric records. Treating the entire file as one text encoding can corrupt it.

The editor retains the original byte buffer and replaces only explicitly edited numeric field spans within their existing widths. It preserves the title, header, IDs, row order, tabs, unrelated padding, line endings, and file size, and never adds a BOM. It rejects unrecognized columns or malformed records. An unchanged unit save writes nothing.

Before a changed unit save, the editor verifies a timestamped copy in **UCONFIG\backups**, validates the replacement, flushes a temporary file beside the original, and atomically replaces the original. If the source changed externally, a backup cannot be made, or replacement fails, an error is shown and pending edits remain available.

To recover a unit configuration, close both editors, choose the matching filename and timestamp in `UCONFIG\backups`, and copy it back into `UCONFIG` under the original `.cfg` name. Keep the backup intact. These unit backups are separate from building settings, which have no automatic backups.

## Window scaling and troubleshooting

The initial window is 1140 × 1000 logical pixels, approximately 2280 × 2000 at 200% DPI, capped to the screen's available work area. Two-line labels and row spacing are retained. Columns expand with the window; toolbars wrap and panels scroll. Narrow windows switch between the unit list and stats. Tab navigation scrolls focused fields into view. Mouse wheel scrolls vertically; Shift+wheel scrolls horizontally. Resizing remains live during dragging.

- **Double-click does nothing or opens source:** try the other launcher, or run `python "Launch Editor.pyw"` from PowerShell to diagnose the Python installation. Ensure Tcl/Tk is installed.
- **No configurations listed:** select the game's `UCONFIG` folder using Folder…, or supply `--folder`. A JSON building-limits file cannot be opened as a unit configuration.
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
    limits_ui.py             Building limits page
    game_launcher.py         Validated Windows process patching
    paths.py                 Portable game/settings discovery
tests/                       Parser, save, GUI, launch, and path regressions
docs/STAT_REFERENCE.md        Field units, maxima, and analysis notes
examples/                    Stock building settings example
```

From the repository root, run:

```powershell
python -m unittest discover -s tests -v
```

Tests require Tk and an interactive desktop. They generate original-format fixtures from the embedded stock values, write only to temporary directories, and mock game launch. No game installation or proprietary config fixture is required. Coverage includes byte-preserving edits, malformed inputs, failures/external changes, defaults and undo/redo, DPI and live resize behavior, shared toolbar positions, settings, patch validation, and portable paths.

For an optional real-file integration run, set `KKND2_TEST_FILE` to a configuration file before running the same command. That source is read once into a temporary copy; it is never edited.

Personal `.cfg` files, backups, game binaries, caches, environments, and local IDE files are ignored by Git. Only the stock example configuration is included. Keep game files and personal presets out of contributions.
