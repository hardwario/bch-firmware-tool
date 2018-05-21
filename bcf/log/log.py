#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import sys
import os
import serial
from datetime import datetime
from time import sleep
from colorama import init, Fore, Style
from ..flasher.serialport.ftdi import SerialPort

BAUDRATE = 115200
log_level_color_lut = {'D': Fore.MAGENTA, 'I': Fore.GREEN, 'W': Fore.YELLOW, 'E': Fore.RED}


def add_arguments(action):
    action.add_argument('--time', help='show time', action='store_true')
    action.add_argument('--no-color', help='disable color', action='store_true')
    action.add_argument('--raw', help='', action='store_true')
    action.add_argument('--record', nargs='?', help="record to file", metavar='FILE')
    return action


class Log(object):
    def __init__(self, show_time, no_color, record_file, raw):
        self._show_time = show_time
        self._no_color = no_color
        self._record_file = record_file
        self._raw = raw

    def get_time_str(self):
        if self._show_time:
            dt = datetime.now()
            ms = round(dt.microsecond / 10000)
            if ms > 99:
                ms = 99
            return dt.strftime('%Y-%m-%d %H:%M:%S.') + "%02i " % ms
        else:
            return ""

    def print(self, line):
        index = line.find("<")
        if index < 0 and not self._raw:
            return

        time = self.get_time_str()

        if self._record_file:
            self._record_file.write(time + line + os.linesep)
            self._record_file.flush()

        if self._no_color:
            print(time + line)
        else:
            if index < 0:
                print(time + line)

            else:
                level_char = line[index + 1]

                print(log_level_color_lut[level_char] + time + line[:index + 3] + Style.RESET_ALL + line[index + 3:])


class SerialPortLog(Log):
    def __init__(self, device, show_time, no_color, raw, record_file):
        Log.__init__(self, show_time, no_color, record_file, raw)
        if isinstance(device, SerialPort):
            self.ser = device
        else:
            self.ser = SerialPort(device, baudrate=BAUDRATE)

    def reset_sequence(self):
        self.ser.reset_sequence()

    def run(self):
        self.ser.reset_input_buffer()

        while True:
            line = self.ser.readline()

            if not line:
                continue

            try:
                line = line.decode()
            except Exception as e:
                continue

            if line[0] == '#' and line.endswith('\r\n'):
                self.print(line[1:].strip())
            else:
                self.print(line.rstrip())


def run(device, show_time=True, no_color=False, raw=False, record_file=None, reset=False):
    init(autoreset=False)
    log = SerialPortLog(device, show_time, no_color, raw, record_file)
    if reset:
        log.reset_sequence()
    log.run()


def run_args(args, reset=False):

    try:
        record_file = open(args.record, 'a') if args.record else None

        if args.device:
            run(args.device, args.time, args.no_color, args.raw, record_file, reset)

    except KeyboardInterrupt as e:
        sys.exit(1)
    except Exception as e:
        print(e)
        if os.getenv('DEBUG', False):
            raise e
        sys.exit(1)
