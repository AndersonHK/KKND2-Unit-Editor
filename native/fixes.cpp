// Freestanding x86 C++: no CRT, imports, heap, threads or initialization code.
#include "kwip_abi.h"
#define EXPORT extern "C" __declspec(dllexport)

// Filled by the launcher before the suspended game starts.
extern "C" {
    __declspec(dllexport) Word zero_damage = 0;
    __declspec(dllexport) Word damage_priority = 0;
    __declspec(dllexport) Word acquisition_range = 0;
    typedef void (__fastcall *UnitTick)(Unit*);
    __declspec(dllexport) UnitTick original_idle = 0;
    __declspec(dllexport) UnitTick original_chase = 0;
    __declspec(dllexport) UnitTick original_chase_result = 0;
    __declspec(dllexport) Selector original_near = 0;
    __declspec(dllexport) Selector original_wide = 0;
    __declspec(dllexport) Selector original_fallback = 0;
    __declspec(dllexport) Validator original_validate = 0;
    __declspec(dllexport) Selector original_compatible = 0;
    typedef void (__fastcall *Cursor)(Byte*, Word);
    typedef int (__fastcall *Order)(Byte*, Word, Unit*);
    typedef int (__fastcall *Event)(Byte*, Word, Byte*, Byte*);
    __declspec(dllexport) Cursor original_cursor = 0;
    __declspec(dllexport) Order original_order = 0;
    __declspec(dllexport) Event original_event = 0;
}

static const Byte* weapon(Unit* unit) {
    const Byte* turret = field<const Byte*>(unit, kwip::turret);
    if (turret) {
        const Byte* definition = field<const Byte*>(turret, kwip::turret_definition);
        return definition ? field<const Byte*>(definition, kwip::turret_weapon) : 0;
    }
    const Byte* definition = field<const Byte*>(unit, kwip::definition);
    return definition ? field<const Byte*>(definition, kwip::direct_weapon) : 0;
}

// Stack-scoped filtering preserves the original selectors' spatial searches,
// visibility, alliances and tie breaking. Equal damage types share one pass.
// Selectors/validator are synchronous on the simulation thread, without yields.
struct Search { Unit* unit; Word classes; Search* previous; };
static Search* search = 0;

static int target_class(const Target* target) {
    const Byte type = static_cast<Byte>(target->type);
    if (type == 0 && target->object) {
        const Byte* definition = field<const Byte*>(reinterpret_cast<Unit*>(target->object), kwip::definition);
        return definition ? field<int>(definition, kwip::damage_class) : -1;
    }
    // The native scanner's destructible map-wall targets use building damage.
    if (type == 2) return 3;
    return -1; // Explicit ground/other special actions retain native behavior.
}

static bool zero_target(Unit* unit, const Target* target) {
    if (!zero_damage) return false;
    if (static_cast<Byte>(target->type) == 0) {
        if (!target->object) return false;
        // Do not inspect a definition through an expired/reused target identity.
        const Word identity = field<unsigned short>(reinterpret_cast<void*>(target->object), 0x212);
        if (!identity || identity != target->identity) return false;
    }
    const int type = target_class(target);
    const Byte* current_weapon = weapon(unit);
    return type >= 0 && type < 5 && current_weapon &&
        field<short>(current_weapon, kwip::damage + type * 2) == 0;
}

static Target unit_target(Unit* unit) {
    Target target = {0, reinterpret_cast<Word>(unit), field<unsigned short>(unit, 0x212), 0};
    return target;
}

// This second native predicate is used before attack-order pursuit, separately
// from the firing validator. False means incompatible, not merely out of range.
EXPORT int __fastcall compatible_target(Unit* unit, Target* target) {
    if (zero_target(unit, target)) return 0;
    return original_compatible(unit, target);
}

static bool selection_can_damage(Unit* target) {
    if (!zero_damage || !target) return true;
    const short selection = *reinterpret_cast<short*>(0x565418);
    if (!selection) return false;
    Target value = unit_target(target);
    Unit* sentinel = reinterpret_cast<Unit*>(0x5c27d8);
    for (Unit* unit = field<Unit*>(sentinel, 0); unit != sentinel; unit = field<Unit*>(unit, 0)) {
        if (field<short>(unit, 0x226) != selection || field<Byte>(unit, 0x30f) || field<Word>(unit, 0x1fc)) continue;
        // An unarmed support unit must not make a mixed selection attack-capable.
        if (weapon(unit) && !zero_target(unit, &value) && original_compatible(unit, &value)) return true;
    }
    return false;
}

EXPORT void __fastcall attack_cursor(Byte* controller, Word cursor) {
    Unit* hover = field<Unit*>(controller, 0x24);
    if (cursor == 0x1e0 && hover && !selection_can_damage(hover)) cursor = 0x214;
    original_cursor(controller, cursor);
}

EXPORT int __fastcall issue_order(Byte* controller, Word command, Unit* target) {
    if (command == 6 && !selection_can_damage(target)) return 0;
    return original_order(controller, command, target);
}

// Network/queued group commands reach each unit as event 0x30. Reject only that
// unit's incompatible attack, without editing the command shared by its peers.
EXPORT int __fastcall deliver_event(Byte* sender, Word event, Byte* argument, Byte* script) {
    if (zero_damage && event == 0x30 && argument && script) {
        const Word handler = field<Word>(script, 0x34);
        if (handler == 0x4db808 || handler == 0x487b0b || handler == 0x4af422 || handler == 0x4ac504) {
            Unit* unit = field<Unit*>(script, 0x3c);
            const Byte* command = field<const Byte*>(argument, 4);
            if (unit && field<Byte*>(unit, 0x58) == script && command && field<short>(command, 0xa) == 6) {
                Target target = {0, field<Word>(command, 0x1c), field<Word>(command, 0x20), 0};
                if (zero_target(unit, &target)) return 0;
            }
        }
    }
    return original_event(sender, event, argument, script);
}

EXPORT int __fastcall validate_target(Unit* unit, Target* target, Target* auxiliary, Word flags) {
    const int result = original_validate(unit, target, auxiliary, flags);
    if (result == 4) return result; // Native generation-ID check rejected a stale target.
    const int type = target_class(target);
    if (type < 0 || type >= 5) return result;
    if (zero_target(unit, target))
        return 4; // Reject even out-of-range targets, so zero damage does not cause pursuit.
    if (search && search->unit == unit && !(search->classes & (1u << type))) return 4;
    return result;
}

static int select_target(Selector original, Unit* unit, Target* target) {
    const Byte* current_weapon = weapon(unit);
    if (!damage_priority || !current_weapon) {
        Search context = {unit, 31, search};
        search = &context;
        const int result = original(unit, target);
        search = context.previous;
        // Fight callers inspect the output rather than the return value. Native
        // failed scans can leave their last REJECTED candidate in this buffer.
        if (!result) { target->type = 0; target->object = 0; target->identity = 0; target->z = 0; }
        return result;
    }
    short damages[5];
    for (int i = 0; i < 5; ++i) damages[i] = field<short>(current_weapon, kwip::damage + i * 2);
    Word remaining = 31;
    Search context = {unit, 0, search};
    search = &context;
    int result = 0;
    while (remaining) {
        int best = -32769;
        for (int i = 0; i < 5; ++i)
            if ((remaining & (1u << i)) && damages[i] > best) best = damages[i];
        context.classes = 0;
        for (int i = 0; i < 5; ++i)
            if ((remaining & (1u << i)) && damages[i] == best) context.classes |= 1u << i;
        remaining &= ~context.classes;
        if (zero_damage && best == 0) continue;
        result = original(unit, target);
        if (result) break;
    }
    search = context.previous;
    if (!result) { target->type = 0; target->object = 0; target->identity = 0; target->z = 0; }
    return result;
}
static int acquire(Selector original, Unit* unit, Target* target) {
    const Byte* definition = field<const Byte*>(unit, kwip::definition);
    if (!acquisition_range || !definition || field<unsigned short>(definition, 0xe4) >= 4 || !weapon(unit))
        return select_target(original, unit, target);
    // Only automatic selection sees the extra radius. Keep the native LOS,
    // alliance, minimum-range and weapon restrictions. Actual attack validation
    // runs after these pointers are restored and retains normal firing range.
    int result = select_target(original_near, unit, target);
    if (result) return result;
    Word local_definition[0x110 / 4];
    for (int i = 0; i < 0x110 / 4; ++i) local_definition[i] = field<Word>(definition, i * 4);
    local_definition[0x24 / 4] += 96;
    Byte* turret = field<Byte*>(unit, kwip::turret);
    const Byte* turret_definition = turret ? field<const Byte*>(turret, kwip::turret_definition) : 0;
    Word local_turret[0x38 / 4];
    if (turret_definition) {
        for (int i = 0; i < 0x38 / 4; ++i) local_turret[i] = field<Word>(turret_definition, i * 4);
        local_turret[0x2c / 4] += 96;
        *reinterpret_cast<const void**>(turret + kwip::turret_definition) = local_turret;
    }
    *reinterpret_cast<const void**>(reinterpret_cast<Byte*>(unit) + kwip::definition) = local_definition;
    result = select_target(original_near, unit, target);
    *reinterpret_cast<const void**>(reinterpret_cast<Byte*>(unit) + kwip::definition) = definition;
    if (turret_definition)
        *reinterpret_cast<const void**>(turret + kwip::turret_definition) = turret_definition;
    return result;
}
// Firing-only scanners must not retain an out-of-range turret target. Idle
// acquisition below owns the movement hand-off; Fight has its own pursuit.
EXPORT int __fastcall select_near(Unit* unit, Target* target) { return select_target(original_near, unit, target); }

static void resume_idle(Unit* unit) {
    *reinterpret_cast<short*>(reinterpret_cast<Byte*>(unit) + 0x2e6) = 1;
    *reinterpret_cast<Word*>(reinterpret_cast<Byte*>(unit) + 0x90) = 0x4cbd4a;
}

// Vanilla temporary pursuit starts from a move order and assumes +114 exists.
// Newly created idle units can have no command node. Do not fabricate a queue
// node; handle its missing-order exits before native code dereferences it.
EXPORT void __fastcall acquisition_chase(Unit* unit) {
    if (!field<Word>(unit, 0x114)) {
        const Byte* current_weapon = weapon(unit);
        Target auxiliary = {0, 0, 0, 0};
        const int result = current_weapon ? reinterpret_cast<Validator>(0x4a265e)(unit,
            reinterpret_cast<Target*>(reinterpret_cast<Byte*>(unit) + 0x144), &auxiliary,
            field<Word>(current_weapon, 0x34)) : 4;
        if (result == 4) { resume_idle(unit); return; }
        // After the shot, the native order dispatcher returns to idle rather
        // than leaving an orderless unit in the temporary pursuit state.
        if (result == 0) *reinterpret_cast<short*>(reinterpret_cast<Byte*>(unit) + 0x2e6) = 1;
    }
    original_chase(unit);
}
EXPORT void __fastcall acquisition_chase_result(Unit* unit) {
    const Byte result = field<Byte>(unit, 0x2f7);
    if (!field<Word>(unit, 0x114) && (result == 4 || result == 5)) {
        resume_idle(unit);
        return;
    }
    original_chase_result(unit);
}

EXPORT void __fastcall idle_acquire(Unit* unit) {
    const Byte* definition = field<const Byte*>(unit, kwip::definition);
    const Byte* current_weapon = weapon(unit);
    const Byte* turret = field<const Byte*>(unit, kwip::turret);
    const Byte* turret_definition = turret ? field<const Byte*>(turret, kwip::turret_definition) : 0;
    const Word flags = turret_definition ? field<Word>(turret_definition, 0x34) : field<Word>(definition, 0x98);
    // Only idle ground combat units: preserve hold, move, guard, special actions,
    // contained units and the native do-not-auto-attack flag. Air has its own FSM.
    if (acquisition_range && current_weapon && field<short>(unit, 0x2e6) == 1 &&
        field<unsigned short>(definition, 0xe4) < 3 && !(flags & 0x1000) &&
        !field<Word>(unit, 0x1fc) && !field<Byte>(unit, 0x30f)) {
        const Word shift = (*reinterpret_cast<const Word*>(0x51058c) >> 9) & 31;
        const Word mask = 0x7f >> shift;
        // Same staggered schedule as native infantry idle scans, not every tick.
        if (((*reinterpret_cast<const Word*>(0x55eaf8)) & mask) ==
            (field<unsigned short>(unit, 0x212) & mask)) {
            Target target = {0, 0, 0, 0}, auxiliary = {0, 0, 0, 0};
            if (acquire(original_near, unit, &target) &&
                reinterpret_cast<Validator>(0x4a265e)(unit, &target, &auxiliary, field<Word>(current_weapon, 0x34)) == 1) {
                // Native temporary pursuit remembers the real order in +114,
                // computes a path, then switches to firing at the original range.
                *reinterpret_cast<Target*>(reinterpret_cast<Byte*>(unit) + 0x144) = target;
                reinterpret_cast<UnitTick>(0x4ce727)(unit);
                return;
            }
        }
    }
    original_idle(unit);
}
EXPORT int __fastcall select_wide(Unit* unit, Target* target) { return acquire(original_wide, unit, target); }

// Fight's last-resort whole-unit-list scan never calls the firing validator.
// Keep its native traversal/distance tie breaking, but filter each candidate.
EXPORT int __fastcall fallback_candidate(Word player, Unit* candidate) {
    typedef int (__fastcall *Alliance)(Word, Unit*);
    if (!reinterpret_cast<Alliance>(0x4c61bc)(player, candidate)) return 0;
    if (!search) return 1;
    Target target = unit_target(candidate);
    const int type = target_class(&target);
    if (zero_target(search->unit, &target) ||
        (type >= 0 && type < 5 && !(search->classes & (1u << type)))) return 0;
    if (!reinterpret_cast<Selector>(0x4a9b40)(search->unit, &target)) return 0;
    Target auxiliary = {0, 0, 0, 0};
    return reinterpret_cast<Validator>(0x451370)(search->unit, &target, &auxiliary, 8);
}

EXPORT int __fastcall select_fallback(Unit* unit, Target* target) {
    // In-range targets win before Fight pursues a more distant target.
    // Preserve Fight's sight-wide fallback, including passive buildings.
    // Acquisition is an extra automatic search, not a restriction on Fight.
    int result = select_target(original_near, unit, target);
    return result ? result : select_target(original_fallback, unit, target);
}

static int __fastcall income_building_limit(const Byte* ai, Word slot) {
    const Byte* faction = field<const Byte*>(ai, 8);
    const Word building = field<Word>(faction, slot);
    const Byte* definition = reinterpret_cast<const Byte*>(0x52bed8 + building * 0x110);
    const Byte* data = field<const Byte*>(definition, 0xe0);
    return field<unsigned short>(data, 0x10);
}

// Replace only the AI planner's two literal-four comparisons. Each faction
// resolves its own building definition; budgets, priorities and tech stay native.
EXPORT __declspec(naked) void ai_solar_limit() {
    __asm {
        pushad
        mov ecx, eax
        mov edx, 014h
        call income_building_limit
        mov edx, [esp + 28]
        cmp dword ptr [edx + 094h], eax
        popad
        ret
    }
}
EXPORT __declspec(naked) void ai_thermal_limit() {
    __asm {
        pushad
        mov ecx, eax
        mov edx, 010h
        call income_building_limit
        mov edx, [esp + 28]
        cmp dword ptr [edx + 090h], eax
        popad
        ret
    }
}

static int __cdecl continue_placement(Byte* frame) {
    if (!(*reinterpret_cast<volatile Word*>(kwip::modifiers) & kwip::shift)) return 0;
    const Byte* controller = field<const Byte*>(frame - kwip::placement_controller, 0);
    const unsigned short building = field<unsigned short>(controller, kwip::selected_building);
    typedef int (__fastcall *CheckLimit)(unsigned short, int);
    // Normal success cleanup (40A9F6) calls this with include-new-placement=1.
    // The placement loop itself only tests the menu, whose icon is otherwise
    // left stale. Run the same count+1 check after EVERY accepted Shift click.
    // It reads the patched per-building cap and removes the icon at the cap.
    if (reinterpret_cast<CheckLimit>(kwip::check_building_limit)(building, 1)) {
        // The native check has removed/freed the selected menu item. Normal
        // cleanup must not call its callback or try removing it a second time.
        *reinterpret_cast<Word*>(kwip::active_build_item) = 0;
        return 0; // Keep success=1 and follow normal placement cleanup.
    }
    *reinterpret_cast<int*>(frame + kwip::placement_success) = 0;
    *reinterpret_cast<volatile Word*>(kwip::left_pressed) &= ~0x10u;
    // Re-enter the native input/placement loop below the instance cap.
    return 1;
}

// The sole mid-function adapter. Preserve the intercepted store, every register,
// flags and stack depth; only redirect the return after an accepted placement.
EXPORT __declspec(naked) void shift_placement() {
    __asm {
        mov byte ptr ds:[0565508h], dl
        pushfd
        pushad
        push ebp
        call continue_placement
        add esp, 4
        test eax, eax
        jz finish
        mov dword ptr [esp + 36], 046677eh
    finish:
        popad
        popfd
        ret
    }
}
#include "upgrades.h"
