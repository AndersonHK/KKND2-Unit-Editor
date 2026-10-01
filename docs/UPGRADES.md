# Building upgrades

The **Upgrades** tab edits building benefits across tech levels **0–5**, shared by all three factions. Each row has a name and a short unit/effect description, with one editable value per level. Stock values are built in. Save creates `upgrades.cfg` beside the editor; Open, Folder or `--upgrades-file` can select another file. The versioned JSON schema is `kknd2-editor-upgrades`, version 1. Personal settings are Git-ignored and saves create no backups.

Use **Launch game** to apply these values. They do not change the original UCONFIG schema or the executable on disk. Keep the same settings when loading a saved game. New curves should be tested in a fresh match; an already-running production/research bill keeps the rate calculated when it started.

| Row | Meaning | Stock levels 0–5 | Allowed |
| --- | --- | --- | --- |
| Research lab upgrade cost and time | Multiplier for upgrading the **lab itself to this level** | 1, 1, 1, 1, 1, 1 | 0.1–10 |
| Power station oil yield | RU earned per unit of delivered oil | 1, 1.05, 1.10, 1.15, 1.20, 1.25 | 0.1–3 |
| Repair and healing rate | HP per repair update at normal speed (512) | 2, 3, 4, 5, 6, 7 | 0.1–32 |
| Outpost construction speed | Ordinary building construction multiplier at the highest owned Outpost tier | 1 at every level | 0.1–10 |
| Infantry production speed | As above, for infantry producers | 1 at every level | 0.1–10 |
| Vehicle production speed | As above, for vehicle producers | 1 at every level | 0.1–10 |
| Armoury construction speed | Defense/wall construction multiplier at the highest owned Armoury tier | 1 at every level | 0.1–10 |

Values accept up to two decimal places. Curves may be non-linear: each column is independent. Production 2 means approximately half the build time; 0.5 means approximately twice the time. Cost is unchanged. The native billing system's integer rounding, minimum progress and game-speed adjustments still apply, so very cheap/fast builds may not scale exactly. Rates saturate at the signed 16-bit AI billing limit rather than overflowing. Stock 1× values preserve the original calculation exactly.

## Research lab example

Set **level 5 to 2** to make upgrading a research lab **from level 4 to 5** cost twice as much cash and take approximately twice as long as another building researched by the same lab. Columns 1–5 refer to destination levels. Column 0 is retained for the complete six-level schema but has no upgrade into it.

This does **not** multiply research performed on other buildings. **Overrides** still controls base research cost/time and their lower-tier surcharges. Those values are not moved or replaced. Research progress uses the same adjusted total as billing, including when a saved game rebuilds the progress display. AI research applies the lab-specific multiplier too, on top of its existing cost/time rules. Its strategic preference for researching the lab is unchanged.

The launcher rejects settings whose lab multiplier and research base/step combination could exceed the signed 16-bit research counter (32,767 RU). Cash is rounded to whole RU. AI difficulty modifiers and native minimum progress can affect the final duration.

## Other benefits

Oil yield applies at refining, independently of tanker capacity and loading/unloading rates. Values below 1 discard some delivered oil value. Native 16.16 arithmetic rounds payout down; untouched stock cells retain their exact original bytes, including the slightly rounded 5% increments. A yield of 3 with the maximum 10,000-unit tanker stays below the signed 32-bit multiplication limit.

Repair/healing values describe each repair update, **not HP per second**. The existing update scheduling, game-speed scaling, healing eligibility and maximum-health clamp remain. The rate has 1/128 HP precision at normal speed, so some decimal inputs are rounded to that granularity.

Infantry/vehicle production multipliers use the specific human player's production-menu owner and its current tier. Outposts and Armouries unlock placeable structures rather than producing mobile units: their construction multipliers apply to the placed structure's build progress. Ordinary buildings use the highest owned Outpost tier; defenses/walls use the highest owned Armoury tier for that player. For example, Armoury level 3 at 2 makes a newly placed defense take approximately half its normal build time, without changing its cost. This is the producer's existing tech tier, not the tier of the structure being built. Construction captures the adjusted billing rate at placement; upgrading the Armoury later does not change builds already underway. Saving/loading retains that rate without multiplying it again. AI unit production uses its selected producer. AI construction has one shared queue: ordinary buildings use the highest owned Outpost tier; defenses/walls use the highest owned Armoury tier. Existing unlock requirements, armour bonuses, radar effects and building limits remain independent.

Each cell displays its **default | delta** below the entry. Blue means unsaved, amber means different from stock. Focusing a cell shows its saved value and allowed limits in the status line. The shared **Unsaved / Defaults** review dialogs list each changed row and level. Undo, Redo, Revert saved, Reset defaults and Different from defaults work as on the other settings tabs.

## Implementation and verification

Business logic is compiled freestanding x86 C++ in [`native/upgrades.h`](../native/upgrades.h), included in the same payload as the behavior fixes. [`upgrades_patch.py`](../src/kknd2_editor/upgrades_patch.py) contains the version-specific bridge. All original sites are checked before any process writes, and the executable hash must match the supported KWIPv3 build.

| Site | Purpose |
| --- | --- |
| `0x5285DC` | Six oil-yield DWORDs, stock 65536, 68813, 72090, 75367, 78644, 81921 |
| `0x4D5A90` | Repair tier rate and equivalent, overflow-safe fixed-point speed scaling |
| `0x45EE4F` | Human menu production billing, including reconstruction after load |
| `0x419A89` | AI selected-producer billing rate |
| `0x419C6D` | AI shared construction billing rate |
| `0x4652B7` | Player placement construction rate stored in the construction record; native save/load restores this already-adjusted value |
| `0x4947CD` | Lab research's initial remaining cost |
| `0x494528` | Research bar total, replacing the older denominator-only fix |
| `0x406E8B` | Research bill total during saved-game reconstruction |
| `0x419DBC` | AI lab-specific cost/time adjustment |

Tests execute the compiled adapters and original range/billing/repair instructions with synthetic state in Unicorn. They cover all tiers, all factions, lab destination levels, non-lab research, the restored research denominator, producer class selection, player-placed buildings/defenses/walls across factions and restoration of the adjusted construction rate, fixed-point payout and ABI preservation. This is not a substitute for manual fresh-match, save/load, campaign and multiplayer testing.
