# https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
# dummy demo of a server connecting sharing a dict to a client
import time
import logging
from multiprocessing import Manager

from p1daemon.workers import (
    HttpWorker,
    SieWorker,
    InfluxDbWorker,
    SolarEdgeWorker,
)

log = logging.getLogger(__name__)

def main():
    m = Manager()
    shared_dict = m.dict()
    SieWorker(shared_dict).start()

    time.sleep(10)
    InfluxDbWorker(shared_dict).start()
    HttpWorker(shared_dict).start()
    SolarEdgeWorker(shared_dict).start()

    while True:
        time.sleep(50)


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    log.info("Launching daemons.")
    main()
