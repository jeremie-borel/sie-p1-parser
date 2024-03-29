"""Proof of concept for a lame script that parses HDLC frames coming from P1 port for ASKRA AM550 meters."""
from typing import Generator

import logging
import datetime
import serial
import time

from dlms_cosem.hdlc.frames import UnnumberedInformationFrame
from dlms_cosem.hdlc.exceptions import HdlcParsingError
from dlms_cosem.protocol.xdlms.data_notification import DataNotification
from dlms_cosem.utils import parse_as_dlms_data

# flag wrapping hdlc frames
flag_char = bytes.fromhex('7e')

log = logging.getLogger(__name__)


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

    def __init__(self, tty: str = ""):
        from p1daemon.config import serial_tty
        self.tty = tty or serial_tty
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

                if len(raw_data) == 1:
                    continue

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
        error_flag = False
        for count, data_frame in enumerate(self._get_frame()):
            try:
                frame = UnnumberedInformationFrame.from_bytes(data_frame)
                payloads += frame.payload

                if frame.final:
                    if error_flag:
                        error_flag = False
                        log.warning("starting fresh after final frame")
                        continue

                    # first 3 bytes should be discarded as per
                    # https://github.com/u9n/dlms-cosem/blob/fb3a66980352beba1d4ab26d6c0ea34de2919aef/examples/parse_norwegian_han.py#L32
                    dn = DataNotification.from_bytes(payloads[3:])

                    result = parse_as_dlms_data(dn.body)
                    payloads = b''
                    t = dn.date_time or datetime.datetime.now(
                        tz=datetime.timezone.utc
                    )
                    if count%50==0:
                        log.debug(f"P1 parser returns frame {count}"
                    )
                    yield t, result

            except KeyError as e:
                log.error("Probably parse_as_dlms that failed.")
                log.exception(e)
                payloads = b''
            except ValueError as e:
                log.error("Could not parse the payload. Skipping this frame.")
                log.exception(e)
                payloads = b''
            except HdlcParsingError as e:
                log.error(f"Skipped a frame")
                log.exception(e)
                error_flag = True
                payloads = b''
            except Exception as e:
                log.error("Generic error:")
                log.exception(e)
                error_flag = True
                payloads = b''


def main():
    import sys, os
    dir_path = os.path.dirname(os.path.realpath(__file__))
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    sys.path.append(os.path.join(dir_path, '../'))

    reader = SieP1Reader()
    log.info("Hit Ctrl+C to stop the script")
    for dt, data in reader.read():
        print("Time is ", dt)
        for item in data:
            print(item)


if __name__ == '__main__':
    main()
