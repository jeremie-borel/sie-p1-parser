# https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
# dummy demo of a server connecting sharing a dict to a client
import time

from multiprocessing.managers import SyncManager
from multiprocessing import Process
# from queue import Queue
import random
from ctypes import Structure, c_double, c_float



class CustomManager(SyncManager):
    pass

class Worker(Process):
    def __init__(self, p):
        self.p = p
        super().__init__()

    def run(self):
        while True:
            a = random.randint(1, 99)
            self.p.update({'a':a})
            print(f"Set {a}")
            time.sleep(5)


syncdict = {}
def get_dict():
    return syncdict

def main():
    CustomManager.register('myfunc', callable=get_dict)
    m = CustomManager(address=('127.0.0.1', 50000), authkey=b'abracadabra')

    m.start()
    w = Worker(m.myfunc())
    w.start()

    while True:
        time.sleep(5)
    print("starting server")

if __name__ == '__main__':
    main()
    print("done")
