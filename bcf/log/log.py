#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import sys
import os
import serial
from datetime import datetime
import math
from colorama import init, Fore, Style
try:
    import fcntl
except ImportError:
    fcntl = None

log_level_color_lut = {'D': Fore.MAGENTA, 'I': Fore.GREEN, 'W': Fore.YELLOW, 'E': Fore.RED}


def add_arguments(action):
    action.add_argument('--device', help='device', required=True)
    action.add_argument('--time', help='show time', action='store_true')
    action.add_argument('--no-color', help='disable color', action='store_true')
    action.add_argument('--record', nargs='?', help="record to file", metavar='FILENAME')
    return action


class Log(object):
    def __init__(self, show_time, no_color, record_file):
        self._show_time = show_time
        self._no_color = no_color
        self._record_file = record_file

    def print(self, line):
        index = line.find("<")
        if index < 0:
            return
        level_char = line[index + 1]

        if self._show_time:
            dt = datetime.now()

            time = dt.strftime('%Y-%m-%d %H:%M:%S.') + "%02i " % round(dt.microsecond / 10000)
        else:
            time = ""

        if self._record_file:
            self._record_file.write(time + line + os.linesep)
            self._record_file.flush()

        if self._no_color:
            print(time + line)
        else:
            print(log_level_color_lut[level_char] + time + line[:index + 3] + Style.RESET_ALL + line[index + 3:])


class SerialPortLog(Log):
    def __init__(self, device, show_time, no_color, record_file):
        Log.__init__(self, show_time, no_color, record_file)
        self.ser = None
        try:
            self.ser = serial.Serial(device, baudrate=115200, timeout=3.0)
        except serial.serialutil.SerialException as e:
            if e.errno == 2:
                raise Exception('Could not open device %s' % device)
            raise e

        self._device = device

        if fcntl:
            try:
                fcntl.flock(self.ser.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except Exception as e:
                raise Exception('Could not lock device %s' % self._device)

    def _close(self):
        if fcntl:
            fcntl.flock(self.ser.fileno(), fcntl.LOCK_UN)
        self.ser.close()

    def run(self):
        self.ser.reset_input_buffer()

        while True:
            try:
                line = self.ser.readline()
            except serial.SerialException as e:
                self._close()
                raise
            except KeyboardInterrupt as e:
                self._close()
                raise

            if not line:
                continue

            try:
                line = line.decode()
            except Exception as e:
                continue

            if line[0] == '#' and line.endswith('\r\n'):
                self.print(line[1:].strip())


def run(args):
    init(autoreset=False)
    try:
        record_file = open(args.record, 'a') if args.record else None

        if args.device:
            SerialPortLog(args.device, args.time, args.no_color, record_file).run()
    except KeyboardInterrupt as e:
        sys.exit(1)
    except Exception as e:
        print(e)
        if os.getenv('DEBUG', False):
            raise e
        sys.exit(1)
