# dumy demonstration of a client connecting to server
import time

from queue import Empty


from multiprocessing.managers import BaseManager, SyncManager
class QueueManager(SyncManager):
    pass
QueueManager.register('myfunc')
m = QueueManager(address=('127.0.0.1', 50000), authkey=b'abracadabra')
m.connect()

while True:
    p = m.myfunc()
    for k,v in p.items():
        print(k,v)
    time.sleep(2)
# queue.put(sys.argv[1])

