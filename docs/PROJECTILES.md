# Projectiles

The Projectiles tab edits weapon travel independently of the Unit editor's firing range. Search by unit name or internal ID, filter by faction, and select a projectile. Value, Default, Delta and Saved work like the Unit editor. Revert saved and Reset defaults affect the selected projectile; Undo/Redo and the review dialogs cover the whole projectile configuration.

The browser lists 58 weapon definitions used by buildable units and defenses, including secondary weapons. It currently exposes 33 verified speed fields and seven homing expiration counters. Instant-hit, flame, radiation, self-destruction and other specialized effects remain visible with an explanation rather than a misleading generic speed control. Bonus/mission-only weapons are outside this first catalog.

## Speed

Speed is the native integer velocity magnitude, in **1/256 world-pixel units per velocity step**. For example, 1,280 corresponds to a magnitude of five pixels before game-speed scaling. This is not pixels per second or monitor frames per second. Direction-table rounding and the simulation's movement scheduling also affect actual travel.

Allowed values are **16–2,048**. Several flight routines divide by `speed >> 4`, so 0–15 would produce a zero divisor. The upper editor bound is the largest stock speed in this verified catalog; it is deliberately conservative pending collision/granularity testing. It is not a universal guarantee that every projectile behaves correctly at every allowed speed. A faster projectile can change accuracy, visual flight, and collision behavior.

Straight projectiles and ballistic shots calculate their travel duration from distance and speed, rather than using the homing missile's fixed expiration counter. Bombs have their own impact handling. The UI explains when there is no fixed timer to edit.

## Expiration

Homing missiles start with **34 homing updates** and decrement an unsigned byte counter. The Projectiles tab permits **1–255 updates**, independently for each of the seven exposed missile definitions. These are not milliseconds; elapsed time depends on game speed and scheduling. Increasing expiration does not prevent early impact or termination when the target disappears.

The Survivors Rocketeer normally has firing range 224 but a separate speed of 1,280 and lifetime of 34. Raising only the unit's range allows shots beyond the original travel budget. Increase the Rocketeer's expiration here to test a longer range without also changing other factions' missile timers. A trial value such as 68 doubles the update budget; it is an experiment, not a guaranteed range conversion. The editor does not automatically rebalance your unit or projectile settings.

## Saving and launching

`projectiles.cfg` uses UTF-8 JSON, schema `kknd2-editor-projectiles`, version 1. Its `projectiles` mapping contains all supported `ID.speed` and `ID.lifetime` keys. The [stock example](../examples/projectiles.example.cfg) contains the complete schema. IDs identify weapon definitions, not installation paths.

Defaults are embedded. A missing personal file is created on Save or Launch game. Open… and Folder… select another preset. Saves are atomic, detect external changes, and create no `.bak` files. Personal files and temporary files are ignored by Git.

Launch game saves all tabs and applies projectile settings to the new KWIPv3 process. Select your unit configuration in the multiplayer lobby as before. Restart through the editor after changing projectile settings. Other network players must use matching presets. The executable on disk remains unchanged.

## Native evidence and validation

All addresses refer to the supported KWIPv3 SHA-256 documented in the README. Weapon definitions use their handler pointer at `+4` and speed at `+0x14`. Verified speed consumers include `0x4E13D4` (direct), `0x4E1959` (ballistic), the bomb routine beginning `0x4DFCB3`, and the homing routine beginning `0x4E1CD7`.

The homing initializer at `0x4E1C99` loads the projectile instance and writes 34 at instance offset `+0x50`. The countdown at `0x4E1FF6` decrements that byte; `0x4E200F–0x4E2017` zero-extends it for the expiration check. The launcher installs a helper only when a timer differs from stock. The helper identifies the weapon through instance `+0x4C`, supplies its chosen timer, and preserves registers/flags; unlisted or unchanged weapons retain 34.

All handler pointers, speed defaults and the complete overwritten instruction span are checked before any feature writes process memory. Tests exercise per-type timer isolation, 1/127/128/254/255 boundaries, untouched fallback behavior, register/stack preservation, configuration validation and GUI actions. These checks do not substitute for manual gameplay tests of long shots, moving targets, lost targets, high game speeds, save/load and consecutive matches.
