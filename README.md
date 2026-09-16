# KKND2 Unit Editor

**Version 0.3.0 — testing build** | Windows x64 | [Download the portable ZIP](release/KKND2-Unit-Editor-v0.3.0-windows-x64.zip?raw=true)

A fan-made editor for **KKND2: Krossfire**. Edit unit stats without corrupting the game's mixed-format configuration files, and launch **KWIPv3** with custom building limits, research and oil settings, tech unlocks, projectile settings and optional behavior fixes.

The portable download needs **no Python installation**. It contains just `KKND2 Unit Editor.exe` and an ASCII-formatted `README.txt`. Game files and personal presets are not included.

## Quick start

1. Download the ZIP above and extract it completely.
2. Put the two extracted files in a **KKND2 Unit Editor** subfolder inside your game folder:

   ```text
   KKND2 Krossfire/
     KWIPv3.exe
     UCONFIG/
     KKND2 Unit Editor/
       KKND2 Unit Editor.exe
       README.txt
   ```

3. Double-click **KKND2 Unit Editor.exe**. If no unit configuration is found, use **Folder...** on the Unit editor tab to choose the game's `UCONFIG` folder.
4. Check the selected configuration, choose a unit and edit its values. **Ctrl+S** saves the current tab.
5. To use the engine settings, click **Launch game** at the bottom right. This saves all tabs and starts KWIPv3 with your settings.
6. **For multiplayer, select the same unit configuration in the game's lobby.** For campaign missions, check **Use in campaign** beside the Unit editor configuration selector before launching. This uses the selected preset's internal name; the checkbox starts off each editor session.

Use 64-bit Windows 10 or 11 and a writable editor/game configuration folder. The EXE opens only the GUI. Close the game's own unit editor while saving changes here.

To upgrade, close the editor and replace the EXE and `README.txt`; keep your existing `.cfg` files. You can keep the editor elsewhere and use **Open... / Folder...**, `--game-dir`, or the `KKND2_GAME_DIR` environment variable. See the [full user guide](docs/USER_GUIDE.md) for options.

## What you can edit

| Tab | Controls |
| --- | --- |
| **Unit editor** | Cost, build time, health, movement, armor, accuracy, ranges, firing delays, turret burst counts and damage by target type; English names for all three factions |
| **Building limits** | Maximum instances per player and building type, including defenses and walls; solar/thermal AI ceilings follow the same settings |
| **Overrides** | Research cost/time and tier steps, tanker capacity, loading/unloading rates, solar/thermal income and building placement reach |
| **Tech unlocks** | Required producer research level for individual units and buildings |
| **Projectiles** | Verified travel speeds and homing missile expiration timers |
| **Upgrades** | Six-level oil yield, repair/healing and production curves; lab-specific upgrade cost/time multiplier |
| **Fixes** | Shift-repeat building placement, zero-damage target filtering, target-type priority, and one-tile extra acquisition range |

The Fixes toggles default to **Off**. Enable the zero-damage filter alongside damage priority if zero-damage target classes should be excluded entirely. Acquisition Range searches 32 world pixels beyond mobile units' weapon range, within sight, and tries in-range targets first. It does not extend firing range or implement attack-move. Targeting changes also apply to AI.

## Defaults, saving and compatibility

- **Default** is the embedded stock reference; **Saved** is the last saved value. **Delta/Change**, **Unsaved**, **Defaults**, and **Different from defaults** help review edits. Undo/redo use **Ctrl+Z / Ctrl+Y**. High DPI, live resizing and scrollable panels are supported.
- The six engine-settings tabs use separate `.cfg` files beside the EXE, created on Save/Launch. They create no `.bak` files. Unit edits preserve the original file format and make recovery copies in `UCONFIG/backups`.
- **Burst Count** saves separately in the matching `UCONFIG_nn_ext.cfg`, with no backups or native-format changes. It controls supported vehicle turrets (the Anaconda defaults to 2), with a limit of 127 shots. Launch game applies the selected preset's extension for the session; changing the multiplayer lobby preset alone does not switch it. See [extended unit settings](docs/UNIT_EXTENSIONS.md) for coverage and file compatibility.
- Unit file editing works without KWIPv3. **Launch game requires the verified KWIPv3 build below**. The launcher patches only its new process's memory, never the game EXE on disk. Relaunch to apply changes. Saved unit CFG edits remain on disk even when launching the game normally.
- Some production-building limits remain constrained, and only verified projectile fields are editable. See the feature guides below for exact limits and special cases. The newer gameplay modifications need broader manual testing, especially multiplayer, save/load, AI progression and large armies. Network players need matching settings.

Supported `KWIPv3.exe` SHA-256:

```text
ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44
```

Other builds, including executables changed by another patcher, are rejected. This download does not include KWIPv3 or the game. The Windows build is unsigned.

## Help and feature details

[Full user guide and troubleshooting](docs/USER_GUIDE.md) · [Unit stats](docs/STAT_REFERENCE.md) · [Extended unit settings](docs/UNIT_EXTENSIONS.md) · [Overrides](docs/OVERRIDES.md) · [Tech unlocks](docs/TECH_UNLOCKS.md) · [Projectiles](docs/PROJECTILES.md) · [Upgrades](docs/UPGRADES.md) · [Fixes](docs/FIXES.md) · [Changelog](CHANGELOG.md)

For bug reports, use [Issues](https://github.com/AndersonHK/KKND2-Unit-Editor/issues). Include the editor version, Windows/DPI, relevant settings and steps to reproduce. Report gameplay issues with the selected unit configuration and enabled fixes.

## Run from source or build a release

Source users need Python 3.9+ with Tcl/Tk. Download/clone the repository and double-click **Launch Editor.pyw**, or use **Launch Editor.vbs** for interpreter discovery. No third-party Python packages are needed to run the source editor. Its version matches the packaged EXE.

```powershell
python -m unittest discover -s tests -v
```

Optional native execution tests use `unicorn`, `pefile`, and `KKND2_TEST_EXE` pointing to the supported game EXE. They emulate its instructions without changing the game file. See [release packaging](docs/RELEASING.md) for building the standalone ZIP, and [native fixes](docs/FIXES.md#rebuilding-and-testing) for rebuilding the C++ module.

Personal configs, backups, build environments and temporary outputs are ignored. `release/` contains the versioned shareable ZIP and its SHA-256 checksum; development files and personal settings are excluded from the archive. The [backlog](docs/ENGINE_EXTENSION_BACKLOG.md) tracks further engine work.

See [AI limits, Anaconda bursts, tier effects and campaign stats](docs/BUILDINGS_AND_CAMPAIGN.md) for the latest gameplay findings.
