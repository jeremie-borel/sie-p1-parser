# https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
# dummy demo of a server connecting sharing a dict to a client
import time
import datetime

from multiprocessing.managers import SyncManager
from multiprocessing import Process, Manager

from influxdb_client import Point
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import (
    SYNCHRONOUS,
    WritePrecision,
)


from p1parser.p1reader import SieP1Reader, get_map
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


class CustomManager(SyncManager):
    pass


class SieWorker(Process):
    def __init__(self, shared_dict: dict):
        self.reader = SieP1Reader()
        self.data = shared_dict

        for name, unit in get_map():
            if unit in ['W', 'A', 'V']:
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
        for data in self.reader.read():
            for key, phd in data.items():
                self.data[key]['twa'](phd.time, phd.value)


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

            points = [
                self.as_point(key, arg)
                for key, arg in self.data.items()
            ]

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
