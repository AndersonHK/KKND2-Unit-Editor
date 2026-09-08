# KKND2 Unit Editor

Double-click **Launch Editor.vbs** or **Launch Editor.pyw** in this folder. Both use windowed Python and open only the GUI. Avoid opening the `.py` source with a console-based file association. It uses your installed Python 3.9 and opens `UCONFIG_02.cfg` in `<game folder>\UCONFIG`. No packages or installation needed. You can also run `python kknd2_editor.py`, or pass a configuration file as the first argument.

1. Choose a configuration, then search for a unit or select a faction.
2. Select the unit and type its values. The **Saved** column shows values from when you opened or last saved the file. Blue values are unsaved changes. Internal game IDs are shown above the fields; some labels differ from the unit names displayed in-game.
3. Use **Unsaved** to see all pending edits. **Save** / **Ctrl+S** writes them, including the unit currently on screen.

**Undo / Ctrl+Z** and **Redo / Ctrl+Y** operate on groups of edits committed when leaving a unit, reviewing, or saving. Saving starts a new undo history. **Revert saved** also clears invalid input. **Ctrl+F** focuses search. Closing or switching files prompts to save pending edits.

## DPI and smaller windows

Fonts, row heights, spacing, and initial window dimensions scale with DPI. The initial window fits inside the Windows work area. At narrow widths, **Units / Search** and **Unit stats** switch between the list and the form; wider windows show both together. Toolbars wrap. The stat panel scrolls vertically and horizontally, and keyboard Tab brings the focused field into view. Use the mouse wheel to scroll stats, Shift+wheel to scroll sideways, or the scrollbars. The **Saved**, **Default**, and **Delta** columns stay reachable at large text sizes.

The app uses Tk 8.6 system DPI awareness; Windows handles scaling when moving it to a monitor with a different DPI. Restart on that monitor if you want native text sharpness there.

## Comparing with defaults

All **1,870 values for 110 units** from your user-confirmed default `UCONFIG_02.cfg` were embedded in `kknd2_editor.py` on 2026-09-08. This snapshot never changes when you save a configuration.

- **Default** shows that frozen value. **Delta** shows current minus default. **Saved** shows the last saved value for the open file.
- **Defaults** opens all differences, including changes saved in earlier sessions. **Unsaved** lists only changes since opening or last saving.
- **Different from defaults** filters the unit list. A `~` marks a unit differing from the baseline; `*` marks unsaved changes. Gold deltas indicate differences from defaults.
- **Reset defaults** restores the selected unit to the embedded baseline. It is undoable and does not write to disk until Save. **Revert saved** restores the last saved values instead.
- A unit missing from the snapshot shows `n/a`; its default values are never guessed.

## File preservation

The inspected files mix a 120-byte UTF-16LE title, UTF-16LE stat headings, and an ASCII table beginning at byte 534. Each of the 110 records has 17 numeric or `-` fields. This is why treating the entire file as one text encoding breaks it.

The editor retains the original byte buffer and changes only the chosen numeric field spans, using the existing field widths. It preserves the title, header, IDs, row order, tabs, padding outside edited fields, line endings, and file size. It never adds a BOM. An unchanged save writes nothing. An unrecognized schema is rejected rather than guessed. The title and unavailable `-` fields are not editable.

Every actual save creates and verifies a timestamped copy under **UCONFIG\backups**, writes and flushes a temporary file beside the original, reparses it, then replaces the original atomically and verifies the result. If the original changed since opening, saving stops. Backup or replacement errors are shown and pending edits remain available.

Close the game's unit editor before saving here, so it cannot overwrite changes with a previously loaded copy. Inputs retain the game's stored numbers. Each field now displays its unit and in-game editor maximum. New edits above that maximum are rejected; existing above-limit values are preserved unchanged, never silently clamped. Build time must be at least 1 when edited. Other fields allow zero because stock inactive stats use zero. These limits reproduce the native editor and are not a guarantee that every combination is meaningful in the game. See STAT_REFERENCE.md for units and evidence.

## Restoring a backup

Close the Python editor and the game's unit editor. In `UCONFIG\backups`, choose the backup with the correct configuration filename and timestamp. Copy it into `UCONFIG` and rename the copy to the original `.cfg` filename, replacing that file. Keep the backup itself intact.

## Verification

Run `python test_editor.py`. Tests read **only UCONFIG_02.cfg** and perform all writes on disposable temporary copies. They check exact unchanged round trips, every editable field's byte boundaries, invalid values, undo/redo, backup integrity, failed writes, external edits, and the GUI's edit/filter/save/reopen flow. Additional tests cover persistent default comparisons, undoable resets, and all controls/fields at simulated 100%, 150%, 200%, and 250% DPI in small windows. The tests do not launch the game.

On another computer, install Python 3.9+ with Tkinter and open `Launch Editor.pyw`; the VBS launcher discovers windowed Python.

## Names, limits, and units

All 110 unit/building names use the English strings from the installed game, including distinct Evolved and Series 9 names. Search accepts these names and the original internal IDs. Config IDs are never rewritten. Maximum values and units appear below every stat name; default comparisons retain the original frozen snapshot. Speed, armour, and accuracy are explicitly marked as raw ratings because their physical or percentage conversion has not been fully verified.
