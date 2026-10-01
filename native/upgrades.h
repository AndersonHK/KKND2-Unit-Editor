// Building benefits for the verified KWIPv3 ABI. No imports or allocation.
// All arrays are populated before launch; factors use hundredths, never floats.
#pragma once
typedef void (__fastcall *ProductionBill)(void*, short, short*, short, int, Word, Word, short);
extern "C" {
    __declspec(dllexport) Word lab_factors[6] = {100,100,100,100,100,100};
    __declspec(dllexport) Word repair_rates[6] = {256,384,512,640,768,896};
    __declspec(dllexport) Word production_factors[24] = {
        100,100,100,100,100,100, 100,100,100,100,100,100,
        100,100,100,100,100,100, 100,100,100,100,100,100};
    __declspec(dllexport) ProductionBill original_production = 0;
}

static int tier(const Unit* unit) {
    if (!unit) return 0;
    const Byte* state = field<const Byte*>(unit, 0x68);
    int value = state ? field<short>(state, 0x4a) : 0;
    return value < 0 ? 0 : value > 5 ? 5 : value;
}

static Word producer_factor(const Unit* unit) {
    if (!unit) return 100;
    const int id = field<int>(unit, 0x5c);
    if (id < 72 || id > 83) return 100;
    return production_factors[((id - 72) / 3) * 6 + tier(unit)];
}

static int scaled_rate(int rate, Word factor) {
    if (factor == 100) return rate; // Preserve stock rounding, including zero.
    // The original AI bill stores this in a signed short. Saturate, never wrap.
    if (rate < 0) return rate;
    Word value = (static_cast<Word>(rate) * factor + 50) / 100;
    return value > 32767 ? 32767 : value == 0 ? 1 : static_cast<int>(value);
}

EXPORT void __fastcall production_bill(void* menu, short player, short* remaining,
                                       short total, int rate, Word source, Word argument, short bucket) {
    const Byte* group = menu ? field<const Byte*>(menu, 8) : 0;
    Unit* producer = 0;
    if (group) {
        typedef Unit* (__fastcall *Resolve)(unsigned short);
        producer = reinterpret_cast<Resolve>(0x4c56cf)(field<unsigned short>(group, 0x18));
    }
    original_production(menu, player, remaining, total, scaled_rate(rate, producer_factor(producer)), source, argument, bucket);
}

static Word lab_factor(const Unit* target) {
    if (!target) return 100;
    const int id = field<int>(target, 0x5c);
    const int destination = tier(target) + 1;
    return id >= 99 && id <= 101 && destination <= 5 ? lab_factors[destination] : 100;
}

static int research_total(const Unit* target, int lab_level) {
    if (lab_level < 0 || lab_level > 5) lab_level = 0;
    const Word base = reinterpret_cast<const Word*>(0x51b2c4)[lab_level];
    Word value = (base * lab_factor(target) + 50) / 100;
    return value > 32767 ? 32767 : value == 0 ? 1 : static_cast<int>(value);
}

static int __cdecl lab_start_value(const Byte* frame, int level) {
    return research_total(field<Unit*>(frame - 0x10, 0), level);
}
static int __cdecl lab_bar_value(const Byte* frame) {
    const Byte* remaining = field<const Byte*>(frame - 8, 0);
    return research_total(field<Unit*>(frame - 4, 0), field<short>(remaining - 2, 0));
}
static int __cdecl lab_resume_value(const Byte* frame, int level) {
    const Byte* progress = field<const Byte*>(frame - 0x10, 0);
    return research_total(field<Unit*>(progress, 0x10), level);
}
static void __cdecl ai_lab_values(Byte* frame) {
    Word factor = lab_factor(field<Unit*>(frame - 0x34, 0));
    if (factor == 100) return;
    int* cost = reinterpret_cast<int*>(frame - 0x14);
    int* time = reinterpret_cast<int*>(frame - 8);
    int adjusted = (*cost * factor + 50) / 100;
    *cost = adjusted > 32767 ? 32767 : adjusted < 1 ? 1 : adjusted;
    adjusted = (*time * factor + 50) / 100;
    *time = adjusted < 1 ? 1 : adjusted;
}
static int __cdecl ai_unit_rate(const Byte* frame, int rate) {
    return scaled_rate(rate, producer_factor(field<Unit*>(frame - 4, 0)));
}
static Word __cdecl repair_increment(Word level) {
    const Word speed = *reinterpret_cast<const Word*>(0x51058c);
    // Equivalent fixed-point result, without overflowing the native (rate<<8)
    // intermediate at a high game speed. A 32x32 product needs no CRT helper.
    return static_cast<Word>((static_cast<unsigned __int64>(repair_rates[level < 6 ? level : 5]) * speed) >> 8);
}
static int __cdecl ai_building_rate(const Byte* frame, int rate) {
    // AI construction uses a single global queue, not an individual menu.
    // Use its highest-tier available producer of the appropriate class.
    const Byte* ai = field<const Byte*>(frame - 0x3c, 0);
    const Byte* definition = field<const Byte*>(frame - 0x24, 0);
    const int category = field<unsigned short>(definition, 0xe4);
    const int first = category >= 5 ? 81 : 72;
    const Word player = field<Word>(ai, 0);
    if (player > 7) return rate;
    const Word head = first == 72 ? 0x19e8 : 0x2974;
    const Unit* sentinel = reinterpret_cast<const Unit*>(ai + head);
    const Unit* unit = field<Unit*>(ai, head + 0x2c + player * 4);
    int best = -1;
    // Guard a malformed list while leaving the original AI control flow alone.
    for (int count = 0; unit && unit != sentinel && count < 4096; ++count) {
        const int id = field<int>(unit, 0x5c);
        if (id >= first && id < first + 3 && tier(unit) > best) best = tier(unit);
        unit = field<Unit*>(unit, 0x2c + player * 4);
    }
    return best < 0 ? rate : scaled_rate(rate, production_factors[((first - 72) / 3) * 6 + best]);
}

// Placement starts a separate construction bill, bypassing menu production.
// Store the adjusted rate in the construction record itself, so save/load and
// progress share it and a resumed game does not apply the multiplier twice.
static int __cdecl player_building_rate(const Byte* frame, int rate) {
    const Unit* building = field<Unit*>(frame - 0x28, 0);
    const Byte* definition = field<const Byte*>(building, 0x60);
    const int category = field<unsigned short>(definition, 0xe4);
    if (category < 4) return rate;
    const int first = category >= 5 ? 81 : 72;
    const Byte player = field<Byte>(building, 0x2fc);
    const Unit* sentinel = reinterpret_cast<const Unit*>(0x5c27d8);
    int best = -1;
    for (const Unit* unit = field<Unit*>(sentinel, 0); unit && unit != sentinel; unit = field<Unit*>(unit, 0)) {
        const int id = field<int>(unit, 0x5c);
        if (id >= first && id < first + 3 && field<Byte>(unit, 0x2fc) == player &&
            !field<Byte>(unit, 0x30f) && field<const Byte*>(unit, 0x68) && tier(unit) > best)
            best = tier(unit);
    }
    return best < 0 ? rate : scaled_rate(rate, production_factors[((first - 72) / 3) * 6 + best]);
}
EXPORT __declspec(naked) void player_construction() {
    __asm {
        pushfd
        pushad
        push eax
        push ebp
        call player_building_rate
        add esp, 8
        mov [esp+28], eax
        popad
        popfd
        mov edx, [ebp-2ch]
        mov [edx+12h], ax
        ret
    }
}

// Small, audited adapters replace whole instructions. PUSHAD isolates the C++
// helpers from each game's live register set; only the documented output changes.
EXPORT __declspec(naked) void lab_start() {
    __asm {
        pushfd
        pushad
        push ecx
        push ebp
        call lab_start_value
        add esp, 8
        mov [esp+28], eax
        popad
        popfd
        ret
    }
}
EXPORT __declspec(naked) void lab_bar() {
    __asm {
        pushfd
        pushad
        push ebp
        call lab_bar_value
        add esp, 4
        mov [esp+28], eax
        popad
        popfd
        ret
    }
}
EXPORT __declspec(naked) void lab_resume() {
    __asm {
        pushfd
        pushad
        push eax
        push ebp
        call lab_resume_value
        add esp, 8
        mov [esp+24], eax
        popad
        popfd
        ret
    }
}
EXPORT __declspec(naked) void ai_lab() {
    __asm {
        pushfd
        pushad
        push ebp
        call ai_lab_values
        add esp, 4
        popad
        popfd
        mov edx, [ebp-38h]
        mov eax, [ebp-14h]
        ret
    }
}
EXPORT __declspec(naked) void repair_tier() {
    __asm {
        pushfd
        pushad
        push ecx
        call repair_increment
        add esp, 4
        mov [esp+24], eax
        popad
        popfd
        ret
    }
}
EXPORT __declspec(naked) void ai_production() {
    __asm {
        pushfd
        pushad
        push eax
        push ebp
        call ai_unit_rate
        add esp, 8
        mov [esp+28], eax
        popad
        popfd
        mov edx, [ebp-20h]
        mov [edx+44h], eax
        ret
    }
}
EXPORT __declspec(naked) void ai_construction() {
    __asm {
        pushfd
        pushad
        push eax
        push ebp
        call ai_building_rate
        add esp, 8
        mov [esp+28], eax
        popad
        popfd
        mov edx, [ebp-3ch]
        mov [edx+4912h], ax
        ret
    }
}
