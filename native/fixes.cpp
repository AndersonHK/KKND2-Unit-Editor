// Freestanding x86 C++: no CRT, imports, heap, threads or initialization code.
#include "kwip_abi.h"
#define EXPORT extern "C" __declspec(dllexport)

// Filled by the launcher before the suspended game starts.
extern "C" {
    __declspec(dllexport) Word zero_damage = 0;
    __declspec(dllexport) Word damage_priority = 0;
    __declspec(dllexport) Selector original_near = 0;
    __declspec(dllexport) Selector original_wide = 0;
    __declspec(dllexport) Validator original_validate = 0;
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

EXPORT int __fastcall validate_target(Unit* unit, Target* target, Target* auxiliary, Word flags) {
    const int result = original_validate(unit, target, auxiliary, flags);
    if (result == 4) return result; // Native generation-ID check rejected a stale target.
    const int type = target_class(target);
    if (type < 0 || type >= 5) return result;
    const Byte* current_weapon = weapon(unit);
    if (current_weapon && zero_damage && field<short>(current_weapon, kwip::damage + type * 2) == 0)
        return 4; // Reject even out-of-range targets, so zero damage does not cause pursuit.
    if (search && search->unit == unit && !(search->classes & (1u << type))) return 4;
    return result;
}

static int select_target(Selector original, Unit* unit, Target* target) {
    const Byte* current_weapon = weapon(unit);
    if (!damage_priority || !current_weapon) return original(unit, target);
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
EXPORT int __fastcall select_near(Unit* unit, Target* target) { return select_target(original_near, unit, target); }
EXPORT int __fastcall select_wide(Unit* unit, Target* target) { return select_target(original_wide, unit, target); }

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
