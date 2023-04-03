#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import __future__
import sys
import logging
import platform
import serial
import serial.tools.list_ports
from time import sleep, time
import math
import array
import intelhex
from ctypes import *
from .serialport import ftdi
try:
    import fcntl
    from .serialport import bridge
except ImportError:
    fcntl = None
    bridge = None

if sys.version_info[0] == 2:
    import struct

LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'

ACK = b'\x79'
NACK = b'\x1F'


class Flash_Serial(object):
    def __init__(self, module, device, baudrate=921600):
        self.ser = None
        self._connect = False
        if bridge and 'hidraw' in device:
            self.ser = bridge.SerialPort(device)
        else:
            if module == 'LoRa':
                self.ser = ftdi.LoRaModuleSerialPort(device, baudrate=baudrate, parity=serial.PARITY_EVEN, timeout=0.1)
            elif module == 'Core':
                self.ser = ftdi.CoreModuleSerialPort(device, baudrate=baudrate, parity=serial.PARITY_EVEN, timeout=0.1)
            else:
                raise Exception(f'Unsupported Hardwario Tower module {module}')

    def connect(self):
        if not self._connect:
            logging.debug('connect')
            for i in range(6):
                self._connect = self.start_bootloader()
                if self._connect:
                    return True
                logging.info('repeate reset')
        return self._connect

    def set_disconnect(self):
        self._connect = False

    def reconnect(self):
        self._connect = False
        return self.connect()

    def start_bootloader(self):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.boot_sequence()
        sleep(0.05)
        self.ser.write([0x7f])
        self.ser.flush()
        if self._wait_for_ack():
            return True

        return False

    def _read_data(self, length, start_ack=True, stop_ack=True):
        if start_ack and not self._wait_for_ack():
            return
        data = b''
        i = 10
        while len(data) < length:
            data += self.ser.read(length - len(data))
            i -= 1
            if i == 0:
                return
        if stop_ack and not self._wait_for_ack():
            return
        return data

    def get_command(self):
        if not self.connect():
            return
        self.ser.write([0x00, 0xff])
        self.ser.flush()
        n, bootloader_version = self._read_data(2, start_ack=True, stop_ack=False)
        if sys.version_info[0] == 2:
            n = ord(n)
            bootloader_version = ord(bootloader_version)
        command = self._read_data(n, start_ack=False, stop_ack=True)
        return n, bootloader_version, command

    def get_version(self):
        if not self.connect():
            return
        self.ser.write([0x01, 0xfe])
        self.ser.flush()
        return self._read_data(3)

    def get_ID(self):
        if not self.connect():
            return
        self.ser.write([0x02, 0xfd])
        self.ser.flush()
        return self._read_data(3)

    def read_memory(self, start_address, length):
        logging.debug('_read_memory %x %i' % (start_address, length))
        if length > 256 or length < 0:
            return

        if not self.connect():
            return

        sa = self._int_to_bytes(start_address)
        xor = self._calculate_xor(sa)
        self.ser.write([0x11, 0xee])
        self.ser.flush()

        # if not self._wait_for_ack():
        #     return

        self.ser.write(sa)
        self.ser.write([xor])
        self.ser.flush()

        # if not self._wait_for_ack():
        #     return

        n = length - 1
        self.ser.write([n, 0xff ^ n])
        self.ser.flush()

        if self.ser.read(3) != b'\x79\x79\x79':
            return

        data = self._read_data(length, start_ack=False, stop_ack=False)

        return data

    def extended_erase_memory(self, pages):
        logging.debug('extended_erase_memory pages=%s' % pages)
        if not pages or len(pages) > 80:
            return

        if not self.connect():
            return

        self.ser.write([0x44, 0xbb])
        self.ser.flush()

        if not self._wait_for_ack():
            return

        data = [0x00, len(pages) - 1]

        for page in pages:
            data.append((page >> 8) & 0xff)
            data.append(page & 0xff)

        data.append(self._calculate_xor(data))

        self.ser.write(data)

        return self._wait_for_ack()

    def write_memory(self, start_address, data):
        logging.debug('_write_memory start_address=%x len(data)=%i' % (start_address, len(data)))

        if len(data) > 256:
            return

        if not self.connect():
            return

        mod = len(data) % 4
        if mod != 0:
            data += bytearray([0] * mod)

        sa = self._int_to_bytes(start_address)
        xor = self._calculate_xor(sa)
        data_xor = self._calculate_xor(data)

        self.ser.write([0x31, 0xce])
        self.ser.write(sa)
        self.ser.write([xor])
        self.ser.flush()

        if self.ser.read(2) != b'\x79\x79':
            return

        length = len(data) - 1
        self.ser.write([length])
        self.ser.write(data)
        self.ser.write([length ^ data_xor])
        self.ser.flush()

        return self._wait_for_ack()

    def go(self, start_address):
        logging.debug('go %x' % start_address)
        if not self.connect():
            return

        self.ser.write([0x21, 0xde])
        self.ser.flush()

        if not self._wait_for_ack():
            return

        sa = self._int_to_bytes(start_address)
        xor = self._calculate_xor(sa)

        self.ser.write(sa)
        self.ser.write([xor])
        self.ser.flush()

        return self._wait_for_ack()

    def write_unprotect(self):
        self.ser.write([0x73, 0x8C])
        self.ser.flush()
        return self._wait_for_ack() and self._wait_for_ack()

    def readout_unprotect(self):
        self.ser.write([0x92, 0x6D])
        self.ser.flush()
        return self._wait_for_ack() and self._wait_for_ack()

    def _calculate_xor(self, data):
        xor = 0
        if isinstance(data, str):
            data = map(ord, data)
        for v in data:
            xor ^= v
        return xor

    def _int_to_bytes(self, value):
        if sys.version_info[0] == 2:
            return struct.pack('>I', value)
        return value.to_bytes(4, 'big', signed=False)

    def _wait_for_ack(self, n=3):
        for i in range(n):
            c = self.ser.read(1)
            if c:
                if c == ACK:
                    return True
                return False
        return False


def _run_connect(api):
    i = 0
    while True:
        try:
            api.set_disconnect()

            if not api.connect():
                raise Exception('Failed to connect')

            if api.get_version() != b'1\x00\x00':
                raise Exception('Bad Verison')

            if api.get_command() != (11, 49, b'\x00\x01\x02\x11!1Dcs\x82\x92'):
                raise Exception('Bad Command')

            if api.get_ID() != b'\x01\x04G':
                raise Exception('Bad ID')

            return True

        except Exception as e:
            if i > 2:
                raise Exception('Cannot switch Core Module to bootloader, please check that the port is correct and it is not blocked by other application.')
            i += 1


def _try_run(api, ntry, fce, *params):
    for i in range(ntry):
        response = fce(*params)
        if response:
            return response
        if i % 2 == 1:
            _run_connect(api)
    else:
        return False


def erase(module, device, length=196608, reporthook=None, api=None, label='Erase '):
    if api is None:
        api = Flash_Serial(module, device)
        _run_connect(api)

    pages = int(math.ceil(length / 128)) + 1
    if pages > 1536:
        pages = 1536

    if reporthook:
        reporthook(label, 0, pages)

    for page_start in range(0, pages, 80):
        page_stop = page_start + 80
        if page_stop > pages:
            page_stop = pages

        if _try_run(api, 6, api.extended_erase_memory, range(page_start, page_stop)):
            if reporthook:
                reporthook(label, page_stop, pages)
        else:
            raise Exception(label + ' Error')


def write(module, device, firmware, reporthook=None, api=None, start_address=0x08000000, label='Write '):
    if api is None:
        api = Flash_Serial(module, device)
        _run_connect(api)

    length = len(firmware)

    if reporthook:
        reporthook(label, 0, length)

    step = 128
    for offset in range(0, length, step):
        write_len = length - offset
        if write_len > step:
            write_len = step

        if _try_run(api, 6, api.write_memory, start_address + offset, firmware[offset:offset + write_len]):
            if reporthook:
                reporthook(label, offset + write_len, length)
        else:
            raise Exception(label + ' Error')


def verify(module, device, firmware, reporthook=None, api=None, start_address=0x08000000, label='Verify'):
    if api is None:
        api = Flash_Serial(module, device)
        _run_connect(api)

    length = len(firmware)

    step = 128
    for offset in range(0, length, step):
        read_len = length - offset
        if read_len > step:
            read_len = step

        for i in range(2):
            data = _try_run(api, 6, api.read_memory, start_address + offset, read_len)
            if data and data == firmware[offset:offset + read_len]:
                break
        else:
            raise Exception(label + ' Error')

        if reporthook:
            reporthook(label, offset + read_len, length)


def clone(module, device, filename, length, reporthook=None, api=None, start_address=0x08000000, label='Clone'):
    if api is None:
        api = Flash_Serial(module, device)
        _run_connect(api)

    f = open(filename, 'wb')
    step = 128
    for offset in range(0, length, step):
        read_len = length - offset
        if read_len > step:
            read_len = step

        for i in range(2):
            data = _try_run(api, 6, api.read_memory, start_address + offset, read_len)
            verify = _try_run(api, 6, api.read_memory, start_address + offset, read_len)
            if data == verify:
                f.write(data)
                break
        else:
            raise Exception(label + ' Error')

        if reporthook:
            reporthook(label, offset + read_len, length)

    f.close()


def _unprotect(module, device, api=None):
    if api is None:
        api = Flash_Serial(module, device)
        _run_connect(api)

    if not api.readout_unprotect():
        raise Exception('Did not succeed Readout unprotect.')
    print('Unprotect Read  OK')
    api.ser.reopen()
    api.reconnect()

    if not api.write_unprotect():
        raise Exception('Did not succeed Write unprotect.')
    print('Unprotect Write OK')
    api.ser.reopen()
    api.reconnect()


def _flash_bin_diff(device, filename, reporthook, api, start_address=0x08000000):
    firmware = open(filename, 'rb').read()

    length = len(firmware)

    page_size = 128

    pages = int(math.ceil(length / page_size))
    if pages > 1536:
        pages = 1536

    offset = 0

    diff_pages = []

    for page in range(0, pages):
        read_len = length - offset
        if read_len > page_size:
            read_len = page_size

        data = _try_run(api, 6, api.read_memory, start_address + offset, read_len)

        if data != firmware[offset:offset + read_len]:
            diff_pages.append(page)

        if reporthook:
            reporthook('Compare', page + 1, pages)

        offset += page_size

    if diff_pages:
        print('Diff pages', len(diff_pages), 'of', pages)
        for i in range(0, len(diff_pages), 80):
            if _try_run(api, 6, api.extended_erase_memory, diff_pages[i:i + 80]):
                if reporthook:
                    reporthook('Erase diff pages', i + 80, len(diff_pages))
            else:
                raise Exception('Errase error')

        for i, page in enumerate(diff_pages):
            offset = page * page_size
            data = firmware[offset:offset + page_size]
            if data:
                if _try_run(api, 6, api.write_memory, start_address + offset, data):
                    if reporthook:
                        reporthook('Write diff pages', i + 1, len(diff_pages))
                else:
                    raise Exception('Write error')


def _flash_bin(module, device, filename, reporthook, api, skip_verify):
    firmware = open(filename, 'rb').read()

    erase(module, device, length=len(firmware), reporthook=reporthook, api=api)

    write(module, device, firmware, reporthook=reporthook, api=api)

    if skip_verify:
        return

    verify(module, device, firmware, reporthook=reporthook, api=api)


def _flash_hex(module, device, filename, reporthook, api, skip_verify):
    ih = intelhex.IntelHex(filename)

    flash_address_start = 0x08000000
    flash_address_end = 0x0802FFFF
    eeprom_address_start = 0x08080000
    eeprom_address_end = 0x080817FF

    length = 0
    pages = 0

    segments = ih.segments()
    for s in segments:
        slength = s[1] - s[0]
        if flash_address_start <= s[0] <= flash_address_end:
            length += slength
            pages += int(math.ceil(slength / 128)) + 1
        elif eeprom_address_start <= s[0] <= eeprom_address_end:
            length += slength
        else:
            raise Exception("Unknown memory address %d", s[0])

    if pages > 0:
        if reporthook:
            reporthook('Erase ', 0, pages)

        done = 0

        for s in segments:
            if flash_address_start <= s[0] <= flash_address_end:
                page_start = int(math.floor((s[0] - flash_address_start) / 128))
                s_pages = int(math.ceil((s[1] - s[0]) / 128)) + 1

                for page_start in range(0, s_pages, 80):
                    page_stop = page_start + 80
                    if page_stop > s_pages:
                        page_stop = s_pages

                    if _try_run(api, 6, api.extended_erase_memory, range(page_start, page_stop)):
                        if reporthook:
                            reporthook('Erase ', done + page_stop, pages)
                    else:
                        raise Exception('Errase Error')

                done += s_pages

    if reporthook:
        reporthook('Write ', 0, length)

    done = 0

    for s in segments:
        sih = ih[s[0]:s[1]]
        for address_start in range(s[0], s[1], 128):
            address_stop = address_start + 128
            if address_stop > s[1]:
                address_stop = s[1]

            data = sih[address_start:address_stop].tobinstr()

            if _try_run(api, 6, api.write_memory, address_start, data):
                if reporthook:
                    done += address_stop - address_start
                    reporthook('Write ', done, length)
            else:
                raise Exception('Write Error')

    if skip_verify:
        return

    if reporthook:
        reporthook('Verify', 0, length)

    done = 0

    for s in segments:
        sih = ih[s[0]:s[1]]
        for address_start in range(s[0], s[1], 128):
            address_stop = address_start + 128
            if address_stop > s[1]:
                address_stop = s[1]

            data = sih[address_start:address_stop].tobinstr()

            for i in range(2):
                vdata = _try_run(api, 6, api.read_memory, address_start, len(data))
                if vdata == data:
                    if reporthook:
                        done += address_stop - address_start
                        reporthook('Verify', done, length)
                    break
            else:
                raise Exception('Verify Error')


def flash(module, device, filename, run=True, reporthook=None, erase_eeprom=False, unprotect=False, skip_verify=False, diff=False, baudrate=921600):
    api = Flash_Serial(module, device, baudrate)

    _run_connect(api)

    if unprotect:
        _unprotect(module, device, api)

    if erase_eeprom:
        eeprom_erase(module, device, reporthook=reporthook, run=False, api=api)

    if filename.endswith(".hex"):
        if diff:
            raise Exception('Diff is not implemented')
        else:
            _flash_hex(module, device, filename, reporthook, api, skip_verify)
    else:
        if diff:
            _flash_bin_diff(module, device, filename, reporthook, api)
        else:
            _flash_bin(module, device, filename, reporthook, api, skip_verify)

    if run:
        api.go(0x08000000)


def reset(module, device, baudrate=921600):
    api = Flash_Serial(module, device, baudrate)
    api.ser.reset_sequence()


def get_list_devices():
    table = []
    for p in serial.tools.list_ports.comports():
        table.append(p.device)
    if bridge:
        for b in bridge.get_list():
            table.append(b[1])
    return table


def eeprom_read(module, device, filename, address=0, length=6144, reporthook=None, run=True, api=None, baudrate=921600, label='Read EEPROM'):
    if length > 6144:
        raise Exception('Max length is 6144B.')

    if api is None:
        api = Flash_Serial(module, device, baudrate)
        _run_connect(api)

    start_address = 0x08080000 + address

    if reporthook:
        reporthook(label, 0, length)

    f = open(filename, 'wb')
    step = 128
    for offset in range(0, length, step):
        read_len = length - offset
        if read_len > step:
            read_len = step

        for i in range(2):
            data = _try_run(api, 6, api.read_memory, start_address + offset, read_len)
            verify = _try_run(api, 6, api.read_memory, start_address + offset, read_len)
            if data == verify:
                f.write(data)
                break
        else:
            raise Exception(label + ' Error')

        if reporthook:
            reporthook(label, offset + read_len, length)

    f.close()

    if run:
        api.go(0x08000000)


def eeprom_write(module, device, filename, address=0, length=6144, reporthook=None, run=True, api=None, baudrate=921600, label='Write EEPROM'):
    if length > 6144:
        raise Exception('Max length is 6144.')

    if api is None:
        api = Flash_Serial(module, device, baudrate)
        _run_connect(api)

    with open(filename, 'rb') as f:
        data = f.read(length)

    start_address = 0x08080000 + address

    if reporthook:
        reporthook(label, 0, length)

    step = 128
    for offset in range(0, length, step):
        write_len = length - offset
        if write_len > step:
            write_len = step

        if _try_run(api, 6, api.write_memory, start_address + offset, data[offset:offset + write_len]):
            if reporthook:
                reporthook(label, offset + write_len, length)
        else:
            raise Exception(label + ' Error')

    if run:
        api.go(0x08000000)


def eeprom_erase(module, device, reporthook=None, run=True, api=None, baudrate=921600, label='Erase EEPROM'):
    if api is None:
        api = Flash_Serial(module, device, baudrate)
        _run_connect(api)

    length = 6144

    start_address = 0x08080000

    if reporthook:
        reporthook(label, 0, length)

    step = 128
    data = bytearray([0xff] * 128)
    for offset in range(0, length, step):
        write_len = length - offset
        if write_len > step:
            write_len = step

        if _try_run(api, 6, api.write_memory, start_address + offset, data):
            if reporthook:
                reporthook(label, offset + write_len, length)
        else:
            raise Exception(label + ' Error')

    if run:
        api.go(0x08000000)
