======================================================================
KKND2 UNIT EDITOR - VERSION @VERSION@
Windows x64 portable build
======================================================================

Repository: https://github.com/AndersonHK/KKND2-Unit-Editor
Full guide: https://github.com/AndersonHK/KKND2-Unit-Editor/blob/master/docs/USER_GUIDE.md

Edit KKND2: Krossfire units without damaging the game's mixed-format
configuration files. Also customize building limits, research/oil rules,
tech unlocks, projectiles and optional targeting/placement fixes.

REQUIREMENTS
------------
* 64-bit Windows 10 or 11.
* Your own KKND2: Krossfire installation and original-format UCONFIG files.
* KWIPv3.exe for Launch game and the five engine-settings tabs.
  Unit file editing works without KWIPv3.
* Write access to the editor and game configuration folders.

Python, Tcl/Tk and the native fixes module are bundled. You do not need
Python, a compiler, an installer or administrator mode. Game executables,
art and personal presets are not included. This is an unsigned fan tool.

INSTALL
-------
1. Extract this ZIP completely. Do not run the EXE inside the ZIP.
2. Put its two files in a folder named KKND2 Unit Editor inside your game
   folder. Example:

   KKND2 Krossfire/
     KWIPv3.exe
     UCONFIG/
     KKND2 Unit Editor/
       KKND2 Unit Editor.exe
       README.txt

3. Double-click KKND2 Unit Editor.exe. Only the GUI opens.
4. If no configuration is found, use Folder on the Unit editor tab to
   select the game's UCONFIG folder, or Open to select a specific CFG.

For an upgrade, close the editor and replace only the EXE and README.txt.
Keep your existing CFG files. Settings are stored beside the EXE unless
you choose a different settings file/folder in a tab.

BASIC USE
---------
1. Check the selected unit configuration before editing.
2. Search for a unit, choose its faction, and edit the displayed values.
3. Save with Ctrl+S. Close the game's own unit editor while editing here.
4. For the other tabs, choose settings and click Launch game (bottom
   right). Launch saves ALL tabs and applies their settings to KWIPv3.
5. In the multiplayer lobby, select the SAME unit configuration you edited.
   The launcher does not select the lobby configuration automatically.

TABS
----
Unit editor     Stats, prices, build times, damage and ranges.
Building limits Maximum instances per player and building type.
Overrides       Research costs/times, tanker capacity, oil transfer,
                passive incomes and building placement reach.
Tech unlocks    Required producer research level for units/buildings.
Projectiles     Supported projectile speeds and homing expiration times.
Fixes           Shift build, zero-damage target filter, damage-type priority.

Fixes default to OFF. Enable them individually. For damage-type priority,
enable the zero-damage filter too if useless target classes must be skipped.
These are acquisition rules, not attack-move or an increased sight radius.
Targeting changes also affect AI. Network players need matching settings.

REVIEW AND UNDO
---------------
Default is the embedded stock reference. Saved is the last saved value.
Delta/Change shows differences from stock. Blue marks unsaved changes.
Use Unsaved, Defaults and Different from defaults to review your edits.
Undo/Redo: Ctrl+Z / Ctrl+Y. Save: Ctrl+S. Unit search: Ctrl+F.
Reset defaults is undoable and remains pending until you save.

FILES AND COMPATIBILITY
-----------------------
Building limits, overrides, tech unlocks, projectiles and fixes use separate
CFG files created on Save/Launch. They do not create .bak files.
Changed original unit files have recovery copies in UCONFIG/backups.
Your settings are not bundled in this download.

The launcher changes only the new game's process memory, never its EXE on
disk. Relaunch to apply changes. Launching outside the editor uses the
original engine behavior; your saved unit CFG edits still remain on disk.
Only the verified KWIPv3 build is supported (SHA-256):
ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44

Other builds and executables changed by another patcher are rejected.
The newer gameplay modifications still need broader in-match testing,
particularly multiplayer, save/load, AI progression and large battles.

TROUBLESHOOTING / FEEDBACK
--------------------------
No files: use Folder to select UCONFIG on the Unit editor tab.
No game: place the editor as shown above, or set KKND2_GAME_DIR to the game
folder. You can also launch the EXE with --game-dir "your game folder".
Cannot save: use writable folders and close other configuration editors.
Existing running editor: close it and reopen after upgrading.
High DPI: resizing stays live; small windows wrap controls and scroll.

For questions or bug reports, use the repository's Issues page. Include
version @VERSION@, Windows/DPI, the relevant settings and steps to reproduce.

======================================================================
BUNDLED RUNTIME NOTICES
======================================================================
The following notices apply to bundled third-party runtime components.
They do not assign a license to the game's assets or this project's code.

@RUNTIME_NOTICES@
