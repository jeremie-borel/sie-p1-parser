# https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
# dummy demo of a server connecting sharing a dict to a client
import time

from multiprocessing.managers import SyncManager
from multiprocessing import Process, Manager

from p1parser.p1reader import SieP1Reader


class CustomManager(SyncManager):
    pass


class SieWorker(Process):
    def __init__(self, shared_dict: dict):
        self.reader = SieP1Reader()
        self.data = shared_dict
        super().__init__()

    def run(self):
        for data in self.reader.read():
            self.data.update(data)
            time.sleep(10)

class InfluxDb(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        super().__init__()
    
    def run(self):
        while True:
            print(f"Woud do something with {self.data}")
            time.sleep(6)

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
