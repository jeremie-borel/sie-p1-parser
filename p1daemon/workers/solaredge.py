import datetime
import requests
import pytz

import logging

from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
# disable_warnings(InsecureRequestWarning)


from ..config import (
    SOLAREDGE_API,
    SOLAREDGE_ID,
)

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import (
    SYNCHRONOUS,
    WritePrecision,
)

ENERGY = 0
POWER = 1
_map = {
    ENERGY: 'energy',
    POWER: 'power',
}

_zurich = pytz.timezone("Europe/Zurich")

def as_date(date:datetime) -> str:
    """Returns the date according to SolarEdge format API"""
    return date.strftime('%Y-%m-%d')

def as_datetime(date:datetime) -> str:
    """Returns the datetime according to SolarEdge
    format API (see manual page 22 for example).
    
    Assumes TZ is local tz (i.e. Zurich)"""
    return date.strftime('%Y-%m-%d %H:%M:%S')

def from_stamp(date:str) -> datetime:
    """Returns the datetime according to SolarEdge
    format API (see manual page 22 for example)"""
    d = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    d = _zurich.localize(d)
    return d


def _query_data(
    time_unit: str = 'QUARTER_OF_AN_HOUR'
) -> dict:
    """
    Query solar edge data. Either power of energy for the given time
    periode. Max diff between :start: and :end: is one month.
    """
    now = datetime.datetime.now()
    

    t = _map[_type]
    url = f"https://monitoringapi.solaredge.com/site/{SOLAREDGE_ID}/power.json"
    kwargs = {
        'api_key': SOLAREDGE_API,
        'startTime': as_datetime(now - datetime.timedelta(minutes=10)),
        'endTime': as_datetime(now),
        'timeUnit': time_unit,
        'meters': "PRODUCTION"
    }
    r = requests.get(url, params=kwargs, verify=False)
    r.raise_for_status()
    return r.json()


def se_query_power_data() -> tuple[datetime.datetime, float]:
    out = _query_data()
    data = out['power']['values'][0]
    value = float(data['value'])
    date = from_stamp(data['date'])


def se_query_energy_data(start: datetime, end: datetime) -> dict:
    return _query_data(ENERGY, start, end)


def main():
    now = datetime.datetime.now(tz=_zurich)

    if now - last > datetime.timedelta(days=20):
        now = last + datetime.timedelta(days=20)

    log.info(f"Loading SolarEdge data from {last} to {now} into influxdb.")

    data = se_query_power_data(last, now)


if __name__ == '__main__':
    main()
