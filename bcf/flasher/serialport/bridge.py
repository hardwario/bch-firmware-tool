#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import fcntl
import time
import sys
import glob
import struct
import math
import select
import os
from .error import *

PARITY_NONE = 0
PARITY_ODD = 1
PARITY_EVEN = 2

STOP_BIT_1 = 0
STOP_BIT_2 = 2

__all__ = ["Bridge", "get_list"]


def get_list():

    bridges = []
    bridge = []

    for hid in sorted(glob.glob('/dev/hidraw*')):
        try:
            file = open(hid, 'rb+', buffering=0)

            name = bytearray(256)
            fcntl.ioctl(file, 0x81004804, name)  # HIDIOCGRAWNAME(256)

            if name[:11] != b'FTDI FT260\x00':
                continue

            file.close()

            bridge.append(hid)

            if len(bridge) == 2:
                bridges.append(bridge)
                bridge = []

        except Exception as error:
            pass

    return bridges


class Bridge:

    def __init__(self, hid):
        try:
            self.file = open(hid, 'rb+', buffering=0)
        except Exception as e:
            raise ErrorOpenDevice('Could not open hid %s' % hid)

        try:
            fcntl.lockf(self.file, fcntl.LOCK_EX)
        except Exception as e:
            raise ErrorLockDevice('Could not lock device %s' % hid)

        flag = fcntl.fcntl(self.file, fcntl.F_GETFL)
        fcntl.fcntl(self.file, fcntl.F_SETFL, flag | os.O_NONBLOCK)

        # Clock 48 MHz
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x01, 0x02]))

        # No flow control mode
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x03, 0x04]))

        self.gpio = [0x00, 0x00]
        self.read_buffer = []
        self._write_gpio()

    def boot(self, state):
        if state:
            self.gpio[0] |= 0x20
        else:
            self.gpio[0] &= ~0x20
        self._write_gpio()

    def reset(self, state):
        if state:
            self.gpio[0] |= 0x10
        else:
            self.gpio[0] &= ~0x10
        self._write_gpio()

    def led(self, state):
        if state:
            self.gpio[1] |= 0x80
        else:
            self.gpio[1] &= ~0x00
        self._write_gpio()

    def _write_gpio(self):
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xB0, self.gpio[0], 0x30, self.gpio[1], 0x80]))

    def uart_reset(self):
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x41]))
        time.sleep(0.1)

    def uart_baundrate_set(self, br):
        speed = int(br).to_bytes(4, 'little', signed=False)
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x42]) + speed)

    def uart_data_bits_set(self, data_bits):
        if data_bits not in (7, 8):
            return
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x43, data_bits]))

    def uart_parity_set(self, parity):
        if parity not in (PARITY_NONE, PARITY_ODD, PARITY_EVEN):
            return
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x44, parity]))

    def uart_stop_bit_set(self, stop_bit):
        if stop_bit not in (STOP_BIT_1, STOP_BIT_2):
            return
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x45, stop_bit]))

    def uart_breaking_set(self, breaking):
        fcntl.ioctl(self.file, 0xC0054806, bytes([0xA1, 0x46, breaking]))

    def uart_write(self, buffer):
        for start in range(0, len(buffer), 60):
            stop = start + 60
            data = buffer[start:stop]
            report_id = math.ceil(len(data) / 4) + 0xF0
            self.file.write(bytes([report_id, len(data)] + list(data) + ([0] * (len(data) % 4))))

    def uart_read(self, length):
        # print('uart_read', length)
        timeout = time.time() + 0.5

        while length > len(self.read_buffer) and timeout > time.time():
            reads, _, _ = select.select([self.file], [], [], 0)
            if self.file in reads:
                data = self.file.read(64)
                # print('data', list(map(hex,data)))
                self.read_buffer += data[2:2 + data[1]]

        buffer = self.read_buffer[:length]
        self.read_buffer = self.read_buffer[length:]

        # print('uart_read buffer', list(map(hex,buffer)), self.read_buffer)
        return bytes(buffer)


class SerialPort:
    def __init__(self, device):
        self.b = Bridge(device)
        self.b.uart_baundrate_set(921600)
        self.b.uart_data_bits_set(8)
        self.b.uart_parity_set(PARITY_EVEN)
        self.b.uart_stop_bit_set(STOP_BIT_1)
        self.b.uart_breaking_set(0)

        self.write = self.b.uart_write
        self.read = self.b.uart_read

    def reset_input_buffer(self):
        return

    def reset_output_buffer(self):
        return

    def flush(self):
        return

    def boot_sequence(self):
        self.b.reset(True)
        self.b.boot(True)
        time.sleep(0.1)
        self.b.reset(False)
        time.sleep(0.1)
        self.b.boot(False)

    def reset_sequence(self):
        self.b.reset(True)
        time.sleep(0.1)
        self.b.reset(False)


if __name__ == '__main__':
    bridges = get_list()

    b = Bridge(bridges[0][1])
    # b.boot(False)

    b.uart_baundrate_set(921600)
    b.uart_data_bits(8)
    b.uart_parity_set(PARITY_EVEN)
    b.uart_stop_bit(STOP_BIT_1)

    b.uart_write(list(range(128)))
