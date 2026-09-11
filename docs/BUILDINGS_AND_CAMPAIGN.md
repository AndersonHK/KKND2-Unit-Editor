# AI limits, firing counts, research tiers and campaign presets

These findings target the supported KWIPv3 executable. Addresses below refer to that build. Native instruction tests use synthetic state; they are not a substitute for a complete match.

## AI solar and thermal limits

The economic planner has separate literal-four checks at `0x4277A6` (solar class) and `0x4277F4` (thermal class). Raising the building definition's limit alone leaves those planning checks unchanged.

In 0.2.1 these comparisons read the limit from the relevant faction's actual building definition. The AI's faction table selects its solar/thermal building; the same two-byte cap edited by Building Limits is then used. There is no separate AI setting to keep synchronized. With stock limits the original instructions remain untouched. Different limits for each faction are supported, including decreases.

This raises the planner's ceiling, not a guaranteed build quota. Existing technology checks, priorities, funds, available space and scripted mission decisions can still stop construction. Other AI building types have independent desired-count logic; this change does not claim to synchronize every AI construction rule.

Implementation: AI state `+8` points to its faction table (`0x505EA8 + faction * 0x74`); table slots `+0x14`/`+0x10` select solar/thermal enums. Native counters are at AI `+0x94`/`+0x90`. Compiled comparison adapters preserve registers, stack and the normal CMP flags. Tests compare those flags with ordinary CMP instructions at multiple counts and different per-faction caps. Both original sites are verified before any feature writes process memory.

## Why the Anaconda fires twice with Bullet Count 0

UCONFIG's Bullet Count is a generic unit-definition field at `+0xF4`. Its native editor descriptor (`0x50673C`) uses the generic setter `0x42DB45`. Unlike Fire Delay and Reload Time, that setter does not redirect to a turret's separate data.

The Anaconda (enum 54) has a turret definition at `0x52AF98`. Its **turret burst count is 2**, at turret `+0x10`. The firing routine compares the current burst counter against that value at `0x4DAF82`. Its Fire Delay and Reload Time are separately 10 and 85 in stock turret data.

Therefore the editor correctly reads 0 from the CFG, but this is not the effective turret burst count. Changing that CFG field is not a way to change the Anaconda's two-shot burst. This is a native schema limitation, not evidence of free shots or a zero-means-two convention. Version 0.2.2 exposes the separate **Burst Count** row, saved in a companion file; see [extended unit settings](UNIT_EXTENSIONS.md).

## Research-tier effects

The [original manual, Appendix B](https://www.assaracos.com/_files/ugd/a1f93e_24bebc5fe2b8457daed0bd700924c024.pdf?index=true) describes these effects across faction equivalents:

| Building class | Confirmed upgrade benefit |
| --- | --- |
| Research lab | Subsequent research becomes cheaper and faster. |
| Power station | More resources refined from the same raw oil. |
| Repair/healing building | Faster repair/healing. The bundled game readme also describes cheaper repairs. |
| Armoury / Forge / Weapons Control | Armor bonuses for newly produced units, plus defense and constructible unlocks. |
| Outpost / Clan Hall / Barn | Minimap/radar improvements and building/wall unlocks. |
| Barracks / Warrior Hall / Microunit Factory | More infantry choices. |
| Machine Shop / Beast Enclosure / Macrounit Factory | More vehicles/beasts, aircraft and constructible choices. |

KWIPv3's refining table at `0x5285DC` contains six fixed-point factors approximately **1.00, 1.05, 1.10, 1.15, 1.20, 1.25**. Stock 400-oil loads therefore yield approximately 400 through 500 resources. Capacity is a separate raw-oil quantity. Solar/thermal payout routines `0x40EF89`/`0x40EF46` use fixed payouts and delays without a tier multiplier; their Overrides values should not be described as per-tier income.

Do not infer a universal production-speed bonus from the tier number. The bundled readme makes a broad production/processing-speed statement, but its building-by-building list and the manual primarily describe new choices for infantry/vehicle producers. A precise KWIPv3 production-speed curve has not yet been established here.

Nonlinear and building-specific effects are feasible: replace a six-entry effect table for a shared curve, or select a separate curve by building type where the routine needs that distinction. For example, refining could use explicit yields of 100%, 103%, 108%, 120%, 140%, 175% instead of even steps. These are illustrative proposed values, not current overrides or verified safe bounds.

The **price/time to research a tier**, the **benefit granted by that tier**, and **what it unlocks** are three different controls. Current Overrides expose lab-dependent research bases and steps; Tech unlocks exposes producer-level requirements. Neither currently provides arbitrary per-building efficiency curves. Candidate follow-ups are per-tier research prices/times, refining yields, repair rates/costs and separate effective turret burst counts. Production-speed consumers need further tracing before exposing a numerical curve.

## Campaign unit configurations

On Unit editor, select the preset and enable **Use in campaign** next to the configuration selector, then **Launch game**. It starts KWIPv3 with the existing `-stats` option as well as the launcher's other patches. Leave the checkbox off for ordinary launching; multiplayer lobby selection remains manual. The checkbox starts off each editor session.

The argument is the **preset's internal display name**, not the filename. For a preset named `My balance`, native usage is:

```text
KWIPv3.exe -stats "My balance"
```

No `-badnews` option is needed. The parser at `0x42D03F` enumerates slots 00 through 29, compares the following argument against the 60-WCHAR preset titles, enables flag `0x10`, and resolves the matched slot to `UCONFIG/UCONFIG_##.cfg`. The non-multiplayer startup path at `0x457C97–0x457CB8` applies that file to the unit definitions. These are native game paths, not a campaign carry-over exploit.

The launcher checks that the selected file is in this game's UCONFIG folder, uses a supported slot and has a unique valid title. It refuses ambiguous names instead of loading the first matching preset silently. It does not copy or rename unit files, modify campaign maps, or bypass scripted mission availability/global-tech restrictions. New-mission play and transitions between campaign missions still need manual verification; existing savegame entities may retain saved state.
