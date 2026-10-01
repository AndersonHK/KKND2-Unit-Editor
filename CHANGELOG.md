# Changelog

## 0.3.1 — 2026-10-01

Confirmed in manual playtesting; 117 automated tests passed.

- Increase Acquisition Range from 32 to 96 world pixels (three tiles), retaining sight checks, in-range priority and normal firing range.
- Fix zero-damage targets remaining selectable by the attack cursor, manual/group orders and Fight fallback searches; clear failed-search output so rejected targets cannot become pursuit orders.
- Restore Fight's sight-wide passive-building fallback with Acquisition Range enabled.
- Connect idle ground acquisition to native pursuit/pathfinding and its transition into firing range; keep firing-only turret scans at their real range.
- Fix Outpost/Armoury speed multipliers bypassed by player placement; label these as construction speed and preserve the adjusted rate across save/load.
- Add Armor Type below Armour in Unit editor: Infantry, Vehicle, Beast, Aircraft and Building, with named defaults and comparisons.
- Save armor enums in version 2 per-preset extensions, preserving native CFG bytes and importing existing burst-only companions.

## 0.3.0 — confirmed in manual testing

- Add Upgrades: six levels of refining yield, repair/healing rates, production speed by producer class, and research-lab self-upgrade cost/time multipliers.
- Preserve existing research base/step controls; lab multiplier columns select the destination tier.
- Add opt-in Acquisition Range: mobile search extends one tile within sight, with in-range targets first and unchanged firing range.
- Add versioned, ignored upgrades.cfg with defaults, comparisons, history and no backups; import old Fixes files with the new toggle off.
- Keep two-line row labels, shared toolbar and live high-DPI resizing.

## 0.2.2 - 2026-09-11

- Add Burst Count to Unit editor for supported vehicle turrets, including the Anaconda's actual two-shot default. Integrate defaults, comparisons, filtering, undo/redo and saving with native unit edits.
- Save new unit fields in versioned `UCONFIG_nn_ext.cfg` companions, without changing the original CFG schema or creating extension backups. Preserve the native preset title so the game's file scan remains compatible.
- Apply extended values through the launcher after checking the supported turret data. Limit bursts to 127 because the runtime counter is signed 8-bit.
- Enlarge the campaign text and checkbox with cached DPI-scaled artwork while retaining native checkbox keyboard behavior and live layout.

Manual playtesting reported working features and no regressions on 2026-09-11. Validation also includes 81 automated tests, native instruction checks, suspended-process patch verification and packaged GUI startup. No personal settings are included.

## 0.2.1 - Included in 0.2.2

- Fix Shift-repeat placement skipping the native per-building limit/menu update.
- Make the AI solar/thermal construction ceilings use the corresponding faction's Building Limits values.
- Add Use in campaign for the selected unit preset, using the native `-stats` option with name/path validation.
- Document separate Anaconda turret burst counts, research-tier effects and remaining research work.

These changes are included in the manually tested 0.2.2 release.

## 0.2.0 - 2026-09-09

First standalone Windows x64 package. Includes the editor improvements developed since the original source-only unit/building editor:

- Grouped Overrides tab for research costs/times and tier steps, tanker capacity, oil transfer, passive incomes and placement reach; research progress-bar correction.
- Faction-specific Tech unlocks tab and Projectiles tab with supported speed/expiration controls.
- Fixes tab with Shift build, zero-damage filtering and damage-class target priority, implemented in a compiled C++ module loaded by the launcher.
- Cost cap extended to 10,000 and reload-time cap to 600, with documented units and limits.
- Shared toolbar, readable stat rows, live resizing, high-DPI layout and wrapping tabs.
- Standalone GUI EXE, portable settings beside the EXE, version metadata, quick-start documentation, ASCII-formatted release readme and repeatable release packaging.

New gameplay behavior remains opt-in where indicated and needs broader manual match testing. Existing personal configurations are not part of the release.
