from typing import Any
import datetime
import copy

from collections import namedtuple

PhysicalData = namedtuple('PhysicalData', 'time value unit')

# https://www.timescale.com/blog/what-time-weighted-averages-are-and-why-you-should-care/
class TimeWeightedAverage:
    # t0: datetime.datetime
    # ti: datetime.datetime
    # vi: float
    # sum: float

    def __init__(self, unit:str):
        self.unit = unit
        self._initialize = False
        self.sum = 0

    def reset(self):
        self._initialize = False        

    def push(self, t: datetime.datetime, v: float) -> None:
        tt = copy.copy(t)
        if not self._initialize:
            self.t0 = tt
            self.ti = tt
            self.vi = v
            self.sum = 0
            self._initialize = True
            return

        self.sum += (self.vi+v)/2*(t-self.ti).total_seconds()
        self.ti = tt
        self.vi = v

    def mean(self) -> tuple[datetime.datetime, float]:
        dt = (self.ti - self.t0).total_seconds()
        if dt == 0:
            return self.ti, self.vi
        return (
            self.t0 + datetime.timedelta(seconds=0.5*dt),
            self.sum / dt
        )

class LastValue:
    ti: datetime.datetime
    vi: float


    def __init__(self, unit:str) -> None:
        self.unit = unit
        self._initialize = None

    def reset(self):
        pass

    def push(self, t: datetime.datetime, v: float) -> None:
        self.ti = t
        self.vi = v

    def mean(self) -> tuple[datetime.datetime, float]:
        return self.ti, self.vi

def main():
    data = [
        (datetime.datetime(2024, 1, 18, 22, 1), 1.0),
        (datetime.datetime(2024, 1, 18, 22, 2), 1.0),
        (datetime.datetime(2024, 1, 18, 22, 3), 2.0),
        (datetime.datetime(2024, 1, 18, 22, 4), 1.0),
        # (datetime.datetime(2024, 1, 18, 22, 5), 1.0),
        # (datetime.datetime(2024, 1, 18, 22, 6), 1.0),
        # (datetime.datetime(2024, 1, 18, 22, 7), 1.0),
        # (datetime.datetime(2024, 1, 18, 22, 30), 8.0),
    ]
    print("run me")
    twa = TimeWeightedAverage('')
    for t,v in data:
        twa.push(t,v)
    print(twa.mean())

if __name__ == '__main__':
    main()