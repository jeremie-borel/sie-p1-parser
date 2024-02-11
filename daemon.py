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

        self.counters = {}
        for name, unit in get_map():
            if unit in ['W', 'A', 'V']:
                self.counters[name] = TimeWeightedAverage()
            else:
                self.counters[name] = LastValue()
        super().__init__()

    def run(self):
        for data in self.reader.read():
            means = {}
            for key, phd in data.items():
                self.counters[key](phd.time, phd.value)
                meantime, meanvalue = self.counters[key].mean()
                means[key] = PhysicalData(meantime, meanvalue, phd.unit)

            self.data.update(means)


class InfluxDb(Process):
    def __init__(self, shared_dict: dict[str, PhysicalData]):
        self.data = shared_dict
        self.api = client.write_api(write_options=SYNCHRONOUS)
        super().__init__()

    def as_point(self, name: str, d:PhysicalData) -> Point:
        label = 'value'
        if d.unit == 'V':
            label = 'voltage'
        elif d.unit == 'A':
            label = 'current'
        elif d.unit == 'W':
            label == 'power'
        elif d.unit == 'Wh':
            label = 'energy'
        return (
            Point("home_power")
            .tag("location", "atelier")
            .tag("sensor", "p1sie")
            .tag("type", label)
            .tag("unit", d.unit)
            .field(name, float(d.value))
            .time(d.time)
        )

    def run(self):
        while True:
            if not self.data:
                time.sleep(2)
                continue

            points = [
                self.as_point(key, phd)
                for key, phd in self.data.items()
            ]

            print(f"will write now")
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
