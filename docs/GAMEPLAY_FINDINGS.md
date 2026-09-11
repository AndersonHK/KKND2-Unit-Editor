# Combat, research and placement findings

This investigation targets the exact KWIPv3 build supported by the launcher. It combines read-only executable analysis with native instruction emulation; gameplay outcomes still need manual testing.

## Research bar starts partially filled

The research-start routine charges using the **research lab's** index: lab state `+0x4A` selects the cost/time arrays, and remaining cost is stored at `+0x4C` (`0x4947C3–0x4947D5`, `0x49488C` onward).

The original progress-bar routine instead selects its total cost using the **target building's** index (`0x49451F–0x494536`). Consequently the remaining amount and the denominator can disagree immediately. This is a display error, not evidence that a fraction of the research really completed for free.

For example, with base cost 250 and cost step 50, lab index 3 gives cost 350, while target index 0 gives 500. Comparing 350 remaining with a total of 500 makes the bar appear approximately 30% complete. A larger surcharge makes the mismatch more visible. Changing research time can coincide with noticing it, but that denominator is cost-based.

The launcher now changes the denominator lookup to use the lab index immediately before the remaining-cost field. Billing speed and resource charges are unchanged. Tests cover all 36 lab/target index combinations. Start a new research after relaunching; an old save made with different research settings need not have a remaining amount compatible with the new costs.

The new [Fixes tab](FIXES.md) can opt into zero-damage filtering, damage-class priority and Shift-repeat placement. The following targeting observations describe the unmodified game.

## Zero damage does not generally mean “cannot attack”

Target eligibility and damage are separate. The native weapon has ground/air eligibility flags at weapon `+0x34`; acquisition/range code uses those flags. The five per-class damage values are signed words starting at `+0x18`. The UCONFIG damage setter (`0x42DD83–0x42DDF6`) writes the damage word and does not rewrite the targeting flags.

Setting a class's damage to zero therefore does not generally disable selecting or attacking that class. An otherwise eligible target can still be fired upon, with zero ordinary damage from that damage component. Setting aircraft damage above zero likewise does not by itself make a ground-only weapon acquire aircraft. Special weapons, multiple weapons and scripted effects can have additional behavior. AI desirability calculations may also respond to damage; that is distinct from a class eligibility switch.

## Building placement reach

The placement preview/acceptance routine `0x466E17` searches neighboring tile cells for a qualifying friendly base building. The standard search acceptance bounds are `[x-R, x+width+R-1]` and `[y-R, y+height+R-1]`, with stock `R=5`. This is a rectangular/Chebyshev-style grid reach, not a circular pixel radius. A neighboring occupied cell five cells from the footprint's last occupied cell leaves four clear intervening cells.

The Overrides control updates all eight bound/search instructions at `0x466E81`, `0x466E8E`, `0x466E98`, `0x466EA1`, `0x466EAA`, `0x466EC1`, `0x466ED1`, and `0x466EE8`. Normal buildings and towers use R. Advanced wall types (category 6, subtype other than 1) retain the native one-cell outer allowance. The separate wall-connection logic remains unchanged.

The search uses the bounds-checked tile lookup at `0x444850`. Terrain occupancy, ownership, eligible base-building flags, visibility and availability checks remain intact. The editor allows R from 1 to 32; larger search areas cost more work while moving the placement preview. This changes the player's placement acceptance path, not AI base-layout strategy.

## Solar and thermal income

All three factions' solar-class definitions use the same payout routine (`0x40EF89`): **7 resource units per payout**. Thermal-class definitions use `0x40EF46`: **21 resource units per payout**. The two Overrides fields change these independently, across all factions, including 0 to disable that income.

Both routines schedule a delay of 360 game-time units. The scheduler scales this by `256 / gameSpeed`; at game speed 512 and 60 simulation updates/second that is approximately 3 seconds. This is income per payout, not per second. The payout interval and tanker refining remain unchanged.

## Shift-repeat placement feasibility

The game already has a persistent placement loop (`0x466724`), per-pass availability checks, a synchronized placement command (`0x466CEE–0x466CF3`), and cleanup after a successful placement. This makes retaining the placement action while Shift is held a plausible small native UI change, rather than a new building-production system.

This is now implemented as an opt-in [Shift build fix](FIXES.md#shift-build). After accepted command submission it preserves the pending count and, from 0.2.1 onward, runs the native success-time instance-cap/menu check before deciding whether to retain the preview. The original 0.2.0 menu-only recheck missed this and allowed Shift builds above the cap. Emulator checks cover actual cap comparisons, cleanup, the adapter and availability paths; full gameplay validation remains necessary. Manual tests need ordinary buildings, towers, walls, the last allowed instance, loss of the producer, insufficient funds, right-click cancellation and network delay.

## Larger art and collision footprints

Enlarging artwork and enlarging physical size are separate changes. Offline sprite conversion can scale all frames and cache the result. It must also account for origins, turret/muzzle offsets, shadows, directional frames, destruction animations, clipping and sorting. Vehicle avoidance, selection and projectile hit geometry may use separate bounds. Buildings additionally involve a tile occupancy mask, placement preview, pathfinding and entrances/exits/docking. The current preview allocates 20 footprint overlay slots (`0x467342`); increasing footprint dimensions beyond that cannot be treated as a simple width/height edit.

Existing work is useful: [ucosty's archive unpacker](https://github.com/ucosty/kknd2-unpack) extracts the archives, and the [unit/building format research](https://www.ucosty.io/articles/kknd2-buildings-and-units) documents CPLC map entities and Creature.klb metadata. That article leaves sprite parsing as future work; these tools are not an established “resize graphics and collision” pipeline.

A one-vehicle/one-building prototype is manageable work to investigate. A general reliable scale control is a larger feature and has not been implemented. Validate rendered size, selection bounds, navigation clearance, hit area and docking separately before batch-converting the rest of the game.
