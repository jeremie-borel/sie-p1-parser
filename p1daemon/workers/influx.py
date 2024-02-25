# https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
# dummy demo of a server connecting sharing a dict to a client
import time
import logging
import datetime
import urllib3
from multiprocessing import Process

from influxdb_client import Point
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import (
    SYNCHRONOUS,
    WritePrecision,
)

from ..config import (
    token,
    host,
    orgid,
    bucket,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)


class InfluxDbWorker(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        self.client = InfluxDBClient(
            url=host,
            token=token,
            org=orgid,
            verify_ssl=False,
        )
        self.api = self.client.write_api(write_options=SYNCHRONOUS)
        super().__init__()

    def as_point(self, name: str, ct: datetime.datetime, value: float, unit: str) -> Point:
        label = 'value'
        if unit == 'V':
            label = 'voltage'
        elif unit == 'A':
            label = 'current'
        elif unit == 'W':
            label == 'power'
        elif unit == 'Wh':
            label = 'energy'

        return (
            Point("house_power")
            .tag("sensor", "p1sie")
            .tag("type", label)
            .tag("unit", unit)
            .field(name, value)
            .time(ct)
        )

    def run(self):
        while True:
            if not self.data:
                time.sleep(2)
                continue

            try:
                points = []
                for key, twa in self.data.items():
                    if key == 'evcc':
                        continue
                    ct, value = twa.mean()
                    twa.reset()
                    # force update of shared memory
                    self.data[key] = twa
                    points.append(self.as_point(key, ct, value, twa.unit))
            except AttributeError as e:
                print(f"Wrong object initialzation: {e}")
                time.sleep(2)
                continue

            time.sleep(10)

            log.debug(f"Writing to bucket {bucket}")
            self.api.write(
                bucket=bucket,
                record=points,
                write_precision=WritePrecision.S
            )
            time.sleep(30)
