# Tech unlock levels

The Tech unlocks tab exposes **106 unit/building entries**, with separate values for each faction. Each row identifies the production building whose level controls that entry. Levels range from **0 to 5**; zero requires no research on that producer. A value of 3 means the item becomes available at level 3 and stays available at higher levels. Other game prerequisites still apply.

| Category | Survivors producer | Evolved producer | Series 9 producer |
| --- | --- | --- | --- |
| Infantry | Barracks | Warrior Hall | Microunit Factory |
| Vehicles | Machine Shop | Beast Enclosure | Macrounit Factory |
| Buildings | Outpost | Clanhall | Barn |
| Defensive towers | Armoury | Forge | Weapon Control |

For example, the stock Survivors Laser Rifleman requires Barracks level 5. Setting it to 2 makes it available from Barracks level 2. The Evolved Spirit Archer and Series 9 Sterilizer retain their own configured levels. This does not change the infantry's cost, statistics, producer, or building instance limit.

Use the faction and Different from defaults filters, compare Value/Default/Delta/Saved, and use the same Save, review, undo/redo, revert, and reset controls as Building limits. **Launch game** saves and applies these levels along with the other tabs. A saved change does not alter a game already running.

## Indirect and special unlocks

The three deployed Drill Rigs come from their Mobile Drill Rigs, so change the mobile rig's unlock requirement. The Scourge Demon uses the Altar of the Scourge's special behavior. These four records have no independent production-list tier and are not presented as editable tier fields. The Altar itself has a building unlock level here, even though its instance limit remains locked in Building limits.

The patch does not bypass scenario restrictions, special production conditions, or missing prerequisite producers. Delaying core infrastructure can make a technology path unreachable. Moving many entries to an early tier should be tested with the native production menu and AI before using the preset for a long match.

## Settings file

`tech_unlocks.cfg` is UTF-8 JSON with schema `kknd2-editor-tech-unlocks`, version `1`, and an `unlocks` mapping of all 106 supported internal IDs to integers 0–5. The [stock example](../examples/tech_unlocks.example.cfg) contains every required key. Unknown, missing, duplicate, and invalid entries are rejected.

Missing files use the embedded stock tiers and are created on Save or Launch game. Open… chooses another preset; Folder… chooses that folder's `tech_unlocks.cfg`. Writes are atomic and detect external changes, without `.bak` files. Personal settings are ignored by Git. Game UCONFIG files and executables are not rewritten by this tab.

## Native implementation

The supported KWIPv3 tables live at `0x50E85C` (vehicles), `0x504198` (infantry), `0x51915C` (buildings), and `0x5040A0` (defences). Each points to six level lists; entries contain three faction IDs, with `0xFFFF` for an absent faction. An all-`0xFFFF` triple terminates a list. The stock data and exact original bytes are frozen in `unlock_data.py`.

The launcher verifies the original pointer blocks and lists, builds replacement lists in the suspended process, and updates those four pointer blocks. Factions can select different levels because their triples are split as needed. Producer membership, duplicate stock entries, and special non-unit commands are preserved. Stock settings need no table patch.

The native menu builder at `0x406918` visits the producer's unlocked levels and calls `0x405D46` to consume these lists. Initialization at `0x41C77B` derives another tier lookup from the vehicle/infantry/building tables, so replacing only that derived lookup would not update production menus. The defence table has separate consumers; this is not a claim that every AI decision uses one unified tier lookup.

Automated tests verify faction splitting, preservation of every stock entry and special command, schema handling, zero-level editing, and toolbar behavior. Suspended-process verification checks the real table patches. Full gameplay, AI progression, save/load, and subsequent matches still require manual testing.
