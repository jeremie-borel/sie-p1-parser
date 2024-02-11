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

def get_client() -> InfluxDBClient:
    return InfluxDBClient(
        url=host,
        token=token,
        org=orgid,
        verify_ssl=False,
        timeout=60,
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
            for key, (t, value, unit) in data.items():
                self.counters[key](t, value)
                means[key] = PhysicalData(t, self.counters[key].mean(), unit)

            self.data.update(means)


class InfluxDb(Process):
    def __init__(self, shared_dict: dict[str, PhysicalData]):
        self.data = shared_dict
        super().__init__()

    def as_point(self, name: str, t: datetime.datetime, v: float, unit: str) -> Point:
        label = 'value'
        if unit == 'V':
            label = 'voltage'
        elif unit == 'A':
            label = 'current'
        elif unit == 'W':
            label == 'power'
        elif unit == 'Wh':
            label = 'energy'
        return Point.from_dict({
            "measurement": "home_power",
            "tags": {'type': label, 'sensor': 'p1sie'},
            "fields": {'unit': unit, 'value':v},
            "time": t,
        })

    def run(self):
        while True:
            if not self.data:
                time.sleep(2)
                continue

            points = [
                self.as_point(key, t, v, unit)
                for key, (t, v, unit) in self.data.items()
            ]

            print(f"will write now")
            client = get_client()
            api = client.write_api(write_options=SYNCHRONOUS)
            api.write(
                bucket="dummy",
                records=points,
                write_precision=WritePrecision.S,
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
