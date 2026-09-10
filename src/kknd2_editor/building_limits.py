"""Versioned editor settings and validated KWIPv3 building-limit patch data."""
from pathlib import Path
import json
import os
import tempfile

# Resolved from the supported executable's unit definition -> building data pointers.
BUILDINGS = {'UNIT_SURV_OUTPOST': {'address': 5260072, 'default': 4, 'maximum': 100},
 'UNIT_SURV_BARRACKS': {'address': 5260312, 'default': 4, 'maximum': 7},
 'UNIT_SURV_MACHINESHOP': {'address': 5260552, 'default': 4, 'maximum': 4},
 'UNIT_SURV_ARMOURY': {'address': 5260792, 'default': 1, 'maximum': 100},
 'UNIT_SURV_POWERSTATION': {'address': 5261032, 'default': 4, 'maximum': 100},
 'UNIT_SURV_DRILLRIG': {'address': 5261272, 'default': 10, 'maximum': 100},
 'UNIT_SURV_CONVERTER': {'address': 5261512, 'default': 4, 'maximum': 100},
 'UNIT_SURV_COLLECTOR': {'address': 5261752, 'default': 4, 'maximum': 100},
 'UNIT_SURV_REPAIRBAY': {'address': 5261992, 'default': 4, 'maximum': 100},
 'UNIT_SURV_RESEARCHLAB': {'address': 5262232, 'default': 1, 'maximum': 100},
 'UNIT_MUTE_OUTPOST': {'address': 5260152, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_BARRACKS': {'address': 5260392, 'default': 4, 'maximum': 7},
 'UNIT_MUTE_MACHINESHOP': {'address': 5260632, 'default': 4, 'maximum': 4},
 'UNIT_MUTE_ARMOURY': {'address': 5260872, 'default': 1, 'maximum': 100},
 'UNIT_MUTE_POWERSTATION': {'address': 5261112, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_DRILLRIG': {'address': 5261352, 'default': 10, 'maximum': 100},
 'UNIT_MUTE_CONVERTER': {'address': 5261592, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_COLLECTOR': {'address': 5261832, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_REPAIRBAY': {'address': 5262072, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_RESEARCHLAB': {'address': 5262312, 'default': 1, 'maximum': 100},
 'UNIT_TEMPLE': {'address': 5264152, 'default': 0, 'maximum': 0},
 'UNIT_ROBOT_OUTPOST': {'address': 5260232, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_BARRACKS': {'address': 5260472, 'default': 4, 'maximum': 7},
 'UNIT_ROBOT_MACHINESHOP': {'address': 5260712, 'default': 4, 'maximum': 4},
 'UNIT_ROBOT_ARMOURY': {'address': 5260952, 'default': 1, 'maximum': 100},
 'UNIT_ROBOT_POWERSTATION': {'address': 5261192, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_DRILLRIG': {'address': 5261432, 'default': 10, 'maximum': 100},
 'UNIT_ROBOT_CONVERTER': {'address': 5261672, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_COLLECTOR': {'address': 5261912, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_REPAIRBAY': {'address': 5262152, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_RESEARCHLAB': {'address': 5262392, 'default': 1, 'maximum': 100},
 'UNIT_SURV_TOWER1': {'address': 5262472, 'default': 4, 'maximum': 100},
 'UNIT_SURV_TOWER2': {'address': 5262552, 'default': 4, 'maximum': 100},
 'UNIT_SURV_TOWER3': {'address': 5262632, 'default': 4, 'maximum': 100},
 'UNIT_SURV_TOWER4': {'address': 5262712, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_TOWER1': {'address': 5263272, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_TOWER2': {'address': 5263352, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_TOWER3': {'address': 5263432, 'default': 4, 'maximum': 100},
 'UNIT_MUTE_TOWER4': {'address': 5263512, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_TOWER1': {'address': 5263592, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_TOWER2': {'address': 5263672, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_TOWER3': {'address': 5263752, 'default': 4, 'maximum': 100},
 'UNIT_ROBOT_TOWER4': {'address': 5263832, 'default': 4, 'maximum': 100},
 'UNIT_SURV_WALL1': {'address': 5262792, 'default': 100, 'maximum': 100},
 'UNIT_SURV_WALL2': {'address': 5262872, 'default': 20, 'maximum': 100},
 'UNIT_MUTE_WALL1': {'address': 5262952, 'default': 100, 'maximum': 100},
 'UNIT_MUTE_WALL2': {'address': 5263032, 'default': 20, 'maximum': 100},
 'UNIT_ROBOT_WALL1': {'address': 5263112, 'default': 100, 'maximum': 100},
 'UNIT_ROBOT_WALL2': {'address': 5263192, 'default': 20, 'maximum': 100}}


def validate(values):
    if not isinstance(values, dict) or set(values) != set(BUILDINGS):
        raise ValueError("Building limits must contain exactly the supported building IDs.")
    for key, value in values.items():
        spec = BUILDINGS[key]
        minimum = 0 if spec['default'] == 0 else 1
        if type(value) is not int or not minimum <= value <= spec['maximum']:
            raise ValueError(f"{key}: enter a whole number from {minimum} to {spec['maximum']}.")
    return dict(values)


class LimitsConfig:
    specs = BUILDINGS
    schema = 'kknd2-editor-building-limits'
    version = 1
    value_key = 'limits'
    title = 'Building limits'
    temporary_prefix = '.limits-'
    validate = staticmethod(validate)

    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.read_bytes() if self.path.exists() else None
        self.defaults = {key: spec['default'] for key, spec in self.specs.items()}
        self.values = dict(self.defaults)
        if self.raw is not None:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError(f"Duplicate setting: {key}")
                    result[key] = value
                return result
            doc = json.loads(self.raw.decode('utf-8'), object_pairs_hook=unique)
            if not isinstance(doc, dict) or set(doc) != {'schema', 'version', self.value_key} or doc['schema'] != self.schema or type(doc['version']) is not int :
                raise ValueError(f"Unsupported {self.title.lower()} schema/version.")
            self.values = self.decode_values(doc[self.value_key], doc['version'])
        self.needs_migration = self.raw is not None and doc['version'] != self.version
        self.saved = dict(self.values)
        self.undo_stack, self.redo_stack = [], []

    def decode_values(self, values, version):
        if version != self.version:
            raise ValueError(f'Unsupported {self.title.lower()} schema/version.')
        return self.validate(values)

    def apply(self, values):
        values = self.validate(values)
        if values != self.values:
            self.undo_stack.append(dict(self.values))
            self.values = values
            self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(dict(self.values))
            self.values = self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(dict(self.values))
            self.values = self.redo_stack.pop()

    def save(self):
        current = self.path.read_bytes() if self.path.exists() else None
        if current != self.raw:
            raise OSError(f"{self.title} changed outside the editor. Reopen the file before saving.")
        if self.raw is not None and self.values == self.saved and not self.needs_migration:
            return
        raw = (json.dumps({'schema': self.schema, 'version': self.version,
                          self.value_key: self.validate(self.values)}, indent=2) + '\n').encode('utf-8')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=self.temporary_prefix, suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            if self.path.read_bytes() != raw:
                raise OSError(f"{self.title} save verification failed.")
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.raw, self.saved = raw, dict(self.values)
        self.needs_migration = False
