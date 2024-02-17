# https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
# dummy demo of a server connecting sharing a dict to a client
import time
import datetime

from multiprocessing import Process, Manager

from influxdb_client import Point
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import (
    SYNCHRONOUS,
    WritePrecision,
)

from p1parser.translator import get_meters, get_name
from p1parser.p1reader import SieP1Reader
from p1parser.stats import TimeWeightedAverage, LastValue, PhysicalData

from p1parser.tokens import (
    token,
    host,
    orgid,
)

bucket = "dummy"
client = InfluxDBClient(
    url=host,
    token=token,
    org=orgid,
    verify_ssl=False,
)



class SieWorker(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        self.reader = SieP1Reader()

        for obis, name, unit in get_meters():
            if unit in ['A', 'W', 'V']:
                self.data[name] = {
                    'twa': TimeWeightedAverage(),
                    'unit': unit,
                }
            else:
                self.data[name] = {
                    'twa': LastValue(),
                    'unit': unit,
                }
        super().__init__()

    def run(self):
        for ct, all_data in self.reader.read():
            for item in all_data:
                if len(item) < 3:
                    continue
                obis, value, (exponent, _unit) = item
                key = get_name(obis)
                if not key:
                    continue
                v = float(round(value*10**exponent, 4))
                print(key, v)
                self.data[key]['twa'](ct, v)


class InfluxDb(Process):
    def __init__(self, shared_dict: dict[str, PhysicalData]):
        self.data = shared_dict
        self.api = client.write_api(write_options=SYNCHRONOUS)
        super().__init__()

    def as_point(self, name: str, arg:dict) -> Point:
        label = 'value'
        unit = arg['unit']
        if unit == 'V':
            label = 'voltage'
        elif unit == 'A':
            label = 'current'
        elif unit == 'W':
            label == 'power'
        elif unit == 'Wh':
            label = 'energy'
        t, value = arg['twa'].mean()
        arg['twa'].reset()

        return (
            Point("home_power")
            .tag("sensor", "p1sie")
            .tag("type", label)
            .tag("unit", unit)
            .field(name, float(value))
            .time(t)
        )

    def run(self):
        while True:
            if not self.data:
                time.sleep(2)
                continue

            try:
                points = []
                for key, arg in self.data.items():
                    print(key)
                    points.append(self.as_point(key, arg))
            except AttributeError as e:
                print(f"Wrong object initialzation: {e}")
                time.sleep(5)
                continue

            print(f"write data")
            self.api.write(
                bucket=bucket,
                record=points,
                write_precision=WritePrecision.S
            )
            time.sleep(30)


def main():
    m = Manager()
    shared_dict = m.dict()
    SieWorker(shared_dict).start()

    time.sleep(10)
    InfluxDb(shared_dict).start()

    while True:
        time.sleep(5)


if __name__ == '__main__':
    main()
    print("done")
