# KWIPv3 overrides and combat-order feasibility

Historical investigation, 2026-09-09. The research/oil controls are now implemented as documented in [Raw engine overrides](OVERRIDES.md); [Tech unlocks](TECH_UNLOCKS.md) was added afterward. Timing correction: the billing constructor adds a minimum increment, applies speed scaling, and doubles its rate in 60 Hz mode; the initial time × 60 division alone does not establish wall-clock seconds or a zero-rate stall. See the current Overrides guide for the full formula. The earlier proposals below are retained as research context, not the current interface specification. In particular, the implemented controls use **absolute raw values**, including defaults, with **no multiplier or enable/inherit mode**, following the requested scope. Combat-order changes remain unimplemented. No Carnage executable was run during this investigation.

All addresses below refer to KWIPv3.exe with SHA-256 `ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44`. Addresses from other executables must not be substituted.

## Proposed Overrides tab

Add an **Overrides** tab alongside Unit editor and Building limits. Keep the existing shared toolbar in place and retain its padding, tab colours, two-line labels, expanding columns, and live resize behavior. Reuse the Value / Default / Delta / Saved presentation and the bottom Undo / Redo / Revert saved / Reset defaults actions.

Initial fields:

| Setting | Proposed scope | Evidence / status |
| --- | --- | --- |
| Base research cost | Global, resource units | Native `UPGRADECOST` option and consumers identified |
| Base research time | Global, game's configured time units | Native `UPGRADETIME` option and timer conversion identified |
| Tanker capacity | Global across factions initially, raw oil units | Shared capacity checks and cargo display identified |
| Rig loading rate | Separate multiplier, default 100% | Loading accumulator and speed-dependent transfer identified |
| Powerplant unloading rate | Separate multiplier, default 100% | Credit/debit path and transfer scheduling identified |

Use an enable/inherit setting per override. Disabled must preserve the game's own option; enabled applies the chosen value. Distinguish stock **Default**, configured override **Value**, and **Saved**: the game may already have nondefault options, which should not silently become overrides when opening this page.

Store these in a versioned `overrides.cfg` owned by this application, separate from UCONFIG and building limits. The existing `*.cfg` ignore rule covers personal overrides. A tracked example should contain only stock values and disabled overrides, with an explicit ignore exception if added. Use atomic saves and external-change detection; do not reintroduce timestamped building/settings backups.

Extend the existing suspended-process launcher to validate all selected patch sites before any write. Instructions patched in executable memory need appropriate page protection and instruction-cache flushing, unlike ordinary writable building-limit data. Apply overrides every relevant game initialization, not through a Python polling loop that races the simulation. Keep the on-disk game executable unchanged.

## Research cost and time

Research already has named native options: **UPGRADECOST** (ID `0x1A`) and **UPGRADETIME** (ID `0x1B`). The supported executable's option metadata gives cost default 250 with bounds 50–500, and time default 20 with bounds 1–40. These are the native option bounds, not newly approved wider bounds.

Evidence:

- Option metadata records at `0x5090C8` and `0x5090EC`; UTF-16 names at `0x509540` and `0x509558`.
- Getter `0x434EFF` reads `options[id]` from `0x552D74`.
- Initialization `0x494319` reads both options and rebuilds six-entry arrays: cost at `0x51B2C4`, time at `0x51B2DC`.
- For array index `i` from 0 through 5, the initializer computes `cost[i] = base_cost + 20 * (5 - i)` and `time[i] = base_time + (5 - i)`. Mapping displayed tech labels to these indices still requires verification.
- Research consumption paths include `0x406E5D–0x406EA5`, `0x4947CD`, and `0x49488C–0x4948A4`. They include a 16-bit remaining-cost value and a fixed-point resource debit rate calculated from cost/time.
- The time multiplier at `0x50E904` is 60 in this KWIPv3 file. Do not copy the original executable's 30-update timing assumptions into precise KWIPv3 elapsed-time labels without measuring the active speed setting.
- AI-related code at `0x419D52–0x419DCC` applies additional percentage factors and lower bounds. Changing research defaults must be tested with AI participants too.

**Implementation assessment:** good candidate for the first Overrides fields. Patching the derived arrays only before startup is insufficient because initialization overwrites them. Options-file integration can use native bounds; a true runtime override can replace/intercept the two initializer inputs so they are reapplied on subsequent matches. Preserve research-lab discounts unless a separate setting explicitly changes them. Wider ranges need validation of effective cost, derived timer, and nonzero debit rate, not just the input's integer width.

The [original manual](https://www.assaracos.com/_files/ugd/a1f93e_24bebc5fe2b8457daed0bd700924c024.pdf?index=true) also describes research-lab upgrades reducing subsequent research cost and duration. Carnage's own bundled readme describes its research controls as base values that retain the low-tech surcharge. That is consistent with the initializer found here, rather than evidence that Carnage's patch addresses are compatible.

## Tanker capacity

The shared tanker logic uses **400 raw oil units** as its full-load threshold. This is not necessarily the resource-unit payout: powerplant upgrade level changes the conversion.

Relevant sites:

- `0x4AAFB6`: routing decision comparing current load with 400.
- `0x4ABD3D`: full-load test in the rig loading path.
- `0x4ABDCF` and `0x4ABDDE`: cap check and clamp after loading.
- `0x4482C9`, `0x4482D2`, `0x4482F3`: cargo-bar cap and conversion to its 28-step display.
- `0x4C8A61`: another unit path initializes cargo to 400. Its calling conditions need classification before deciding whether an override should affect it (e.g. special/mission behavior).
- Unit cargo uses dword fields `+0x1A4` and `+0x1A8` in these paths. The latter serves as a fixed-point loading accumulator and later as remaining resource payout during unloading; its meaning changes by state.
- Refining factors at `0x5285DC` contain six 16.16 fixed-point values from approximately 1.00 through 1.25. Conversion occurs at `0x4AC0FE`; unloading also uses this table at `0x4AC26C`.

**Implementation assessment:** a global capacity override is feasible, but it must cover routing, filling, clamping, and display consistently. Per-faction capacity needs a lookup/hook because these instructions are shared; it is not three independent data values. Do not replace every occurrence of the number 400: unrelated code uses it for other purposes, including candidate-buffer limits.

Carnage's readme explicitly reports problems on subsequent campaign missions with its capacity patch. That is a reason to avoid blindly copying its technique. Tests must include two matches in one process, save/reload, empty rigs, and full/partial tanker loads. A verified startup instruction patch is a different approach from periodically overwriting game data.

## Loading and unloading speed

Both have distinct code paths and can plausibly become independent settings.

**Loading:** `0x4ABD5A–0x4ABDC6` calculates a transfer increment from game speed, limits it by oil available at the rig, adds it to an accumulator, debits the rig through `0x47D640`, and updates whole-unit cargo by shifting right 8. The speed expression is `(gameSpeed << 15) >> 16` before fixed-point conversion. At gameSpeed 512, this yields 256 accumulator units, or one raw oil unit per invocation. This is a per-invocation statement, not a measured wall-clock rate.

**Unloading:** `0x4AC161–0x4AC1D0` schedules transfer opportunities using simulation tick and unit identity. `0x4AC1E6–0x4AC24A` derives a transfer amount from game speed, limits it to remaining payout, credits resources through `0x45F258`, and decrements the remaining amount. The visual/raw cargo reduction is updated separately using the refining factor at `0x4AC26C`.

**Implementation assessment:** use separate rate multipliers with conservation checks. Raising capacity by itself can lengthen filling and unloading. A rate patch must preserve partial transfers, avoid creating/destroying resources through rounding, and leave rig extraction/refining yield separate from docking transfer speed. Docking, turning, and animation time may remain even with a faster transfer rate. The full safe multiplier range is not yet established.

## Unit and building cost: why 5,000?

5,000 is an editor bound, not a 5,000-sized numeric type. Definition cost is a dword at `+0x0C`; the configuration setter stores a dword. Actual production is narrower:

- `0x4344D7` reads the low word of definition cost.
- `0x4344DE` stores it in the production record at `+8`.
- `0x434503` sign-extends that word before further arithmetic.
- Another path at `0x40941B–0x409422` also copies cost as a word.
- `0x45B4BE–0x45B4CC` similarly narrows/sign-extends cost for another use.

The signed boundary is **32,767**: 32,768 becomes -32,768 in these paths. This is concrete evidence against exposing arbitrary 32-bit costs. It does not explain the designers' exact choice of 5,000; a balance/usability ceiling is plausible but remains an inference.

A modest extension above 5,000 is a reasonable candidate for testing, but 32,767 is not a certified universally safe cap. Audit modifiers, production billing, cancellation/refunds, display, and AI affordability. The editor cost cap is now 10,000 as requested; this fits the observed signed-word fields, with in-game billing/refund testing still outstanding.

## Acquisition and attack-move: required behavior

Fight mode is already useful for large armies, but its targeting must not be used as the desired behavioral specification. The required priority is:

1. Prefer a valid enemy the unit can shoot **now**, respecting minimum/maximum range, target category, visibility, and firing constraints.
2. If none is available, acquire the **nearest valid enemy** within the separate acquisition radius. Pursue that target, while continuing to check for shootable enemies encountered en route.
3. When an in-range enemy becomes available, stop pursuing the distant target and engage the local threat. Do not let threat scoring override this priority.

Within the in-range group, keep a current valid target to avoid constant switching; otherwise choose nearest, with a stable unit-ID tie break. This preserves firing cycles while enforcing the required in-range-first priority. Explicit manual target orders and Stand Ground need separate, documented behavior: Stand Ground must not unexpectedly chase.

For **attack-move**, save a destination, travel toward it, pause to engage enemies in firing range, then resume that destination. As specified, a distant acquisition candidate must not pull the unit away from this route. Stop/replacement orders cancel attack-move. Target death/loss, temporary blockage, or combat interruption must not discard its destination.

### Code found

- The narrow acquisition routine at `0x4A1893` sets a scan radius to `min(view_range, weapon_range >> 5)` at `0x4A1951–0x4A1991`. This helps explain why increasing sight alone does not make ordinary units acquire distant enemies.
- A broader candidate routine at `0x4A2039` uses the larger sight/range extent at `0x4A2124–0x4A2198` and chooses candidates using a score from `0x4A1FB8`, compared at `0x4A23F5–0x4A240F`. This is not a simple nearest-distance comparison.
- Both call common target/range validation at `0x4A265E`, including from `0x4A1B56` and `0x4A23DB`. Several movement/combat routines call the broader selector; mapping every call to the UI's Fight/Guard/other modes remains necessary. The precise function-to-Fight-key chain has not yet been proven end to end.
- The game's shipped Readme documents F as Fight mode. The [developer diary](https://planet.kknd2.com/development/) describes it as seeking visible enemies; that documentation does not establish the requested destination-preserving attack-move behavior.

**Implementation assessment:** acquisition needs a new priority policy and pursuit transition, not merely a wider search radius. Preserve weapon range for actual firing; changing the shared range validator globally could accidentally allow shots beyond weapon range or affect unrelated unit modes.

Attack-move is feasible in principle but requires more new logic: order input, a persistent destination, movement/combat state transitions, and cancellation. Reuse the game's spatial search, eligibility checks, and existing move/attack routines while adding small native hooks. Python remains the editor/launcher; gameplay hooks execute with the simulation, not in an external polling loop.

Target selection must be deterministic for network games: fixed scan cadence, stable tie-breaking, synchronized orders, matching patch settings on every client, and no wall-clock-dependent decisions. Save/load and replay representation for the extra destination/order state still needs design. Large-army tests must measure scan cost; expanding a radius increases searched area roughly quadratically.

## Suggested implementation order and validation

1. Overrides tab plus base research cost/time and global tanker capacity. Validate process bytes and repeatedly initialize matches to verify persistence.
2. Independent load/unload multipliers, with resource conservation, partial loads, exhausted rigs, upgraded refineries, and docking/queue tests.
3. In-range-first / nearest-outside acquisition in an isolated single-player prototype. Test front-line enemies versus a distant high-threat unit, minimum-range weapons, aircraft-only weapons, blocked paths, and Stand Ground.
4. Destination-preserving attack-move using that selector. Test movement interruption, target loss, resume/cancel, mixed armies, and repeated engagements, then save/load and multiplayer synchronization.

Do not claim these features supported until their engine hooks and in-match behavior have been exercised. Only the reload cap of 600 and cost cap of 10,000 are part of the current implemented editor changes. See [the extension backlog](ENGINE_EXTENSION_BACKLOG.md) for source-project findings, projectile speed, sizing, and acceleration research.
