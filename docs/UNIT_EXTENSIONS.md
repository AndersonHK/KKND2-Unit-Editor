# Extended unit settings

**Burst Count** appears directly below **Bullet Count** in Unit editor. It sets the number of shots in a supported vehicle turret's burst. Fire Delay controls spacing inside that burst; Reload Time controls the pause between bursts. For example, the Anaconda's stock Burst Count is **2**, even though its native Bullet Count is **0**.

The new row uses the same Default, Saved and Delta columns, modified-unit filter, comparisons, undo/redo, Revert saved and Reset defaults as other unit stats. Its allowed range is **1–127 shots**. Defaults are embedded in the editor, independent of your files.

## Saving and using a preset

1. Open a native preset such as `UCONFIG_02.cfg` and edit Burst Count.
2. Save. The editor creates **`UCONFIG_02_ext.cfg` beside it**. A burst-only change leaves the original CFG byte-for-byte unchanged. Extension saves are atomic and create no backups. An unchanged stock preset needs no companion file.
3. Click **Launch game** to apply the selected preset's extended values. In multiplayer, select that same native preset in the lobby. Use **Use in campaign** to also load its native stats in campaign missions.

Extended settings apply to the launched game session, including AI. They require the supported KWIPv3 launcher; launching the game normally uses stock turret counts. Relaunch after selecting another preset or changing extended values. Changing the lobby preset alone does not switch extensions. Multiplayer participants need matching native and extended settings.

Keep the native file and its companion together when sharing a preset, and use matching names if changing the slot number. Both are personal settings excluded from Git and release ZIPs. If you rename the preset's display title in the game's own editor, reopen it here and Save before playing; that refreshes the companion title too. Do not keep orphaned `_ext.cfg` files in the game folder.

## Which weapons are covered?

The row currently supports 16 vehicle turret definitions: Hover Buggy, ATV, Anaconda Tank, Barrage Craft, The Enforcer, Juggernaut, Crinoid, War Mastodon, Death Hippo, Missile Crab, Responsebot, Radiator, Tankbot, Doom Dome, Cauteriser and Grim Reaper.

A **`-`** means there is no supported separate turret burst setting for that unit. Infantry and other direct weapons retain their original Bullet Count field. Specialized aircraft and defense firing routines are not covered by this extension. The legacy Bullet Count field is preserved exactly; it does not become a second control for the new turret value.

## Companion schema and compatibility

The schema uses stable unit IDs and named fields so future extensions can add more values without adding columns to the native CFG. Version 1 stores only differences from stock:

```json
{
  "schema": "kknd2-editor-unit-extensions",
  "version": 1,
  "units": {
    "UNIT_SURV_ANACONDATANK": {"burst_count": 3}
  }
}
```

**On disk this UTF-8 JSON follows a 120-byte compatibility header**, containing the native preset title as null-padded UTF-16LE. It is not a plain JSON file. Use the editor to change it. The game's preset scanner accepts `UCONFIG_02_ext.cfg` as slot 02 and reads its title; preserving the same terminated title keeps enumeration harmless regardless of file order. The game then loads the canonical `UCONFIG_02.cfg`, whose original schema remains intact. The editor's configuration selector excludes companions.

Unknown schemas, versions, unit IDs, fields, duplicate keys and out-of-range values are rejected instead of discarded. Saving checks both files for external changes first. If a disk error occurs after native values were saved but before the extension was saved, the error identifies that partial save and preserves the pending extension edits for retry.

## Implementation and validation

For the verified KWIPv3 build, vehicle unit definitions at `0x52BED8 + enum * 0x110` point to turret definitions through `+0x60`. Turret `+0x10` is the burst count and `+0x28` identifies the supported `0x4DA4D9` handler. The launcher verifies these pointers, handlers and original counts before writing four-byte count values into its suspended child process. It does not alter the executable on disk or inject another code hook for this feature.

The firing routine at `0x4DAF5A–0x4DAF85` increments a byte at runtime unit `+0x310`, sign-extends it and compares it with the turret count. At 128 the counter would wrap negative, so this editor caps the value at 127. Native instruction tests exercise the burst/reload transition for each supported turret, including that boundary. They also execute the game's title-reading loop with both native/extension enumeration orders. Full-match behavior still needs player testing.
