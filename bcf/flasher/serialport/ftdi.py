#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import __future__
import sys
import logging
import platform
import serial
from time import sleep, time
import math
import array
from ctypes import *
from .error import *
try:
    import fcntl
except ImportError:
    fcntl = None

__all__ = ["SerialPort"]


class SerialPort:
    def __init__(self, device, baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=3):
        self.ser = None
        try:
            self.ser = serial.Serial(device,
                                     baudrate=baudrate,
                                     bytesize=bytesize,
                                     parity=parity,
                                     stopbits=stopbits,
                                     timeout=timeout,
                                     xonxoff=False,
                                     rtscts=False,
                                     dsrdtr=False)
        except serial.serialutil.SerialException as e:
            if e.errno == 2:
                raise ErrorOpenDevice('Could not open device %s' % device)
            raise e

        self._device = device

        self._connect = False

        self._lock()
        self._speed_up()

        self.reset_input_buffer = self.ser.reset_input_buffer
        self.reset_output_buffer = self.ser.reset_output_buffer

        self.write = self.ser.write
        self.read = self.ser.read
        self.flush = self.ser.flush
        self.readline = self.ser.readline

    def __del__(self):
        self._unlock()

    def _lock(self):
        if not fcntl or not self.ser:
            return
        try:
            fcntl.flock(self.ser.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception as e:
            raise ErrorLockDevice('Could not lock device %s' % self._device)

        logging.debug('_lock')

    def _unlock(self):
        if not fcntl or not self.ser:
            return
        fcntl.flock(self.ser.fileno(), fcntl.LOCK_UN)
        logging.debug('_unlock')

    def _speed_up(self):
        if not fcntl:
            return
        if platform.system() != 'Linux':
            return

        logging.debug('_speed_up')

        TIOCGSERIAL = 0x0000541E
        TIOCSSERIAL = 0x0000541F
        ASYNC_LOW_LATENCY = 0x2000

        class serial_struct(Structure):
            _fields_ = [("type", c_int),
                        ("line", c_int),
                        ("port", c_uint),
                        ("irq", c_int),
                        ("flags", c_int),
                        ("xmit_fifo_size", c_int),
                        ("custom_divisor", c_int),
                        ("baud_base", c_int),
                        ("close_delay", c_ushort),
                        ("io_type", c_byte),
                        ("reserved_char", c_byte * 1),
                        ("hub6", c_uint),
                        ("closing_wait", c_ushort),
                        ("closing_wait2", c_ushort),
                        ("iomem_base", POINTER(c_ubyte)),
                        ("iomem_reg_shift", c_ushort),
                        ("port_high", c_int),
                        ("iomap_base", c_ulong)]

        buf = serial_struct()

        try:
            fcntl.ioctl(self.ser.fileno(), TIOCGSERIAL, buf)
            buf.flags |= ASYNC_LOW_LATENCY
            fcntl.ioctl(self.ser.fileno(), TIOCSSERIAL, buf)
        except Exception as e:
            logging.exception(e)

    def boot_sequence(self):
        self.ser.rts = True
        self.ser.dtr = True
        sleep(0.1)

        self.ser.rts = True
        self.ser.dtr = False
        sleep(0.1)

        self.ser.dtr = True
        self.ser.rts = False
        sleep(0.1)

        self.ser.dtr = False

    def reset_sequence(self):
        self.ser.rts = True
        self.ser.dtr = False
        sleep(0.1)
        self.ser.rts = False
