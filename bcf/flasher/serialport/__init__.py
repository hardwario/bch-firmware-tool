#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import __future__
import logging
import platform
import serial
from time import sleep, time
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
            if e.errno == 13:
                raise ErrorOpenDevicePermissionDenied('Could not open device %s Permission denied' % device)
            raise e

        self._device = device

        self._lock()
        self._speed_up()

        self.reset_input_buffer = self.ser.reset_input_buffer
        self.reset_output_buffer = self.ser.reset_output_buffer

        self.write = self.ser.write
        self.read = self.ser.read
        self.flush = self.ser.flush
        self.readline = self.ser.readline

    def close(self):
        if not self.ser:
            return
        self._unlock()
        try:
            self.ser.close()
        except Exception as e:
            pass
        self.ser = None

    def reopen(self):
        self.ser.close()
        self.ser.open()

    def __del__(self):
        self.close()

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
