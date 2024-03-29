import logging
import datetime

from multiprocessing import Process

from p1daemon.translator import get_meters
from p1daemon.p1reader import SieP1Reader
from p1daemon.stats import TimeWeightedAverage, LastValue


from ..config import (
    EVCC_KEY,
)
from ..stats import as_datetime, _zurich

log = logging.getLogger(__name__)

class SieWorker(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        self.reader = SieP1Reader()

        self.obis2name = {}
        self.obis2units = {}
        for obis, name, unit in get_meters():
            self.obis2name[obis] = name
            if unit in ['A', 'W', 'V']:
                self.data[name] = TimeWeightedAverage(unit)
            elif unit in ['Wh']:
                self.data[name] = LastValue(unit)
            else:
                raise ValueError("Unit is unknown")

        self.data[EVCC_KEY] = {}
        super().__init__()

    def to_evcc(self, key:str, value:float, evcc:dict[str,float]) -> None:
        if key == 'input_power' and value > 0:
            evcc['power'] = int(value)
        elif key == 'output_power' and value > 0:
            # sign of power must follow evcc conventions
            evcc['power'] = -int(value)
        elif key in ['current1','current2','current3']:
            evcc[key] = value


    def run(self):
        # starts infinite loop
        log.info("Running worker for sie reading.")
        for ct, all_data in self.reader.read():
            now = datetime.datetime.now(tz=_zurich)
            evcc = {
                'power': 0,
                'pw_stamp': as_datetime(now),
            }
            for item in all_data:
                if len(item) < 3:
                    continue
                obis, value, (exponent, _unit) = item
                try:
                    name = self.obis2name[bytes(obis)]
                except KeyError:
                    continue
                v = float(round(value*10**exponent, 4))
                twa = self.data[name]
                twa.push(ct, v)
                self.to_evcc(name, v, evcc)
                # re-writes dict so that shared memory is updated.
                self.data[name] = twa

            current_data = {k:v for k,v in self.data.get(EVCC_KEY, {}).items()}
            current_data.update(evcc)
            self.data[EVCC_KEY] = current_data
