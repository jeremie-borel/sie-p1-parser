
_map = [
    ('020309060100010700ff06', 'input_power', 'W'),
    ('020309060100020700ff06', 'output_power', 'W'),
    ('020309060100200700ff12', 'voltage1', 'V'),
    ('020309060100340700ff12', 'voltage2', 'V'),
    ('020309060100480700ff12', 'voltage3', 'V'),
    ('0203090601001f0700ff12', 'current1', 'A'),
    ('020309060100330700ff12', 'current2', 'A'),
    ('020309060100470700ff12', 'current3', 'A'),
    ('020309060100010801ff06', 'energy_import_tarif_plein', 'Wh'),
    ('020309060100010802ff06', 'energy_import_tarif_creux', 'Wh'),
    ('020309060100020801ff06', 'energy_export_tarif_plein', 'Wh'),
    ('020309060100020802ff06', 'energy_export_tarif_plein', 'Wh'),
]

def get_map() -> list[tuple[str, str]]:
    return [
        (name, unit)
        for _, name, unit in _map
    ]

