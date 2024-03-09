import datetime
import time
import requests
import logging

from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)

from ..config import (
    SOLAREDGE_API,
    SOLAREDGE_ID,
    EVCC_KEY,
)
from ..stats import (
    _zurich,
    as_datetime,
)

from multiprocessing import Process

MIN_QUERY_INTERVAL = 15*60 # min time between updates of SE value.
QUERY_TIME_RANGE = (5,20)

log = logging.getLogger(__name__)

def query_solaredge(time_unit: str = 'QUARTER_OF_AN_HOUR') -> dict:
    """
    Query solar edge data. Either power of energy for the given time
    periode. Max diff between :start: and :end: is one month.
    """
    now = datetime.datetime.now(tz=_zurich)

    url = f"https://monitoringapi.solaredge.com/site/{SOLAREDGE_ID}/powerDetails.json"
    kwargs = {
        'api_key': SOLAREDGE_API,
        'startTime': as_datetime(now - datetime.timedelta(minutes=1)),
        'endTime': as_datetime(now),
        'timeUnit': time_unit,
        'meters': "PRODUCTION"
    }
    r = requests.get(url, params=kwargs, verify=False)
    r.raise_for_status()
    return r.json()

def query_power_value() -> float:
    try:
        data = query_solaredge()
    except Exception as e:
        log.error(f"Got an exception while querying solaredge server")
        log.exception(e)
        return 0.0
    try:
        val = float(data['powerDetails']['meters'][0]['values'][0]['value'])
    except Exception as e:
        log.error(f"Got an exception while querying solaredge server")
        log.exception(e)
        return 0.0
    return round(val,3)

class SolarEdgeWorker(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        super().__init__()

    def test_is_daytime(self) -> bool:
        now = datetime.datetime.now(tz=_zurich)
        start, end = QUERY_TIME_RANGE
        if start <= now.hour <= end:
            return True
        return False

    def run(self):
        while True:
            if self.test_is_daytime():
                log.info("Hitting solarege server")
                value = query_power_value()
            else:
                log.info("It's night return 0 solar power.")
                value = 0.0
            
            now = datetime.datetime.now(tz=_zurich)
            copy = {k:v for k,v in self.data.get(EVCC_KEY,{}).items()}
            copy['solar_power'] = value
            copy['solar_stamp'] = as_datetime(now)
            self.data[EVCC_KEY] = copy
            
            time.sleep(MIN_QUERY_INTERVAL)


def main():
    print("Get SE solar power")
    print(query_power_value())

if __name__ == '__main__':
    main()
