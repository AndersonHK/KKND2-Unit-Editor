// Verified KWIPv3 ABI. See docs/FIXES.md for hook sites and validation.
#pragma once
typedef unsigned char Byte;
typedef unsigned int Word;
struct Unit;
struct Target { int type; Word object; Word identity; Word z; };
template<class T> inline T field(const void* object, Word offset) {
    return *reinterpret_cast<const T*>(reinterpret_cast<const Byte*>(object) + offset);
}
namespace kwip {
    const Word definition = 0x60, turret = 0x64, turret_definition = 0x10;
    const Word direct_weapon = 0x64, turret_weapon = 0x1c;
    const Word damage_class = 0x9c, damage = 0x18;
    const Word modifiers = 0x565438, left_pressed = 0x5652cc;
    const Word shift = 0x10;
    const int placement_success = -0x5c;
}
typedef int (__fastcall *Selector)(Unit*, Target*);
typedef int (__fastcall *Validator)(Unit*, Target*, Target*, Word);
