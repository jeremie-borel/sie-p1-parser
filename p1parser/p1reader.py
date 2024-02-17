"""Proof of concept for a lame script that parses HDLC frames coming from P1 port for ASKRA AM550 meters."""
from typing import Generator

import logging
import datetime
import serial
import time
from collections import namedtuple

from dlms_cosem.cosem import Obis
from dlms_cosem.hdlc.frames import UnnumberedInformationFrame
from dlms_cosem.hdlc.exceptions import HdlcParsingError
from dlms_cosem.protocol.xdlms.data_notification import DataNotification
from dlms_cosem.utils import parse_as_dlms_data

TimedResults = namedtuple('TimedResults', 'datetime results')

# flag wrapping hdlc frames
flag_char = bytes.fromhex('7e')

log = logging.getLogger(__name__)


_map = [
    ('020309060100010700ff06', 'input_power', 'W'),
    ('020309060100020700ff06', 'output_power', 'W'),
    ('020309060100200700ff12', 'voltage1', 'V'),
    ('020309060100340700ff12', 'voltage2', 'V'),
    ('020309060100480700ff12', 'voltage3', 'V'),
    ('0203090601001f0700ff12', 'current1', 'A'),
    ('020309060100330700ff12', 'current2', 'A'),
    ('020309060100470700ff12', 'current3', 'A'),
    ('020309060100010801ff06', 'energy_import_tarif_plein', 'Wh'),
    ('020309060100010802ff06', 'energy_import_tarif_creux', 'Wh'),
    ('020309060100020801ff06', 'energy_export_tarif_plein', 'Wh'),
    ('020309060100020802ff06', 'energy_export_tarif_plein', 'Wh'),
]

def get_map() -> list[tuple[str, str]]:
    return [
        (name, unit)
        for _, name, unit in _map
    ]


class SieP1Reader:
    """
    Find the correct tty using for example this answer:
    https://unix.stackexchange.com/a/144735/601656

    Then create a permanent link to the tty by using:
    https://unix.stackexchange.com/questions/445450/how-to-create-a-permanent-symlink-to-a-device

    to create /etc/udev/rules.d/99_usb0.rules with content:
    KERNEL=="ttyUSB0", SYMLINK+="serialFTDI"

    Don't forget to 
    usermod -a -G dialout <yourname>
    to allow to read the tty with a unpriviledge user and to login and logout to have the new
    group permissions applied.
    """
    def __init__(self, tty: str = '/dev/serialFTDI'):
        self.tty = tty
        self.raw_array = b''

    # one should tweak the tty to its need.
    def _get_frame(self) -> Generator[bytearray, None, None]:
        serial_socket = serial.Serial(
            self.tty,
            baudrate=115200,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=3
        )
        bytes_array = b''
        with serial_socket:
            while True:
                raw_data = serial_socket.read_until(expected=flag_char)
                if not raw_data:
                    time.sleep(0.1)
                    continue
                    
                bytes_array += raw_data

                start_flag = bytes_array.find(flag_char, 0)
                end_flag = bytes_array.find(flag_char, start_flag+1)

                if end_flag < 0 or start_flag < 0:
                    continue

                # not a frame. We took an end as a start.
                # Truncates the beginning
                if end_flag - start_flag < 8:
                    bytes_array = bytes_array[end_flag:]
                    continue

                data_frame = bytes_array[start_flag:end_flag+1]
                bytes_array = bytes_array[end_flag+1:]
                yield data_frame

    def read(self) -> Generator[list[int], None, None]:
        # Reads frames until final=True and return the parsed dlms objects.
        payloads = b''
        for data_frame in self._get_frame():
            try:
                frame = UnnumberedInformationFrame.from_bytes(data_frame)
                payloads += frame.payload
            except HdlcParsingError:
                log.error("Skipped a frame")
                payloads = b''
                continue

            if frame.final:
                try:       
                    # first 3 bytes should be discarded as per
                    # https://github.com/u9n/dlms-cosem/blob/fb3a66980352beba1d4ab26d6c0ea34de2919aef/examples/parse_norwegian_han.py#L32
                    dn = DataNotification.from_bytes(payloads[3:])
                except ValueError:
                    log.error("Could not parse the payload. Skipping this frame.")
                    payloads = b''
                    continue
                payloads = b''

                result = parse_as_dlms_data(dn.body)
                t = dn.date_time or datetime.datetime.now(tz=datetime.timezone.utc)

                yield t, result


def main():
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    reader = SieP1Reader()
    log.info("Hit Ctrl+C to stop the script")
    for data in reader.read():
        print('data:', data)



if __name__ == '__main__':
    main()
