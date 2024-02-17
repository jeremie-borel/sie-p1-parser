from typing import Sequence, Generator

from collections import namedtuple

PhysicalData = namedtuple('PhysicalData', 'time value unit')

_obis_map = [
    (bytes.fromhex('0100010700ff'), 'input_power', 'W'),
    (bytes.fromhex('0100020700ff'), 'output_power', 'W'),
    (bytes.fromhex('0100200700ff'), 'voltage1', 'V'),
    (bytes.fromhex('0100340700ff'), 'voltage2', 'V'),
    (bytes.fromhex('0100480700ff'), 'voltage3', 'V'),
    (bytes.fromhex('01001f0700ff'), 'current1', 'A'),
    (bytes.fromhex('0100330700ff'), 'current2', 'A'),
    (bytes.fromhex('0100470700ff'), 'current3', 'A'),

    (bytes.fromhex('0100010800ff'), 'energy_import_total', 'Wh'),
    (bytes.fromhex('0100020800ff'), 'energy_export_total', 'Wh'),

    (bytes.fromhex('0100010801ff'), 'energy_import_tarif_plein', 'Wh'),
    (bytes.fromhex('0100010802ff'), 'energy_import_tarif_creux', 'Wh'),
    (bytes.fromhex('0100020801ff'), 'energy_export_tarif_plein', 'Wh'),
    (bytes.fromhex('0100020802ff'), 'energy_export_tarif_plein', 'Wh'),
]
_unit_map = {
    27:'W',
    30:'Wh',
    35:'V',
    33:'A',
}

def get_meters() -> Generator[tuple[bytes, str, str],None,None]:
    for obis, name,unit in _obis_map:
        yield obis, name, unit

def get_name(obis:bytes):
    for tobis, name, unit in _obis_map:
        if tobis == obis:
            return name