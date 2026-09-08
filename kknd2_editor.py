"""Small, lossless KKND2 UCONFIG editor. Python 3.9+, standard library only."""
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import argparse
import os
import re
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

DEFAULT_FOLDER = Path(__file__).resolve().parent.parent / "UCONFIG"
FIELDS = ("Cost", "Build-Time", "Hitpoints", "View-Range", "Speed", "Armour",
          "Accuracy", "Weapon-Range", "Min-Range", "Bullet-Count", "Fire-Delay",
          "Reload-Time", "InfantryDamage", "VehicleDamage", "BeastDamage",
          "BuildingDamage", "AircraftDamage")
FACTIONS = {"SURV": "Survivors", "MUTE": "Evolved", "ROBOT": "Series 9"}


# Native KKND2 editor limits, verified against its metadata table and UI.
# These are supported editor limits, not claims about integer storage capacity.
FIELD_MAXIMUMS = (5000, 600, 10000, 41, 260, 255, 260, 510, 256,
                  250, 300, 250, 4000, 4000, 4000, 4000, 4000)
FIELD_UNITS = (
    "resource units", "seconds (normal speed)", "HP",
    "tiles", "raw movement rate", "raw armour rating",
    "raw accuracy rating", "pixels (32 = 1 tile)", "pixels (32 = 1 tile)",
    "burst count", "1/60 s ticks (normal speed)", "1/60 s ticks (normal speed)",
    "base damage", "base damage", "base damage", "base damage", "base damage",
)

def field_hint(column):
    return f"{FIELD_UNITS[column]} | max {FIELD_MAXIMUMS[column]:,}"

# English display names from the installed game, keyed by stable config IDs.
UNIT_NAMES = {
    "UNIT_SURV_GUNNER": "Machine Gunner",
    "UNIT_SURV_GRENADIER": "Grenadier",
    "UNIT_SURV_FLAMER": "Flamer",
    "UNIT_SURV_ROCKETEER": "Rocketeer",
    "UNIT_SURV_SNIPER": "Laser Rifleman",
    "UNIT_SURV_TECHNICIAN": "Technician",
    "UNIT_SURV_KAMIKAZE": "Kamikaze",
    "UNIT_MUTE_GUNNER": "Berzerker",
    "UNIT_MUTE_GRENADIER": "Rioter",
    "UNIT_MUTE_FLAMER": "Pyromaniac",
    "UNIT_MUTE_ROCKETEER": "Homing Bazookoid",
    "UNIT_MUTE_SNIPER": "Spirit Archer",
    "UNIT_MUTE_TECHNICIAN": "Mekanik",
    "UNIT_MUTE_KAMIKAZE": "Martyr",
    "UNIT_MUTE_DEMON": "Scourge Demon",
    "UNIT_ROBOT_GUNNER": "Seeder",
    "UNIT_ROBOT_GRENADIER": "Pod Launcher",
    "UNIT_ROBOT_FLAMER": "Weed Killer",
    "UNIT_ROBOT_ROCKETEER": "Spore Missile",
    "UNIT_ROBOT_SNIPER": "Sterilizer",
    "UNIT_ROBOT_TECHNICIAN": "Systech",
    "UNIT_ROBOT_KAMIKAZE": "Michaelangelo",
    "UNIT_SURV_MOBILEOUTPOST": "Mobile Outpost",
    "UNIT_SURV_MOBILEDRILLRIG": "Mobile Drill Rig",
    "UNIT_SURV_TANKER": "Oil Tanker",
    "UNIT_SURV_BIKE": "Dirt Bike",
    "UNIT_SURV_HOVERBUGGY": "Hover Buggy",
    "UNIT_SURV_ATV": "ATV",
    "UNIT_SURV_ANACONDATANK": "Anaconda Tank",
    "UNIT_SURV_BARRAGECRAFT": "Barrage Craft",
    "UNIT_SURV_AUTOCANNONTANK": "The Enforcer",
    "UNIT_SURV_JUGGERNAUT": "Juggernaut",
    "UNIT_MUTE_MOBILEOUTPOST": "Mobile Clanhall",
    "UNIT_MUTE_MOBILEDRILLRIG": "Mobile Derrick",
    "UNIT_MUTE_TANKER": "Bull Ant Tanker",
    "UNIT_MUTE_DIREWOLF": "Dire Wolf",
    "UNIT_MUTE_SCORPION": "Pit Scorpion",
    "UNIT_MUTE_CRINOID": "Crinoid",
    "UNIT_MUTE_MASTODON": "War Mastodon",
    "UNIT_MUTE_HIPPO": "Death Hippo",
    "UNIT_MUTE_CRAB": "Missile Crab",
    "UNIT_MUTE_BEETLE": "Mega Beetle",
    "UNIT_ROBOT_MOBILEOUTPOST": "Mobile Barn",
    "UNIT_ROBOT_MOBILEDRILLRIG": "Mobile Oilbot",
    "UNIT_ROBOT_TANKER": "Oil Tankeroid",
    "UNIT_ROBOT_PATROLBOT": "Patrolbot",
    "UNIT_ROBOT_RESPONSEBOT": "Responsebot",
    "UNIT_ROBOT_RADIATOR": "Radiator",
    "UNIT_ROBOT_TANKBOT": "Tankbot",
    "UNIT_ROBOT_DOOMDOME": "Doom Dome",
    "UNIT_ROBOT_CAUTERISER": "Cauteriser",
    "UNIT_ROBOT_GRIMREAPER": "Grim Reaper",
    "UNIT_SURV_OUTPOST": "Outpost",
    "UNIT_SURV_BARRACKS": "Barracks",
    "UNIT_SURV_MACHINESHOP": "Machine Shop",
    "UNIT_SURV_ARMOURY": "Armoury",
    "UNIT_SURV_POWERSTATION": "Power Station",
    "UNIT_SURV_DRILLRIG": "Drill Rig",
    "UNIT_SURV_CONVERTER": "Thermal Exchanger",
    "UNIT_SURV_COLLECTOR": "Solar Collector",
    "UNIT_SURV_REPAIRBAY": "Repair Bay",
    "UNIT_SURV_RESEARCHLAB": "Research Lab",
    "UNIT_MUTE_OUTPOST": "Clanhall",
    "UNIT_MUTE_BARRACKS": "Warrior Hall",
    "UNIT_MUTE_MACHINESHOP": "Beast Enclosure",
    "UNIT_MUTE_ARMOURY": "Forge",
    "UNIT_MUTE_POWERSTATION": "Power Plant",
    "UNIT_MUTE_DRILLRIG": "Derrick",
    "UNIT_MUTE_CONVERTER": "Pig Pen",
    "UNIT_MUTE_COLLECTOR": "Big Pig",
    "UNIT_MUTE_REPAIRBAY": "Healing Tent",
    "UNIT_MUTE_RESEARCHLAB": "Alchemy Hall",
    "UNIT_TEMPLE": "Altar of the Scourge",
    "UNIT_ROBOT_OUTPOST": "Barn",
    "UNIT_ROBOT_BARRACKS": "Microunit Factory",
    "UNIT_ROBOT_MACHINESHOP": "Macrounit Factory",
    "UNIT_ROBOT_ARMOURY": "Weapon Control",
    "UNIT_ROBOT_POWERSTATION": "Power Unit",
    "UNIT_ROBOT_DRILLRIG": "Oilbot",
    "UNIT_ROBOT_CONVERTER": "Wind Turbine",
    "UNIT_ROBOT_COLLECTOR": "Windmill",
    "UNIT_ROBOT_REPAIRBAY": "Maintenance Depot",
    "UNIT_ROBOT_RESEARCHLAB": "Technostudy",
    "UNIT_SURV_TOWER1": "Sentry Gun",
    "UNIT_SURV_TOWER2": "Cannon Tower",
    "UNIT_SURV_TOWER3": "AA Tower",
    "UNIT_SURV_TOWER4": "Laser Destroyer",
    "UNIT_MUTE_TOWER1": "Kneecapper",
    "UNIT_MUTE_TOWER2": "The Worm",
    "UNIT_MUTE_TOWER3": "Bazooka Battery",
    "UNIT_MUTE_TOWER4": "Touch of Death",
    "UNIT_ROBOT_TOWER1": "Distance Seeder",
    "UNIT_ROBOT_TOWER2": "Pod Cannon",
    "UNIT_ROBOT_TOWER3": "Solar Intensifier",
    "UNIT_ROBOT_TOWER4": "Lightning Generator",
    "UNIT_SURV_AIR1": "Orville Fighter",
    "UNIT_SURV_AIR2": "Wilbur Bomber",
    "UNIT_SURV_AIR3": "Airlifter",
    "UNIT_MUTE_AIR1": "Pteranodon",
    "UNIT_MUTE_AIR2": "Wasp Bomber",
    "UNIT_MUTE_AIR3": "Floater",
    "UNIT_ROBOT_AIR1": "AG-Responsebot Fighter",
    "UNIT_ROBOT_AIR2": "Crop Duster Bomber",
    "UNIT_ROBOT_AIR3": "Transport Dome",
    "UNIT_SURV_WALL1": "Barricade",
    "UNIT_SURV_WALL2": "Force Wall",
    "UNIT_MUTE_WALL1": "Skeletal Wall",
    "UNIT_MUTE_WALL2": "Thunder Fence",
    "UNIT_ROBOT_WALL1": "Boundary Fence",
    "UNIT_ROBOT_WALL2": "Bugzapper"
}


class FormatError(ValueError):
    pass


@dataclass(frozen=True)
class Cell:
    offset: int
    width: int
    original: str


@dataclass(frozen=True)
class Unit:
    identifier: str
    cells: tuple

    @property
    def faction(self):
        return "Evolved" if self.identifier == "UNIT_TEMPLE" else FACTIONS.get(
            self.identifier.split("_")[1], "Other")

    @property
    def label(self):
        if self.identifier in UNIT_NAMES:
            return UNIT_NAMES[self.identifier]
        parts = self.identifier.split("_")
        return " ".join(parts[2:] if parts[1] in FACTIONS else parts[1:]).title()


class Config:
    """Retain the entire file; only replace explicitly edited fixed-width cells."""

    def __init__(self, raw):
        self.raw = bytes(raw)
        self.changes = {}
        self.undo_stack = []
        self.redo_stack = []
        if len(raw) < 122 or raw.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf")):
            raise FormatError("Not a supported original KKND2 UCONFIG file (short file or added BOM).")
        try:
            self.name = raw[:120].decode("utf-16le").split("\0", 1)[0]
            # The 60-WCHAR title is followed by UTF-16LE column labels and LF.
            end = next(i for i in range(120, min(len(raw) - 1, 8192), 2)
                       if raw[i:i + 2] == b"\n\0")
            header = raw[120:end].decode("utf-16le")
        except (UnicodeError, StopIteration) as exc:
            raise FormatError("Cannot read the UTF-16LE title and column header.") from exc
        if tuple(x.strip() for x in header.rstrip().rstrip("/").split("/")) != FIELDS:
            raise FormatError("Unrecognized stat columns; refusing to guess their order.")
        self.body_offset = end + 2
        self.units = []
        identifiers = set()
        pos = self.body_offset
        for row_number, line in enumerate(raw[pos:].splitlines(keepends=True), 1):
            content = line.rstrip(b"\r\n")
            if content == b"":
                pos += len(line)
                continue
            parts = content.split(b"\t")
            # Original rows contain an extra trailing tab.
            if parts and parts[-1] == b"":
                parts.pop()
            if len(parts) != len(FIELDS) + 1 or not re.fullmatch(rb"UNIT_[A-Z0-9_]+ *", parts[0]):
                raise FormatError(f"Malformed unit record on row {row_number}.")
            identifier = parts[0].rstrip(b" ").decode("ascii")
            if identifier in identifiers:
                raise FormatError(f"Duplicate unit identifier: {identifier}")
            identifiers.add(identifier)
            cells = []
            offset = pos + len(parts[0]) + 1
            for field, part in zip(FIELDS, parts[1:]):
                if not re.fullmatch(rb"(?:[0-9]+|-) *", part):
                    raise FormatError(f"Invalid {field} value in {identifier}.")
                cells.append(Cell(offset, len(part), part.rstrip(b" ").decode("ascii")))
                offset += len(part) + 1
            self.units.append(Unit(identifier, tuple(cells)))
            pos += len(line)
        if not self.units:
            raise FormatError("No unit records found.")

    def value(self, row, column):
        return self.changes.get((row, column), self.units[row].cells[column].original)

    def validate(self, row, column, value):
        cell = self.units[row].cells[column]
        if cell.original == "-":
            if value != "-":
                raise ValueError("This stat is unavailable for this unit.")
        elif not re.fullmatch(r"[0-9]+", value):
            raise ValueError("Enter a whole number, 0 or greater.")
        elif len(value) > cell.width:
            raise ValueError(f"This field has room for at most {cell.width} digits.")
        if value != "-" and value != cell.original:
            maximum = FIELD_MAXIMUMS[column]
            if int(value) > maximum:
                raise ValueError(f"{FIELDS[column]}: maximum is {maximum:,} (in-game editor limit).")
            if column == 1 and int(value) < 1:
                raise ValueError("Build-Time: minimum is 1 second.")
        return value

    def apply(self, edits):
        updated = self.changes.copy()
        for (row, column), value in edits.items():
            value = self.validate(row, column, value)
            if value == self.units[row].cells[column].original:
                updated.pop((row, column), None)
            else:
                updated[row, column] = value
        if updated != self.changes:
            self.undo_stack.append(self.changes.copy())
            self.changes = updated
            self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.changes.copy())
            self.changes = self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.changes.copy())
            self.changes = self.redo_stack.pop()

    def serialize(self):
        out = bytearray(self.raw)
        for (row, column), value in self.changes.items():
            self.validate(row, column, value)
            cell = self.units[row].cells[column]
            out[cell.offset:cell.offset + cell.width] = value.encode("ascii").ljust(cell.width, b" ")
        result = bytes(out)
        # Reparse before writing; IDs, offsets and file size must stay identical.
        check = Config(result)
        if len(result) != len(self.raw) or [u.identifier for u in check.units] != [u.identifier for u in self.units]:
            raise FormatError("Internal format validation failed.")
        return result


def save_config(path, config):
    """Backup, flush, then atomically replace. Never truncate the source file."""
    path = Path(path)
    if path.is_symlink():
        raise OSError("Please open the real configuration file rather than a symbolic link.")
    if path.read_bytes() != config.raw:
        raise OSError("This file changed on disk. Reopen it before saving; your edits are still in memory.")
    payload = config.serialize()
    if payload == config.raw:
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_dir / f"{path.name}.{stamp}.bak"
    with backup.open("xb") as stream:
        stream.write(config.raw)
        stream.flush()
        os.fsync(stream.fileno())
    if backup.read_bytes() != config.raw:
        raise OSError("Backup verification failed; source file was not changed.")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".kknd2-", suffix=".tmp", delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if temp_path.read_bytes() != payload:
            raise OSError("Temporary file verification failed; source file was not changed.")
        if path.read_bytes() != config.raw:
            raise OSError("The file changed while saving; source file was not overwritten.")
        os.replace(str(temp_path), str(path))
        temp_path = None
        if path.read_bytes() != payload:
            raise OSError(f"Post-save verification failed. Original backup: {backup}")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return backup



# Frozen from the user-confirmed defaults; never refreshed from an edited file.
DEFAULT_SOURCE_SHA256 = 'e725992fc9c7227c0ac67f17bc43b4457bda72411605fd3b383fed69853df5ad'
_DEFAULT_ROWS = """\
UNIT_SURV_GUNNER 100 10 450 12 45 0 153 176 0 3 0 100 50 10 10 5 10
UNIT_SURV_GRENADIER 125 14 450 12 45 0 153 176 32 1 150 150 125 375 375 35 375
UNIT_SURV_FLAMER 200 14 450 12 45 0 153 64 0 0 80 80 50 150 150 45 150
UNIT_SURV_ROCKETEER 200 18 450 12 45 0 153 224 48 1 60 150 50 50 50 20 107
UNIT_SURV_SNIPER 250 22 550 12 45 0 204 240 0 1 1 100 600 60 60 18 60
UNIT_SURV_TECHNICIAN 100 7 500 12 45 0 153 96 0 0 60 30 - - - - -
UNIT_SURV_KAMIKAZE 250 25 450 12 50 0 255 96 0 0 60 30 1000 2500 2500 1250 2500
UNIT_MUTE_GUNNER 100 10 450 12 45 0 153 176 0 1 100 100 200 40 40 20 40
UNIT_MUTE_GRENADIER 125 14 450 12 45 0 153 176 32 1 150 150 125 375 375 35 375
UNIT_MUTE_FLAMER 200 14 450 12 45 0 153 64 0 0 80 80 50 150 150 46 150
UNIT_MUTE_ROCKETEER 200 18 450 12 45 0 153 224 48 1 60 150 50 50 50 20 107
UNIT_MUTE_SNIPER 250 22 550 12 45 0 255 240 0 1 1 100 600 60 60 18 60
UNIT_MUTE_TECHNICIAN 100 7 500 12 45 0 153 96 0 0 60 30 - - - - -
UNIT_MUTE_KAMIKAZE 250 25 450 12 50 0 255 96 0 0 60 30 1000 2500 2500 1250 2500
UNIT_MUTE_DEMON 100 10 1000 12 45 0 255 240 0 1 100 200 250 250 250 25 250
UNIT_ROBOT_GUNNER 250 15 1200 12 45 0 179 184 0 4 0 100 70 15 15 7 15
UNIT_ROBOT_GRENADIER 300 20 1200 12 45 0 179 176 32 1 150 150 123 370 370 34 370
UNIT_ROBOT_FLAMER 450 20 1200 12 45 0 179 64 0 0 80 80 50 150 150 45 150
UNIT_ROBOT_ROCKETEER 450 25 1200 12 45 0 179 224 48 1 60 250 50 50 50 20 100
UNIT_ROBOT_SNIPER 600 30 1250 12 45 0 204 256 0 1 1 100 700 70 70 22 70
UNIT_ROBOT_TECHNICIAN 100 7 700 12 45 0 153 96 0 0 60 30 - - - - -
UNIT_ROBOT_KAMIKAZE 500 25 750 12 50 0 255 96 0 0 60 30 1000 2500 2500 1250 2500
UNIT_SURV_MOBILEOUTPOST 5000 270 10000 15 25 0 179 96 256 0 60 30 - - - - -
UNIT_SURV_MOBILEDRILLRIG 1000 50 5000 12 30 0 0 0 256 0 12 30 - - - - -
UNIT_SURV_TANKER 1000 100 10000 12 20 0 0 0 256 0 35 30 - - - - -
UNIT_SURV_BIKE 200 10 750 12 100 0 179 128 0 2 50 150 35 75 75 15 75
UNIT_SURV_HOVERBUGGY 500 20 1500 12 70 0 179 192 0 1 1 90 35 89 89 12 89
UNIT_SURV_ATV 300 15 1250 12 75 0 179 160 0 5 1 100 100 40 40 7 40
UNIT_SURV_ANACONDATANK 800 25 2000 12 50 0 179 224 64 0 10 85 125 338 338 40 338
UNIT_SURV_BARRAGECRAFT 1000 30 2500 12 40 0 179 256 64 0 0 150 250 600 600 70 600
UNIT_SURV_AUTOCANNONTANK 1250 35 3000 12 35 0 179 288 64 0 5 100 300 125 125 34 125
UNIT_SURV_JUGGERNAUT 1500 40 3500 12 35 0 179 320 64 0 1 20 30 70 70 10 70
UNIT_MUTE_MOBILEOUTPOST 5000 270 10000 15 25 0 179 96 256 0 60 30 - - - - -
UNIT_MUTE_MOBILEDRILLRIG 1000 50 5000 12 30 0 0 0 256 0 12 30 - - - - -
UNIT_MUTE_TANKER 1000 100 10000 12 20 0 0 0 256 0 35 30 - - - - -
UNIT_MUTE_DIREWOLF 200 10 750 12 100 0 179 128 0 1 75 75 71 152 152 31 152
UNIT_MUTE_SCORPION 300 15 1250 12 75 0 179 160 0 2 1 170 314 125 125 20 125
UNIT_MUTE_CRINOID 500 20 1500 12 70 0 179 192 0 0 5 100 40 102 102 14 102
UNIT_MUTE_MASTODON 800 25 2000 12 50 0 179 224 32 0 10 100 145 400 400 48 400
UNIT_MUTE_HIPPO 1000 30 2500 12 40 0 179 256 32 10 0 80 65 150 150 18 150
UNIT_MUTE_CRAB 1250 35 3000 12 35 0 179 288 64 0 0 159 590 250 250 65 250
UNIT_MUTE_BEETLE 1500 40 3500 12 35 0 179 320 64 1 5 150 300 425 425 75 425
UNIT_ROBOT_MOBILEOUTPOST 5000 270 10000 15 25 0 179 96 256 0 60 30 - - - - -
UNIT_ROBOT_MOBILEDRILLRIG 1000 50 5000 12 30 0 0 0 256 0 12 30 - - - - -
UNIT_ROBOT_TANKER 1000 100 10000 12 20 0 0 0 256 0 35 30 - - - - -
UNIT_ROBOT_PATROLBOT 200 10 750 12 100 0 179 128 0 4 13 150 36 77 77 15 77
UNIT_ROBOT_RESPONSEBOT 300 15 1250 12 75 0 179 160 0 10 1 100 128 51 51 9 51
UNIT_ROBOT_RADIATOR 500 20 1500 12 70 0 179 56 0 0 1 75 150 450 450 60 450
UNIT_ROBOT_TANKBOT 800 25 2000 12 50 0 179 224 32 0 10 150 135 370 370 45 370
UNIT_ROBOT_DOOMDOME 1000 30 2500 12 40 0 179 256 32 0 100 100 265 595 595 70 595
UNIT_ROBOT_CAUTERISER 1250 35 3000 12 35 0 179 288 64 0 151 151 895 398 398 120 398
UNIT_ROBOT_GRIMREAPER 1500 40 3500 12 35 0 179 320 0 0 0 100 80 170 170 20 170
UNIT_SURV_OUTPOST 1500 60 10000 20 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_BARRACKS 400 30 4000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_MACHINESHOP 800 30 6000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_ARMOURY 500 45 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_POWERSTATION 2000 80 6000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_DRILLRIG 1000 8 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_CONVERTER 2000 60 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_COLLECTOR 1000 30 1500 10 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_REPAIRBAY 500 45 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_RESEARCHLAB 700 30 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_OUTPOST 1500 60 10000 20 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_BARRACKS 400 30 4000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_MACHINESHOP 800 30 6000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_ARMOURY 500 45 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_POWERSTATION 2000 80 6000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_DRILLRIG 1000 8 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_CONVERTER 2000 60 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_COLLECTOR 1000 30 1500 10 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_REPAIRBAY 500 45 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_MUTE_RESEARCHLAB 700 30 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_TEMPLE 1500 60 4000 20 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_OUTPOST 1500 60 10000 20 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_BARRACKS 400 30 4000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_MACHINESHOP 800 30 6000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_ARMOURY 500 45 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_POWERSTATION 2000 80 6000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_DRILLRIG 1000 8 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_CONVERTER 2000 60 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_COLLECTOR 1000 30 1500 10 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_REPAIRBAY 500 45 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_ROBOT_RESEARCHLAB 700 30 5000 15 0 0 0 0 0 0 0 30 - - - - -
UNIT_SURV_TOWER1 800 15 1000 15 0 0 230 256 0 0 0 0 79 38 38 19 38
UNIT_SURV_TOWER2 1200 30 1500 15 0 0 230 320 0 0 15 15 55 136 136 26 136
UNIT_SURV_TOWER3 2500 45 1500 15 0 0 230 320 64 0 0 150 0 0 0 0 190
UNIT_SURV_TOWER4 3500 60 2000 15 0 0 255 352 0 0 60 60 400 933 933 95 933
UNIT_MUTE_TOWER1 800 15 1000 15 0 0 230 256 0 0 0 150 236 115 115 57 115
UNIT_MUTE_TOWER2 1200 30 1500 15 0 0 230 320 0 0 16 16 105 261 261 50 261
UNIT_MUTE_TOWER3 2500 45 1500 15 0 0 230 320 64 0 0 150 0 0 0 0 120
UNIT_MUTE_TOWER4 3500 60 2000 15 0 0 255 352 0 0 50 50 500 620 620 90 620
UNIT_ROBOT_TOWER1 800 15 1000 15 0 0 230 256 0 0 0 10 70 34 34 17 34
UNIT_ROBOT_TOWER2 1200 30 1500 15 0 0 230 320 32 0 15 15 105 261 261 50 261
UNIT_ROBOT_TOWER3 2500 45 1500 15 0 0 230 320 64 0 0 150 0 0 0 0 190
UNIT_ROBOT_TOWER4 3500 60 2000 15 0 0 255 352 0 0 50 50 520 1205 1205 170 1205
UNIT_SURV_AIR1 2000 120 1000 12 120 0 153 256 64 0 300 30 30 40 40 15 40
UNIT_SURV_AIR2 2500 150 1500 8 90 0 153 192 0 3 20 120 250 200 200 150 200
UNIT_SURV_AIR3 2000 135 2500 12 70 0 153 96 0 0 60 30 - - - - -
UNIT_MUTE_AIR1 2000 120 1000 12 120 0 153 256 64 0 1 1 30 40 40 15 40
UNIT_MUTE_AIR2 2500 150 1500 12 90 0 153 192 0 3 20 30 250 200 200 150 200
UNIT_MUTE_AIR3 2000 135 2500 12 70 0 153 96 0 0 60 30 - - - - -
UNIT_ROBOT_AIR1 2000 120 1000 12 120 0 153 256 64 0 60 30 30 40 40 15 40
UNIT_ROBOT_AIR2 2500 150 1500 12 90 0 153 192 0 3 20 30 250 200 200 150 200
UNIT_ROBOT_AIR3 2000 135 2500 12 70 0 153 96 0 0 60 30 - - - - -
UNIT_SURV_WALL1 100 5 500 10 0 0 230 192 0 0 0 30 - - - - -
UNIT_SURV_WALL2 500 15 7500 10 0 0 230 192 0 0 0 30 1125 3750 3750 125 3750
UNIT_MUTE_WALL1 100 5 500 10 0 0 230 192 0 0 0 30 - - - - -
UNIT_MUTE_WALL2 500 15 7500 10 0 0 230 192 0 0 0 30 1125 3750 3750 125 3750
UNIT_ROBOT_WALL1 100 5 500 10 0 0 230 192 0 0 0 30 - - - - -
UNIT_ROBOT_WALL2 500 15 7500 10 0 0 230 192 0 0 0 30 1125 3750 3750 125 3750
"""
DEFAULTS = {parts[0]: tuple(parts[1:]) for parts in (line.split() for line in _DEFAULT_ROWS.splitlines())}

class FlowBar(ttk.Frame):
    """Wrap controls into rows instead of clipping them at large text sizes."""
    def __init__(self, parent, gap=6):
        super().__init__(parent)
        self.gap = gap
        self.buttons = []
        self.bind("<Configure>", self.arrange)

    def add(self, text, command):
        button = ttk.Button(self, text=text, command=command, width=0)
        self.buttons.append(button)
        return button

    def arrange(self, _event=None):
        width = max(1, self.winfo_width())
        x = y = row_height = 0
        for button in self.buttons:
            w, h = button.winfo_reqwidth(), button.winfo_reqheight()
            if x and x + w > width:
                x = 0
                y += row_height + self.gap
                row_height = 0
            button.place(x=x, y=y, width=min(w, width), height=h)
            x += w + self.gap
            row_height = max(row_height, h)
        self.configure(height=y + row_height)


class ScrollPanel(ttk.Frame):
    def __init__(self, parent, background):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, background=background)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vertical = ttk.Scrollbar(self, command=self.canvas.yview)
        self.vertical.grid(row=0, column=1, sticky="ns")
        self.horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.horizontal.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=self.horizontal.set, yscrollcommand=self.vertical.set)
        self.content = ttk.Frame(self.canvas)
        self.item = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.content.bind("<Configure>", self.resize)
        self.canvas.bind("<Configure>", self.resize)

    def resize(self, _event=None):
        width = max(self.content.winfo_reqwidth(), self.canvas.winfo_width())
        if int(float(self.canvas.itemcget(self.item, "width"))) != width:
            self.canvas.itemconfigure(self.item, width=width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def reveal(self, widget):
        """Tab navigation brings an offscreen input into view on both axes."""
        self.update_idletasks()
        box = self.canvas.bbox("all")
        if not box:
            return
        x = widget.winfo_rootx() - self.content.winfo_rootx()
        y = widget.winfo_rooty() - self.content.winfo_rooty()
        for axis, start, size, total, viewport in (
            ("x", x, widget.winfo_width(), box[2], self.canvas.winfo_width()),
            ("y", y, widget.winfo_height(), box[3], self.canvas.winfo_height()),
        ):
            current = getattr(self.canvas, axis + "view")()[0] * total
            target = current
            if start < current:
                target = start
            elif start + size > current + viewport:
                target = start + size - viewport
            getattr(self.canvas, axis + "view_moveto")(max(0, target) / max(1, total))


def enable_dpi_awareness():
    # Tk 8.6 is system-DPI aware. Windows handles scaling on other monitors;
    # do not opt into per-monitor V2 without handling WM_DPICHANGED in Tk.
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


class Editor(tk.Tk):
    def __init__(self, folder=DEFAULT_FOLDER, initial=None, tk_scaling=None):
        super().__init__()
        self.withdraw()
        if tk_scaling is not None:  # Deterministic DPI regression testing.
            self.tk.call("tk", "scaling", tk_scaling)
        self.scale = float(self.tk.call("tk", "scaling")) / (96 / 72)
        self.config_doc = None
        self.path = None
        self.current = None
        self.loading = False
        self.folder = Path(folder)
        self.file_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.faction_var = tk.StringVar(value="All factions")
        self.defaults_only = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Open a UCONFIG file to begin.")
        self.unit_title = tk.StringVar(value="Choose a unit")
        self.unit_id = tk.StringVar()
        self.layout_mode = None
        self.compact_page = "stats"
        self.style = ttk.Style(self)
        if "vista" in self.style.theme_names():
            self.style.theme_use("vista")
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(name).configure(family="Segoe UI", size=10)
        self.title_font = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        self.style.configure("Treeview", rowheight=max(self.px(27), tkfont.nametofont("TkDefaultFont").metrics("linespace") + self.px(8)))
        self.style.configure("Title.TLabel", font=self.title_font)
        self.style.configure("Invalid.TEntry", foreground="#bd2727")
        self.style.configure("Changed.TEntry", foreground="#005ca8")
        self.build_ui()
        self.protocol("WM_DELETE_WINDOW", self.close)
        for key, command in (("<Control-s>", self.save), ("<Control-z>", self.undo), ("<Control-y>", self.redo), ("<Control-f>", self.focus_search)):
            self.bind(key, lambda event, fn=command: (fn(), "break")[1])
        self.bind("<MouseWheel>", self.mousewheel, add="+")
        self.scan_files()
        target = Path(initial) if initial else self.folder / "UCONFIG_02.cfg"
        if not target.exists() and self.files:
            target = self.files[0]
        if target.is_file():
            self.load_file(target)
        self.fit_window(self, 1140, 820)
        self.deiconify()

    def px(self, number):
        return max(1, round(number * self.scale))

    def work_area(self):
        area = (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes
                rect = wintypes.RECT()
                if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                    area = (rect.left, rect.top, rect.right, rect.bottom)
            except (AttributeError, OSError):
                pass
        return area

    def fit_window(self, window, width, height):
        left, top, right, bottom = self.work_area()
        available_w, available_h = right - left, bottom - top
        w = min(self.px(width), int(available_w * .94))
        h = min(self.px(height), max(200, available_h - self.px(70)))
        window.geometry(f"{w}x{h}+{left + (available_w - w) // 2}+{top + self.px(12)}")
        window.minsize(min(self.px(440), w), min(self.px(400), h))

    def build_ui(self):
        p = self.px
        outer = ttk.Frame(self, padding=p(12))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)
        self.app_heading = ttk.Label(outer, text="KKND2 / Unit Editor", style="Title.TLabel")
        self.app_heading.grid(row=0, column=0, sticky="w", pady=(0, p(8)))
        self.toolbar = FlowBar(outer, p(5))
        self.toolbar.grid(row=1, column=0, sticky="ew", pady=(0, p(8)))
        self.toolbar.add("Save  Ctrl+S", self.save)
        self.toolbar.add("Unsaved", self.review)
        self.toolbar.add("Defaults", self.review_defaults)
        self.toolbar.add("Open...", self.open_file)
        self.toolbar.add("Folder...", self.open_folder)
        self.file_caption = ttk.Label(outer, text="Configuration")
        self.file_caption.grid(row=2, column=0, sticky="w")
        self.file_box = ttk.Combobox(outer, state="readonly", textvariable=self.file_var, width=15)
        self.file_box.grid(row=3, column=0, sticky="ew", pady=(p(4), p(10)))
        self.file_box.bind("<<ComboboxSelected>>", self.file_selected)
        self.main_panel = ttk.Frame(outer)
        self.main_panel.grid(row=4, column=0, sticky="nsew")
        self.page_tabs = ttk.Frame(self.main_panel)
        ttk.Button(self.page_tabs, text="Units / Search", command=lambda: self.switch_page("units")).pack(side="left")
        ttk.Button(self.page_tabs, text="Unit stats", command=lambda: self.switch_page("stats")).pack(side="left", padx=p(6))
        self.left = ttk.Frame(self.main_panel)
        self.left.columnconfigure(0, weight=1)
        self.left.rowconfigure(3, weight=1)
        self.search = ttk.Entry(self.left, textvariable=self.search_var, width=18)
        self.search.grid(row=0, column=0, sticky="ew", pady=(0, p(6)))
        self.search.insert(0, "")
        factions = ttk.Combobox(self.left, textvariable=self.faction_var, state="readonly", width=18,
                               values=("All factions", "Survivors", "Evolved", "Series 9", "Other"))
        factions.grid(row=1, column=0, sticky="ew", pady=(0, p(6)))
        ttk.Checkbutton(self.left, text="Different from defaults", variable=self.defaults_only,
                        command=self.filter_units).grid(row=2, column=0, sticky="w", pady=(0, p(6)))
        listing = ttk.Frame(self.left)
        listing.grid(row=3, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(listing, columns=("faction",), show="tree headings", selectmode="browse", height=5)
        self.tree.heading("#0", text="Unit / building  (* unsaved, ~ modified)")
        self.tree.column("#0", width=p(240), minwidth=p(180))
        self.tree.heading("faction", text="Faction")
        faction_width = tkfont.nametofont("TkDefaultFont").measure("Survivors") + p(18)
        self.tree.column("faction", width=faction_width, minwidth=faction_width, stretch=False)
        scroll = ttk.Scrollbar(listing, orient="vertical", command=self.tree.yview)
        hscroll = ttk.Scrollbar(listing, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set, xscrollcommand=hscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("changed", foreground="#005ca8")
        self.tree.tag_configure("modified", foreground="#986009")
        self.tree.bind("<<TreeviewSelect>>", self.select_unit)
        self.search_var.trace_add("write", lambda *_: self.filter_units())
        self.faction_var.trace_add("write", lambda *_: self.filter_units())
        self.right = ttk.Frame(self.main_panel)
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(2, weight=1)
        self.heading = ttk.Label(self.right, textvariable=self.unit_title, style="Title.TLabel")
        self.heading.grid(row=0, column=0, sticky="ew", pady=(0, p(3)))
        self.identifier_label = ttk.Label(self.right, textvariable=self.unit_id, foreground="#666666")
        self.identifier_label.grid(row=1, column=0, sticky="ew", pady=(0, p(8)))
        self.stats = ScrollPanel(self.right, self.style.lookup("TFrame", "background") or "#f0f0f0")
        self.stats.grid(row=2, column=0, sticky="nsew")
        grid = self.stats.content
        grid.columnconfigure(0, weight=1)
        for col, label in enumerate(("STAT", "VALUE", "DEFAULT", "DELTA", "SAVED")):
            ttk.Label(grid, text=label, foreground="#666666").grid(row=0, column=col, sticky="w" if col == 0 else "e", padx=p(7), pady=p(7))
        self.values, self.entries, self.original_labels = [], [], []
        self.default_labels, self.delta_labels = [], []
        for i, field in enumerate(FIELDS):
            label = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", field).replace("-", " ")
            ttk.Label(grid, text=label + "\n" + field_hint(i)).grid(row=i + 1, column=0, sticky="w", pady=p(7), padx=p(7))
            var = tk.StringVar()
            entry = ttk.Entry(grid, width=8, textvariable=var, state="disabled")
            entry.grid(row=i + 1, column=1, sticky="ew", padx=p(7), pady=p(3))
            entry.bind("<FocusIn>", lambda _event, widget=entry: self.stats.reveal(widget))
            labels = []
            for col in (2, 3, 4):
                item = ttk.Label(grid, text="", foreground="#777777", width=8, anchor="e")
                item.grid(row=i + 1, column=col, sticky="e", padx=p(7))
                labels.append(item)
            self.values.append(var)
            self.entries.append(entry)
            self.default_labels.append(labels[0])
            self.delta_labels.append(labels[1])
            self.original_labels.append(labels[2])
            var.trace_add("write", lambda *_, index=i: self.form_changed(index))
        self.actions = FlowBar(self.right, p(5))
        self.actions.grid(row=3, column=0, sticky="ew", pady=(p(8), 0))
        self.actions.add("Undo", self.undo)
        self.actions.add("Redo", self.redo)
        self.actions.add("Revert saved", self.revert_unit)
        self.actions.add("Reset defaults", self.reset_defaults)
        self.status_label = ttk.Label(outer, textvariable=self.status)
        self.status_label.grid(row=5, column=0, sticky="ew", pady=(p(8), 0))
        self.main_panel.bind("<Configure>", self.reflow)
        self.right.bind("<Configure>", self.wrap_heading)
        outer.bind("<Configure>", lambda event: self.status_label.configure(wraplength=max(1, event.width - p(24))))

    def reflow(self, _event=None):
        width = self.main_panel.winfo_width()
        mode = "side" if width >= self.px(980) else "tabs"
        if mode != self.layout_mode:
            self.layout_mode = mode
            self.left.grid_forget()
            self.right.grid_forget()
            if mode == "side":
                self.app_heading.grid()
                self.file_caption.grid()
                self.page_tabs.grid_forget()
                self.main_panel.columnconfigure(0, weight=0, minsize=self.px(330))
                self.main_panel.columnconfigure(1, weight=1)
                self.main_panel.rowconfigure(0, weight=0)
                self.main_panel.rowconfigure(1, weight=1)
                self.left.grid(row=1, column=0, sticky="nsew", padx=(0, self.px(14)))
                self.right.grid(row=1, column=1, sticky="nsew")
            else:
                self.app_heading.grid_remove()
                self.file_caption.grid_remove()
                self.main_panel.columnconfigure(0, weight=1, minsize=0)
                self.main_panel.columnconfigure(1, weight=0)
                self.main_panel.rowconfigure(0, weight=0)
                self.main_panel.rowconfigure(1, weight=1)
                self.page_tabs.grid(row=0, column=0, sticky="ew", pady=(0, self.px(6)))
                self.switch_page(self.compact_page)
    def wrap_heading(self, event):
        wrap = max(self.px(120), event.width - self.px(10))
        self.heading.configure(wraplength=wrap)
        self.identifier_label.configure(wraplength=wrap)

    def switch_page(self, page):
        self.compact_page = page
        if self.layout_mode == "tabs":
            self.left.grid_forget()
            self.right.grid_forget()
            (self.left if page == "units" else self.right).grid(row=1, column=0, sticky="nsew")

    def mousewheel(self, event):
        widget = event.widget
        while widget is not None:
            if widget == self.stats:
                axis = "x" if event.state & 1 else "y"
                getattr(self.stats.canvas, axis + "view_scroll")(-1 if event.delta > 0 else 1, "units")
                return "break"
            widget = getattr(widget, "master", None)

    def scan_files(self):
        self.files = sorted(self.folder.glob("*.cfg")) if self.folder.is_dir() else []
        self.file_box.configure(values=[p.name for p in self.files])

    def load_file(self, path):
        try:
            doc = Config(Path(path).read_bytes())
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot open configuration", str(exc), parent=self)
            self.file_var.set(self.path.name if self.path else "")
            return False
        self.path, self.folder = Path(path), Path(path).parent
        self.config_doc, self.current = doc, None
        self.scan_files()
        self.file_var.set(self.path.name)
        self.search_var.set("")
        self.faction_var.set("All factions")
        self.defaults_only.set(False)
        self.filter_units()
        if self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])
            self.select_unit()
        self.update_status()
        return True

    def file_selected(self, _event=None):
        target = self.folder / self.file_var.get()
        if self.can_leave():
            self.load_file(target)
        else:
            self.file_var.set(self.path.name if self.path else "")

    def open_file(self):
        if self.can_leave():
            chosen = filedialog.askopenfilename(parent=self, initialdir=self.folder, title="Open KKND2 configuration", filetypes=[("KKND2 configuration", "*.cfg")])
            if chosen:
                self.load_file(chosen)

    def open_folder(self):
        if not self.can_leave():
            return
        chosen = filedialog.askdirectory(parent=self, initialdir=self.folder)
        if chosen:
            candidates = sorted(Path(chosen).glob("*.cfg"))
            if not candidates:
                messagebox.showinfo("No configurations", "This folder has no .cfg files.", parent=self)
                return
            preferred = Path(chosen) / "UCONFIG_02.cfg"
            self.load_file(preferred if preferred.exists() else candidates[0])

    def current_value(self, row, col):
        if row == self.current:
            return self.values[col].get()
        return self.config_doc.value(row, col)

    def different(self, row):
        unit = self.config_doc.units[row]
        base = DEFAULTS.get(unit.identifier)
        return bool(base and any(self.current_value(row, col) != value for col, value in enumerate(base)))

    def unit_mark(self, row):
        modified = self.different(row)
        unsaved = any(self.current_value(row, col) != cell.original for col, cell in enumerate(self.config_doc.units[row].cells))
        return ("* " if unsaved else "") + ("~ " if modified else ""), ("changed",) if unsaved else ("modified",) if modified else ()

    def filter_units(self):
        if not self.config_doc or self.loading or not self.commit_form():
            return
        selected = str(self.current) if self.current is not None else None
        self.tree.delete(*self.tree.get_children())
        query, faction = self.search_var.get().casefold(), self.faction_var.get()
        for i, unit in enumerate(self.config_doc.units):
            if query not in (unit.label + " " + unit.identifier + " " + unit.faction).casefold():
                continue
            if faction != "All factions" and faction != unit.faction:
                continue
            if self.defaults_only.get() and not self.different(i):
                continue
            prefix, tags = self.unit_mark(i)
            self.tree.insert("", "end", iid=str(i), text=prefix + unit.label, values=(unit.faction,), tags=tags)
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)

    def select_unit(self, _event=None):
        selection = self.tree.selection()
        if not selection or int(selection[0]) == self.current:
            return
        if not self.commit_form():
            if self.current is not None and self.tree.exists(str(self.current)):
                self.tree.selection_set(str(self.current))
            return
        self.current = int(selection[0])
        self.show_unit()
        self.switch_page("stats")
        self.stats.canvas.yview_moveto(0)

    def show_unit(self):
        if self.current is None:
            return
        self.loading = True
        unit = self.config_doc.units[self.current]
        self.unit_title.set(f"{unit.label} / {unit.faction}")
        self.unit_id.set(unit.identifier)
        for i, cell in enumerate(unit.cells):
            self.values[i].set(self.config_doc.value(self.current, i))
            self.entries[i].configure(state="readonly" if cell.original == "-" else "normal")
            self.original_labels[i].configure(text=cell.original)
            self.update_field(i)
        self.loading = False
        self.update_status()

    def update_field(self, i):
        unit = self.config_doc.units[self.current]
        value = self.values[i].get()
        base = DEFAULTS.get(unit.identifier, (None,) * len(FIELDS))[i]
        self.default_labels[i].configure(text=base if base is not None else "n/a")
        valid = True
        try:
            self.config_doc.validate(self.current, i, value)
            self.entries[i].configure(style="Changed.TEntry" if value != unit.cells[i].original else "TEntry")
        except ValueError:
            valid = False
            self.entries[i].configure(style="Invalid.TEntry")
        delta = "n/a" if base is None else "0" if value == base else "changed"
        if base is not None and valid and value.isascii() and value.isdigit() and base.isdigit():
            delta = f"{int(value) - int(base):+d}" if value != base else "0"
        if not valid:
            delta = "invalid"
        self.delta_labels[i].configure(text=delta, foreground="#986009" if base is not None and value != base else "#777777")

    def form_changed(self, i):
        if not self.loading and self.current is not None:
            self.update_field(i)
            self.refresh_marks()

    def form_dirty(self):
        return self.current is not None and any(v.get() != self.config_doc.value(self.current, i) for i, v in enumerate(self.values))

    def commit_form(self):
        if self.current is None or self.loading:
            return True
        try:
            self.config_doc.apply({(self.current, i): v.get() for i, v in enumerate(self.values)})
        except ValueError as exc:
            messagebox.showerror("Invalid stat", str(exc), parent=self)
            return False
        self.refresh_marks()
        return True

    def refresh_marks(self):
        if self.config_doc:
            for item in self.tree.get_children():
                row = int(item)
                prefix, tags = self.unit_mark(row)
                self.tree.item(item, text=prefix + self.config_doc.units[row].label, tags=tags)
            self.update_status()

    def update_status(self):
        if self.config_doc is None:
            return
        dirty = bool(self.config_doc.changes) or self.form_dirty()
        count = sum(self.different(i) for i in range(len(self.config_doc.units)))
        self.title(("* " if dirty else "") + f"{self.config_doc.name} - KKND2 Unit Editor")
        self.status.set(f"{self.path.name} | {count} units differ from defaults | " + ("Unsaved changes" if dirty else "All changes saved"))

    def undo(self):
        if self.config_doc and self.commit_form():
            self.config_doc.undo()
            self.show_unit()
            self.filter_units()

    def redo(self):
        if self.config_doc and self.commit_form():
            self.config_doc.redo()
            self.show_unit()
            self.filter_units()

    def revert_unit(self):
        if self.current is not None:
            self.config_doc.apply({(self.current, i): c.original for i, c in enumerate(self.config_doc.units[self.current].cells)})
            self.show_unit()
            self.filter_units()

    def reset_defaults(self):
        if self.current is None:
            return
        unit = self.config_doc.units[self.current]
        base = DEFAULTS.get(unit.identifier)
        if base is None:
            messagebox.showinfo("No baseline", "This unit is not in the embedded defaults.", parent=self)
            return
        # Snapshot valid pending edits, so undo can return to exactly those values.
        if not self.commit_form():
            return
        edits = {(self.current, i): value for i, value in enumerate(base)}
        try:
            self.config_doc.apply(edits)
        except ValueError as exc:
            messagebox.showerror("Cannot reset unit", f"The available stats differ from the baseline: {exc}", parent=self)
            return
        self.show_unit()
        self.filter_units()

    def comparison_rows(self, defaults=False):
        result = []
        for row, unit in enumerate(self.config_doc.units):
            base = DEFAULTS.get(unit.identifier) if defaults else tuple(c.original for c in unit.cells)
            if base is None:
                continue
            for col, old in enumerate(base):
                value = self.config_doc.value(row, col)
                if value != old:
                    delta = f"{int(value) - int(old):+d}" if value.isdigit() and old.isdigit() else "changed"
                    result.append((f"{unit.label} / {unit.faction} ({unit.identifier})", FIELDS[col], old, value, delta))
        return result

    def review(self):
        self.show_comparison(False)

    def review_defaults(self):
        self.show_comparison(True)

    def show_comparison(self, defaults):
        if not self.config_doc or not self.commit_form():
            return
        rows = self.comparison_rows(defaults)
        title = "Differences from defaults" if defaults else "Unsaved changes"
        if not rows:
            messagebox.showinfo(title, "All values match the embedded defaults." if defaults else "No unsaved changes.", parent=self)
            return
        window = tk.Toplevel(self)
        window.title(title)
        window.transient(self)
        self.fit_window(window, 930, 460)
        frame = ttk.Frame(window, padding=self.px(12))
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        label = ttk.Label(frame, text="Baseline: UCONFIG_02.cfg snapshot, 2026-09-08" if defaults else "Changes since this file was opened or last saved.")
        label.grid(row=0, column=0, sticky="w", pady=(0, self.px(8)))
        table = ttk.Treeview(frame, columns=("unit", "stat", "old", "new", "delta"), show="headings")
        for key, heading, width in (("unit", "Unit", 310), ("stat", "Stat", 170), ("old", "Default" if defaults else "Saved", 90), ("new", "Current", 90), ("delta", "Delta", 90)):
            table.heading(key, text=heading)
            table.column(key, width=self.px(width), minwidth=self.px(width), stretch=True)
        scroll = ttk.Scrollbar(frame, command=table.yview)
        hscroll = ttk.Scrollbar(frame, orient="horizontal", command=table.xview)
        table.configure(yscrollcommand=scroll.set, xscrollcommand=hscroll.set)
        table.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        hscroll.grid(row=2, column=0, sticky="ew")
        for row in rows:
            table.insert("", "end", values=row)
        frame.bind("<Configure>", lambda event: label.configure(wraplength=max(1, event.width - self.px(24))))

    def save(self):
        if not self.config_doc or not self.commit_form():
            return False
        try:
            backup = save_config(self.path, self.config_doc)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            return False
        if backup:
            self.config_doc = Config(self.config_doc.serialize())
            self.show_unit()
            self.filter_units()
            self.status.set(f"Saved {self.path.name} | Backup: backups/{backup.name}")
        else:
            self.update_status()
        return True

    def can_leave(self):
        if not self.config_doc or not (self.config_doc.changes or self.form_dirty()):
            return True
        choice = messagebox.askyesnocancel("Unsaved changes", "Save your changes before continuing?", parent=self)
        return self.save() if choice is True else choice is False

    def close(self):
        if self.can_leave():
            self.destroy()

    def focus_search(self):
        self.switch_page("units")
        self.search.focus_set()
        self.search.selection_range(0, "end")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="Optional UCONFIG file to open")
    parser.add_argument("--folder", type=Path, default=DEFAULT_FOLDER)
    args = parser.parse_args()
    enable_dpi_awareness()
    Editor(args.folder, args.file).mainloop()


if __name__ == "__main__":
    # Opening a .py file can use python.exe. Hand off to pythonw without
    # creating a second console. Prefer Launch Editor.pyw to avoid even a flash.
    import sys
    if os.name == "nt" and Path(sys.executable).name.lower() == "python.exe":
        import subprocess
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if pythonw.exists():
            subprocess.Popen([str(pythonw), str(Path(__file__).resolve()), *sys.argv[1:]], creationflags=subprocess.CREATE_NO_WINDOW)
            sys.exit(0)
    main()
