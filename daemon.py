# https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
# dummy demo of a server connecting sharing a dict to a client
import time
import logging
import datetime
import urllib3
from json import dumps
from multiprocessing import Process, Manager, Lock

from influxdb_client import Point
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import (
    SYNCHRONOUS,
    WritePrecision,
)

from p1parser.translator import get_meters
from p1parser.p1reader import SieP1Reader
from p1parser.stats import TimeWeightedAverage, LastValue


from p1parser.tokens import (
    token,
    host,
    orgid,
)

from http.server import HTTPServer, BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

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

        self.obis2name = {}
        self.obis2units = {}
        for obis, name, unit in get_meters():
            self.obis2name[obis] = name
            if unit in ['A', 'W', 'V']:
                self.data[name] = TimeWeightedAverage(unit)
            else:
                self.data[name] = LastValue(unit)

        self.data['evcc'] = {}
        super().__init__()

    def run(self):
        # starts infinite loop
        for ct, all_data in self.reader.read():
            evcc = {'power': 0}
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
                # sign of power must follow evcc conventions
                if name == 'input_power' and v > 0:
                    evcc['power'] = int(v)
                elif name == 'output_power' and v > 0:
                    evcc['power'] = -int(v)
                # re-writes dict so that shared memory is updated.
                self.data[name] = twa
            self.data['evcc'] = evcc


class InfluxDb(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        self.api = client.write_api(write_options=SYNCHRONOUS)
        super().__init__()

    def as_point(self, name: str, ct:datetime.datetime, value:float, unit:str) -> Point:
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
            Point("home_power")
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

class GetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        copy = {k:v for k,v in self.server.data.get('evcc',{}).items()}
        self.wfile.write(dumps(copy).encode())

class MyHttpServer(HTTPServer):
    def __init__(self, shared_dict):
        self.data = shared_dict
        super().__init__(('0.0.0.0', 8123), GetHandler)

class HttpProcess(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        self.server = MyHttpServer(shared_dict)
        super().__init__()

    def run(self):
        self.server.serve_forever()

def main():
    m = Manager()
    shared_dict = m.dict()
    SieWorker(shared_dict).start()

    time.sleep(10)
    InfluxDb(shared_dict).start()

    HttpProcess(shared_dict).start()

    while True:
        time.sleep(50)


if __name__ == '__main__':
    main()
    print("done")
