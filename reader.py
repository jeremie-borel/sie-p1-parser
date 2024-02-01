"""Proof of concept for a lame script that parses HDLC frames coming from P1 port for ASKRA AM550 meters."""

import serial
import time
import sys
from typing import Generator

# flag wrapping hdlc frames
flag_char = bytes.fromhex('7e')
# starts a frame sequence
start_seq = bytes.fromhex('7ea8a4cf0223039996e6e700')
# matches between value and expnoent. Used to tell apart 2 bytes from 4 bytes values
middle_pattern = bytes.fromhex('02020f')

def format(raw:str) -> str:
    """Roughly format a frame to make it more or less human readable"""
    raw = raw.replace('02020906', '\n  0202 0906')
    raw = raw.replace('02030906', '\n  0203 0906')

    raw = raw.replace('7ea8a4cf0223039996e6e700', '7e a8a4 cf 0223 039996 e6e700\n')
    raw = raw[:-6] + '\n' + raw[-6:-2] + ' ' + raw[-2:]
    return raw

def _parse_value_type1(sig:bytearray, frame:bytearray) -> int:
    pos = frame.find(sig)
    if pos < 0:
        raise ValueError(f"Could not find {sig.hex()}")
    start = pos + len(sig)
    middle = frame.find(middle_pattern, start)
    if middle <0 or middle - start > 12:
        raise ValueError(f"Could not find middle value in {frame[start:start+20].hex()}")
    
    byte_mantis = frame[start:middle]
    byte_exponent = frame[middle+3:middle+4]

    # we use two different methods because exponent is signed.
    mantis = int.from_bytes(byte_mantis, byteorder="big", signed=False)
    exponent = int.from_bytes(byte_exponent, byteorder="big", signed=True)
    # exponent = struct.unpack('>b', byte_exponent)[0]

    return mantis*10**exponent

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

raw_array = b''

# one should tweak the tty to its need.
def get_frame(tty:str='/dev/ttyUSB0') -> Generator[bytearray, None, None]:
    global raw_array
    with serial.Serial(tty, baudrate=115200, bytesize=8, parity='N',stopbits=1, timeout=3) as ser:
        full_data = b''
        bytes_array = b''
        while True:
            time.sleep(0.5)
            b = ser.read_until(expected=flag_char, size=900)
            bytes_array += b
            raw_array += b


            hdlc_flag =  bytes_array.find(flag_char, 0)
            end_flag =  bytes_array.find(flag_char, hdlc_flag+1)

            if end_flag < 0 or hdlc_flag < 0:
                continue

            # not a frame. We took an end as a start.
            if end_flag - hdlc_flag < 8:
                hdlc_flag = end_flag
                end_flag =  bytes_array.find(flag_char, hdlc_flag+1)

            data_frame = bytes_array[hdlc_flag:end_flag+1]
            bytes_array = bytes_array[end_flag+1:]

            # if begin of frame matches start signature, we have in hand
            # the previous packet ended.
            if data_frame[:len(start_seq)] == start_seq:
                raw_array = b''
                full_data = data_frame
                continue

            if data_frame[3:6] != bytes.fromhex('cf0223'):
                print("Frame header is not as expected. Resetting full frame.", file=sys.stderr)
                full_data = b""
                continue

            head_size = 9
            # appends data after flag + 7bytes = 8 bytes.
            # truncate current frame from the CRC and end flag bytes (3)

            full_data = full_data[:-3] + data_frame[head_size:]

            if data_frame[1:3] == bytes.fromhex('a02e'):
                yield full_data
                full_data = b''


for frame in get_frame():
    print("_"*30)
    print(format(frame.hex()))
    print("_"*30)

    for sig, name, unit in _map:
        try:
            v = _parse_value_type1(bytes.fromhex(sig), frame)
        except ValueError:
            print(raw_array.hex())
        print(f"{name}: {v} [{unit}]")

