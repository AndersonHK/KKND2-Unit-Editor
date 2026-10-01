# KKND2 stat reference

The maximums below match the reference English KKND2 native unit editor, except cost (10,000 instead of 5,000) and reload time (600 instead of 250). They are enforced for new edits. Loading or saving an unrelated edit never clamps an existing value. The numeric representation on disk remains unchanged.

| Field | Maximum | Stored unit |
|---|---:|---|
| Cost | 10000 | Resource units |
| Build time | 600 | Seconds at normal speed; edited minimum 1 |
| Hitpoints | 10000 | HP |
| View range | 41 | Map tiles |
| Speed | 260 | Raw movement rate; conversion unverified |
| Armour | 255 | Raw armour rating; conversion unverified |
| Armor Type (extended) | Enum 0–4 | Incoming damage category: Infantry, Vehicle, Beast, Building or Aircraft |
| Accuracy | 260 | Raw accuracy rating; not a 0–100 percentage |
| Weapon range | 510 | World pixels; 32 pixels = 1 tile |
| Minimum range | 256 | World pixels; 32 pixels = 1 tile |
| Bullet count | 250 | Native weapon count; not the separate turret burst count |
| Burst count (extended) | 127 | Shots per supported vehicle turret burst; minimum 1, saved in a companion CFG |
| Fire delay | 300 | Nominal 1/60-second game-time ticks |
| Reload time | 600 | Nominal 1/60-second game-time ticks |
| Each of the five damage fields | 4000 | Base damage before game combat modifiers |

For example, weapon range 320 means 10 tiles; view range 12 means 12 tiles. Delay 60 corresponds nominally to 1 second at normal speed. Delay values are not milliseconds or rendered frame counts. Actual timing also depends on integer frame rounding, animations, veterancy, game speed, and executable patches. The editor does not promise stopwatch timing for KWIPv3 or other altered executables.

The Burst Count and Armor Type rows are outside the original 17-column schema. See [extended unit settings](UNIT_EXTENSIONS.md) for stock turret counts, supported units, launch behavior, and the signed-byte reason for the 127 cap.

## Evidence from the reference original KKND2.exe

Read-only analysis of the executable on 2026-09-08:

- The 17 native slider metadata records begin at virtual address `0x4B02F0`, with stride `0x24`. The maximum is the dword at record offset `+24`. Slider initialization at `0x428C41` consumes the bounds. These include accuracy 260 and weapon range 510.
- All 110 English names were resolved from the config identifier/enum table (`0x4AFEAC`, stride 8) into unit definitions (`0x4CCA20`, stride `0x110`), using their display-name pointer at offset `+8`. Names are embedded in the Python script; no executable reads or additional dependencies are needed at runtime.
- Build time at definition offset `+0x7C` is multiplied by 30 for the production timer at `0x4205B9`. Building production also uses this value as a divisor after conversion (`0x44303D`), so new zero build times are rejected.
- View range at definition offset `+0x20` is shifted left 13 at `0x40D608` into map coordinates. A tile is 8192 coordinate subunits, or 32 world pixels.
- Range checks at `0x468247` onward shift coordinate distances right 8 and compare against weapon range (`+0x24`, `0x4682C0`) and minimum range (`+0xA4`, `0x4682EE`). `0x4676D0` converts weapon range into tiles by shifting right 5.
- Firing code at `0x474DDE` and `0x485F30` converts delay with `(value << 8) / gameSpeed + 1`. The original normal gameSpeed is 512; at 30 simulation updates/second this is nominally 1/60 second per raw unit, plus frame rounding. This is a conversion reference, not an assertion that every weapon's complete firing cycle is identical.

Reload time is stored in 32-bit definition fields, with a signed 16-bit intermediate/countdown in one firing path. The extended cap of 600 fits both paths; it is not a claim that arbitrarily large values are safe. In KWIPv3, the narrower path stores the reload value at `0x4D2638`, sign-extends it at `0x4D271F`, and converts/narrows it again at `0x4D2726–0x4D2736`. Cost is also deliberately extended: 10,000 fits the signed 16-bit production cost fields observed in KWIPv3. For example, `0x4344D7` copies the definition cost into a word and `0x434503` sign-extends it. The positive signed-word boundary is 32,767, not a universally safe cap; modifiers and other consumers still require play-testing. Remaining field caps retain the native editor limits. Not all fields share the same storage type, and target acquisition and other game systems can impose additional restrictions.
