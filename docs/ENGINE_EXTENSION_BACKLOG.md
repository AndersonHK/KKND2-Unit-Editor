# Engine extension backlog and existing research

Updated 2026-09-09. Implemented: editor cost cap 10,000, reload cap 600, raw Overrides, and Tech unlocks. See [Overrides](OVERRIDES.md) and [Tech unlocks](TECH_UNLOCKS.md). Automated/native patch checks do not replace the pending manual gameplay tests. Unchecked items below remain research or proposed work.

## Start with existing work

Search for existing implementations and documentation before reconstructing another engine subsystem. For each candidate, record the supported executable, actual implemented coverage, and what transfers to KWIPv3. A repository's name or README is not proof of a complete engine implementation.

### Closest match: ucosty/kknd2

[KKND2: Reverse Engineered](https://github.com/ucosty/kknd2) reconstructs functions as C++ and redirects calls from the original game into a `DSOUND.dll`. Its README describes imports for game functions and globals, plus replacement hooks. This is a concrete precedent for incremental native extensions without a complete engine rewrite.

The documented target SHA-256 is `9907da8cd86269045e2c06c06cddd63383c2d208ab4903963c21174f96021295`. Read-only hashing confirmed that this matches the installed **original KKND2.exe**, not KWIPv3. Our supported KWIPv3 hash and addresses remain different.

Inspected material:

- [Function list](https://github.com/ucosty/kknd2/blob/main/docs/function-list.txt): useful original-build address/name references, with many functions still unidentified.
- [DLL entry and hooks](https://github.com/ucosty/kknd2/blob/main/src/dllmain.cpp): relative jumps redirect initialization, level loading, decompression, allocation, and a building-menu routine into C++.
- [Types and imports](https://github.com/ucosty/kknd2/blob/main/src/types.h): calling-convention-aware imports and partial structures; research option IDs agree with the local investigation.
- Level, initialization, and Windows code are present. The inspected project does not supply completed targeting, projectile physics, or unit collision replacements.

Use it as a reference for subsystem boundaries and original addresses; match functions into KWIPv3 by code and callers, never by assuming a constant address offset. A runtime module for our build still needs byte/hash checks, audited calling conventions, register/stack preservation, and compatibility testing. The inspected repository has no declared license; do not vendor its implementation into this public project without resolving reuse terms. None was copied or installed here.

### Other leads

- [KWIP original release and author discussion](https://www.indiedb.com/downloads/kwip-high-res-patch-for-kknd2): Mutekx's binary distribution and compatibility/resolution notes. No public KWIP source or rebuild instructions were found in this search. That does not establish that private or unindexed source does not exist. A same-name GitHub account is not confirmed to be the same person.
- [pquerner/kknd2-patches](https://github.com/pquerner/kknd2-patches): a small Python patch repository with a WASD patch module; potential input-hook reference, not evidence of KWIP source or attack-move support.
- [ucosty's archive research](https://www.ucosty.io/articles/kknd2-archive-format), [map viewer](https://github.com/ucosty/kknd2-mapview), and [entity parser](https://github.com/ucosty/kknd2-cplc-parser): existing asset and map tooling. The [entity article](https://www.ucosty.io/articles/kknd2-buildings-and-units) explains CPLC entity records and Creature.klb metadata. These do not establish runtime collision dimensions.
- [OpenKrush](https://github.com/IceReaper/OpenKrush): an OpenRA-based remake, useful for asset-format research but a different engine from KWIPv3.
- [Interview with the 2026 update developers](https://www.remastered.blog/kknd-update-without-source-code-interview/): describes reverse engineering and replacing networking behavior despite missing original source, plus asset decompilation/recompilation tooling. This is direct testimony about the newer update, not KWIP's development history. The [publisher's Steam page](https://steamcommunity.com/app/1292180?l=english) reports the update released on August 14, 2026. Its modding tools warrant inspection; no updated executable was installed or assumed compatible here.

## Proposed native extension: working concept “KWIPv3M”

Keep Python for configuration and launch, with a separately compiled 32-bit C++ module for gameplay. Redirect only the verified functions we need while continuing to use KWIPv3's rendering, pathfinding, and other existing behavior. Small instruction patches remain appropriate for constants; stateful behavior belongs in named, testable native functions.

An extension module is enough to change the code the game executes. A separately rebuilt full EXE is not a prerequisite. Shipping our own module/patch source also avoids putting game executables in this repository. A permanent EXE patch could be a later packaging choice, but does not remove the same compatibility work.

First prove a no-change hook, then the in-range-first acquisition policy described in [the combat research](OVERRIDES_RESEARCH.md). Attack-move must retain its destination, pause for eligible enemies in firing range, then resume. Wider autonomous acquisition must check in-range opportunities during pursuit and choose the nearest eligible outside target only when there is no in-range target.

## Backlog

- [x] Overrides tab: base research cost/time, both lower-tier surcharge steps, and global tanker capacity; shared toolbar and defaults/delta/saved behavior.
- [x] Independent raw rig loading and powerplant unloading coefficients, with partial-transfer and resource-conservation checks.
- [x] Tech unlocks tab: 106 faction-specific unit/building levels and required producer labels.
- [ ] Manual gameplay validation of overrides and unlocks: AI progression, transfer cycles, save/load, and consecutive matches.
- [x] Compiled C++ native fixes module with verified KWIPv3 bridges; see [Fixes](FIXES.md).
- [ ] In-range-first, nearest-outside acquisition with deterministic ties and pursuit reevaluation.
- [ ] Destination-preserving attack-move, synchronized orders, save/load, and cancellation.
- [x] Projectiles tab: 33 verified speed fields and seven per-type homing expiration timers, with embedded defaults and an ignored personal CFG.
- [ ] Extend the projectile catalog beyond buildable-unit weapons and establish higher speed bounds from update granularity and collision handling.
- [x] Placement reach and shared solar/thermal-class income overrides; research-bar billing-index correction.
- [x] Shift-repeat placement, zero-damage filtering and damage-class target priority in the Fixes tab.
- [ ] Manual gameplay validation of fixes: cancellation/availability, mixed armies, large battles, network play and save/load.
- [ ] Separate graphical scale, selection bounds, unit collision size, and building placement/pathfinding footprint overrides.
- [ ] Optional acceleration/deceleration, first for a limited ground-vehicle prototype.

## Projectile speed and simulation granularity

The initial projectile editor uses the largest observed stock catalog speed (2,048) as a conservative upper bound. No verified universal speed cap is available yet. Identify projectile definitions, update cadence, coordinate format, movement integration, hit tests, lifespan, and impact handling separately for straight shots, homing missiles, arcs, and instantaneous effects.

For a sampled update, travel per step is `speed * simulation_dt`. If a hit test checks only the new position, a projectile can cross a target between samples. Its bound depends on target size and the smallest intersection along the trajectory, not just a tile's width; grazing hits defeat a simple diameter-based guarantee. First determine whether KKND2 already tests the swept segment, clamps arrival, or uses another impact rule.

If needed, a native replacement can test the previous-to-next movement segment, clamp to the first impact, or use bounded substeps. Homing turn rate and target movement need separate tests. Swept collision can reduce tunneling but does not remove arithmetic, lifetime, map-boundary, or steering limits. Do not expose an arbitrary high cap on the strength of the storage width alone.

Validation: small and large targets, crossing targets, grazing trajectories, maximum game speed, short shots, map edges, target death, high projectile counts, and repeated multiplayer simulation. Measure against simulation updates rather than monitor refresh rate.

## Graphical and collision size overrides

Treat these as distinct settings. Nothing inspected proves a universal “size” field that safely changes all of them.

**Graphical size:** investigate scaled/repacked sprite frames or a renderer hook. Asset preprocessing can cache resized frames, avoiding per-frame scaling cost. Runtime scaling enables adjustable sizes but needs clipping, transparent pixels, depth ordering, and draw bounds. Both need consistent origins, directional frames, shadows, turret offsets, muzzle points, and destruction animations. A larger picture alone does not establish a larger collision object.

**Selection size:** clicking/hit selection may use separate bounds; verify and adjust independently so visible units remain selectable without blocking nearby selections.

**Physical footprint:** identify unit avoidance/occupancy, projectile hit geometry, and building placement/pathfinding footprints separately. A smaller unit radius is ineffective if pathfinding still treats it as occupying the old cells. Changing building size can also affect entrances, production exits, docking, queues, and placement validation. A single modified bound risks visual overlap or units unable to traverse spaces they appear to fit through.

Start with one vehicle and one building, and compare four independent outcomes: rendered size, selection area, navigation clearance, and damage hit area. Existing asset tooling is a starting point; runtime collision field locations and safe bounds remain unverified.

## Acceleration and deceleration

Feasible in principle through movement integration hooks; no existing general acceleration setting has been established. The game need not gain a full rigid-body physics system.

A first prototype can retain the engine's path and desired direction while approaching desired speed by an acceleration limit each simulation update. Braking begins early enough to stop near a waypoint or attack position. In a continuous approximation, stopping distance is `v*v/(2*deceleration)`; discrete steps require an arrival clamp and margin. Start with scalar speed ramping, leaving lateral inertia and sliding out of scope.

The new state is per unit, not a shared modification to the unit-definition speed. Store it safely through spawn/destruction, ID reuse, save/load, and repeated matches. Use deterministic fixed-point arithmetic tied to simulation time. Zero acceleration must have a defined meaning such as disabled/instant speed change, rather than a division-by-zero or permanently stationary unit.

Check turning, tight waypoint corners, congestion, docking, reverse/retreat orders, firing stops, and interruptions by attack-move. Existing avoidance may assume an immediate stop; braking must not carry a vehicle through blockers. Air units and homing projectiles should remain separate follow-up work because their motion rules can differ.

## Next research milestone

Build an executable/version map from the existing function list and local evidence, inspect the available asset SDK, then locate the smallest no-change hook that can be validated in KWIPv3. This establishes a reusable base for gameplay work before increasing the amount of new C++.
