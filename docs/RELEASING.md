# Release packaging

`release/KKND2-Unit-Editor-v0.2.0-windows-x64.zip` is the shareable portable build. It contains exactly two top-level files: `KKND2 Unit Editor.exe` and `README.txt`. No source tree, tests, game files, personal CFGs, logs or backups are copied into the ZIP. Python/Tk and `fixes_native.json` are bundled inside the EXE. A SHA-256 sidecar accompanies the archive.

The single version source is `src/kknd2_editor/__init__.py`. It supplies the window title, Windows file/product version, ZIP filename and text readme. Update the version, README download link and changelog together for a new release. Archives are intentionally tracked in `release/`; intermediate EXEs and build files remain ignored.

## Build on Windows

Use 64-bit Python with Tcl/Tk and its runtime license files installed. The initial 0.2.0 package uses Python 3.9.7 and Tcl/Tk 8.6.9. If changing the Tcl version, update its corresponding notice in `tools/licenses/TCL.txt` and the build script. Python and Tk notices are read from the selected interpreter, and the PyInstaller notice is taken from its installed distribution.

```powershell
python -m venv .venv-build
.venv-build\Scripts\python -m pip install -r tools/requirements-build.txt
.venv-build\Scripts\python tools/build_release.py
```

PyInstaller is only a build dependency. The [official packaging guide](https://pyinstaller.org/en/stable/usage.html) describes the one-file/windowed and version-resource options used here. The script keeps the build/spec/cache outputs in a temporary folder and packages an explicit two-file allowlist. It does not scan for local settings. The native fixes payload is already built; if its C++ sources change, first follow [the native build instructions](FIXES.md#rebuilding-and-testing).

`tools/release-readme.txt` is the ASCII-formatted player guide template. Version substitution and verbatim bundled-runtime notices are added when packaging. The Tcl notice comes from the [Tcl 8.6.9 source distribution](https://github.com/tcltk/tcl/blob/core-8-6-9/license.terms). Third-party notices do not assign a license to this project's code or game assets.

## Check before sharing

1. Run `python -m unittest discover -s tests -v`. Use the optional native tests with `unicorn`, `pefile` and `KKND2_TEST_EXE` when changing engine behavior.
2. Extract the release into an empty writable folder and launch the EXE. Confirm the six tabs, version and GUI-only startup. Test from a working directory different from the EXE folder. Personal settings must stay beside the EXE, outside its temporary runtime extraction directory.
3. Verify the ZIP's two filenames and SHA-256 sidecar. Open README.txt and follow the installation steps. Check that `fixes_native.json` is included in the packaged application.
4. Manually test edited units, launch overrides and behavior fixes in-game before declaring gameplay validation complete. Automated and suspended-process tests do not replace matches.
5. Commit with a descriptive message when authorized. Upload/push or publish a GitHub Release only when requested. This packaging script does not publish anything.

## Upgrading a player's installation

Close the editor and replace only the EXE and README.txt. Leave the five personal settings CFGs and the game's UCONFIG folder intact. Missing settings files start from embedded defaults and are created on Save/Launch. A source checkout stores settings beside its launchers; a frozen build uses the EXE's folder.
