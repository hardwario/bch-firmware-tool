#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import serial
from datetime import datetime
from time import sleep
import click
from colorama import init, Fore, Style
from ..flasher.serialport.ftdi import SerialPort


BAUDRATE = 115200
log_level_color_lut = {'X': Fore.BLUE, 'D': Fore.MAGENTA, 'I': Fore.GREEN, 'W': Fore.YELLOW, 'E': Fore.RED}


def test(ctx, param, value):
    if value and '--log' not in sys.argv:
        ctx.fail('-log is required when use --time or --no-color or --raw or --record.')
    return value


def click_options(f):
    f = click.option('--time', is_flag=True, help='Show time.', callback=test)(f)
    f = click.option('--no-color', is_flag=True, help='Disable color.', callback=test)(f)
    f = click.option('--raw', is_flag=True, help='Print raw .', callback=test)(f)
    return click.option('--record', help='Record to file.', callback=test)(f)


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
        if line[0] == '#' and line.endswith('\r\n'):
            line = line[1:].strip()

            index = line.find("<")

            if index < 0:
                return

            time = self.get_time_str()

            if self._record_file:
                self._record_file.write(time + line + os.linesep)
                self._record_file.flush()

            if self._no_color:
                click.echo(time + line)
            else:
                if index < 0:
                    click.echo(time + line)

                else:
                    color = ""
                    try:
                        level_char = line[index + 1]
                        color = log_level_color_lut[level_char]
                    except Exception as e:
                        pass

                    click.echo(color + time + line[:index + 3] + Style.RESET_ALL + line[index + 3:])

        elif self._raw:
            time = self.get_time_str()

            if self._record_file:
                self._record_file.write(time + line)
                self._record_file.flush()

            click.echo(time + line.rstrip())


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

            self.print(line)


def run(device, show_time=True, no_color=False, raw=False, record_file=None, reset=False):
    init(autoreset=False)
    log = SerialPortLog(device, show_time, no_color, raw, record_file)
    if reset:
        log.reset_sequence()
    log.run()


def run_args(device, args, reset=False):
    try:
        record_file = open(args['record'], 'a') if args['record'] else None

        if device:
            run(device, args['time'], args['no_color'], args['raw'], record_file, reset)

    except KeyboardInterrupt as e:
        sys.exit(1)
