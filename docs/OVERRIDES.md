# Raw engine overrides

The Overrides tab contains absolute KWIPv3 values, grouped into Research, Oil and Tankers, and Building Placement. Each section explains its formulas above the editable rows. Values, defaults, deltas, saved values, undo/redo, and the shared toolbar work like Building limits.

Save writes `overrides.cfg`; **Launch game** applies it to the newly launched, verified KWIPv3 process. Changes do not affect an already running game. Defaults are embedded and apply even when the game has different research options. The editor does not change `Options.cfg` or the executable on disk.

## Research

For internal tier index `i` from 0 through 5:

```text
cost[i] = base cost + (5 - i) × cost step
time[i] = base time + (5 - i) × time step
```

“Lower-tech research adds up to” refers to this surcharge on the base. With stock values, index 0 costs `250 + 5 × 20 = 350` and takes `20 + 5 × 1 = 25` nominal seconds before speed scaling. Index 5 costs 250 and takes 20. It is not a sum of all earlier research purchases.

| Internal index | Stock cost | Stock nominal seconds |
| --- | ---: | ---: |
| 0 | 350 | 25 |
| 1 | 330 | 24 |
| 2 | 310 | 23 |
| 3 | 290 | 22 |
| 4 | 270 | 21 |
| 5 | 250 | 20 |

Both steps are editable. A cost step of zero removes the cost surcharge; a time step of zero removes the time surcharge. They are independent. Changing base cost to 500 while retaining step 20 produces costs 600, 580, 560, 540, 520, 500.

The research lab supplies the index used by the billing path; it is not the target building's next unlock level. The launcher now corrects the progress bar to use that same billing index. The original bar used the target building's index and could appear partly complete immediately; see [the research-bar trace](GAMEPLAY_FINDINGS.md#research-bar-starts-partially-filled). Existing lab/AI factors can affect the final calculation. The field is labeled **Seconds before speed scaling (nominal)**. In the default 60 Hz mode, speed 256 gives roughly that many seconds; speed 512 gives roughly half. This is inferred from the native calculation, not a stopwatch measurement. Rendering FPS alone is not a sufficient conversion.

The research caller first calculates `q = floor(cost × 256 / (time × F))`, where `F` is the engine timing mode (60 by default, 30 with `-thirty`). The billing constructor then calculates `r = floor(q × speedOption / 512) + 1` and doubles `r` when `F == 60`. The resource task adds `r` to its 1/256-RU accumulator each update and completes when the cost has been paid. At 60 updates/second with funds available, approximate duration is `ceil(cost × 256 / r) / 60`.

For cost 250 and time 20 at speed 512, `q=53`, `r=108`, and the calculated duration is about **9.88 seconds**. At speed 256, `r=54`, giving about **19.77 seconds**. Integer rounding means cost also slightly affects duration. At very low cost / long time, the constructor's `+1` sets a minimum progress rate, so increasing time can stop making research slower. A zero initial quotient does **not** stall this billing path. Resource shortages can delay progress.

Evidence: research caller `0x49488C–0x4948C0`; billing constructor `0x45EBB3–0x45EBD7`; resource accumulator/debit loop `0x45F3FE–0x45F4B7`; rescheduling at `0x45F701`. The earlier investigation only followed the first division and missed the downstream speed adjustment. These controls preserve the native billing behavior rather than replacing it with an exact-duration timer.

The exposed ranges keep the largest effective tier cost at 15,000 and nominal time at 800. These are conservative editor bounds, not a claim that every engine consumer supports arbitrary larger values.

## Tanker Capacity

Capacity defaults to **400 raw oil units**, shared across the three factions. Refining upgrades can increase the resource payout from that oil. Capacity and refining yield are separate concepts.

The patch covers the full-load routing decision, loading checks and clamp, cargo bar, and the unit-spawn flag that starts a tanker full. When capacity changes, loading is capped to remaining capacity before oil is taken from the rig.

## Oil Transfer

The controls replace raw integer coefficients, not percentages:

```text
load increment = floor(gameSpeed × loading constant / 65,536)
                 measured in 1/256-oil accumulator units
unload amount  = floor(gameSpeed × unloading constant / 65,536)
                 measured in resource units
```

At the runtime speed value **512**, the stock loading constant **32,768** gives 256 accumulator units, or **1 oil per loading update**. The stock unloading constant **4,096** gives **32 resource units per transfer opportunity**. Doubling a constant doubles the calculated increment before rounding and capacity/availability limits; it does not necessarily halve a complete tanker round trip. Docking, travel, turning, extraction, and the unloading schedule remain separate.

Loading retains fractional oil in the accumulator. Rig debit uses the increase in whole oil carried, preventing repeated fractional increments from creating free oil. Native rig-availability checks remain in place. Transfer helpers use a wide intermediate product and cap the result to remaining capacity or payout. The unloading minimum of 512 gives at least one resource unit at the tested runtime speed value 128; a nonstandard speed below that can still round a small coefficient to zero.

## Solar and thermal income

Solar-class buildings pay **7 RU per payout** by default, and thermal-class buildings pay **21 RU per payout**. Each class uses one shared routine across all three factions. The separate controls accept 0–10,000 RU per payout; zero stops that income. Payouts are approximately every 3 seconds at speed 512 / 60 Hz, or 6 seconds at speed 256 / 60 Hz. The controls do not change the payout interval. Both rows sit under Oil and Tankers in the UI.

## Building Placement

**Building placement reach** defaults to **5 tile cells**, allowing up to four clear cells between the new footprint and an eligible friendly building. The search includes diagonal cells and is rectangular, not a circular pixel radius. Normal buildings and towers use this reach; advanced walls retain their native one-cell extra allowance. The editor permits 1–32. Larger values increase the work done by the placement preview. Ownership, terrain, occupied cells, producer availability and building limits still apply. AI base-layout strategy and wall-connection rules are unchanged.

## Schema and defaults

`overrides.cfg` is UTF-8 JSON using schema `kknd2-editor-overrides`, version `2`, and an `overrides` mapping containing all ten keys:

| Key | Stock | Allowed |
| --- | ---: | ---: |
| `research_cost` | 250 | 50–10,000 |
| `research_time` | 20 | 1–600 |
| `research_cost_step` | 20 | 0–1,000 |
| `research_time_step` | 1 | 0–40 |
| `tanker_capacity` | 400 | 1–10,000 |
| `rig_loading_rate` | 32,768 | 1–1,048,576 |
| `powerplant_unloading_rate` | 4,096 | 512–1,048,576 |
| `solar_income` | 7 | 0–10,000 |
| `thermal_income` | 21 | 0–10,000 |
| `building_placement_range` | 5 | 1–32 |

The [complete stock example](../examples/overrides.example.cfg) can be used as a preset. Missing files start from embedded defaults and are created on Save or Launch game. Version-1 files with exactly the original seven keys load without losing values, add the three stock defaults in memory, and upgrade on Save. Opening alone never writes. Unknown/missing/duplicate keys, non-integers and out-of-range values are rejected. Saves use atomic replacement and external-change detection, with no `.bak` files. Personal configs are ignored by Git.

## Implementation and validation

`overrides_patch.py` records exact original instructions for the supported executable. Research input reads at `0x49431F` and `0x494329` are replaced with the configured bases; step expressions at `0x49434B` and `0x494362` use native helpers when changed. Consequently, subsequent match initialization uses the same overrides. Capacity sites are enumerated in `CAPACITY_SITES`. Research-bar lookup at `0x494528` now follows the billing lab. Income constants are at `0x40EF92` and `0x40EF4F`; eight placement search bounds are recorded in the patch module. Loading hooks are at `0x4ABD5A`, `0x4ABD72`, and `0x4ABDA9`; unloading is at `0x4AC1E6`.

The launcher checks the executable hash and every expected instruction/table before patching its suspended child. Helpers run inside the game's own thread; Python does not poll or modify a running simulation. Helper memory becomes read/execute after verification. A failure terminates only that new child.

Automated checks cover configuration failures, UI behavior, patch verification, and x86 helper execution across fractional/partial transfers, large products, and all research indices. Suspended-process checks verify patch placement without executing gameplay. Manual validation is still needed for AI matches, save/load, consecutive matches/campaign missions, near-empty rigs, upgraded powerplants, and the user's preferred speed settings. Use matching presets between network players.
