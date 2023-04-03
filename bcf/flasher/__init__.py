#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from . import uart
from . import dfu


def flash(filename, module, device=None, reporthook=None, run=True, erase_eeprom=False, unprotect=False, skip_verify=False, diff=False, baudrate=921600):
    if device == 'dfu':
        if filename.endswith(".hex"):
            raise Exception("DFU not support hex.")
        if unprotect:
            raise Exception("DFU not support Unprotect.")
        dfu.flash(filename, reporthook=reporthook, erase_eeprom=erase_eeprom)
    else:
        uart.flash(module, device, filename, run=run, reporthook=reporthook, erase_eeprom=erase_eeprom, unprotect=unprotect, skip_verify=skip_verify, diff=diff, baudrate=baudrate)


def reset(module, device):
    uart.reset(module, device)


def eeprom_erase(module, device, reporthook):
    if device == 'dfu':
        dfu.eeprom_erase(reporthook=reporthook)
    else:
        uart.eeprom_erase(module, device, reporthook=reporthook, run=True)


def eeprom_read(module, device, filename, address=0, length=6144, reporthook=None):
    if 0 > address or address >= 6144:
        raise Exception('Bad address')

    if 0 >= length or length > 6144:
        raise Exception('Bad length')

    if device == 'dfu':
        dfu.eeprom_read(filename, address, length, reporthook=reporthook)
    else:
        uart.eeprom_read(module, device, filename, address, length, reporthook=reporthook)


def eeprom_write(module, device, filename, address=0, length=6144, reporthook=None):
    if 0 > address or address >= 6144:
        raise Exception('Bad address, max: 6144')

    if 0 >= length or length > 6144:
        raise Exception('Bad length, max: 6144')

    if device == 'dfu':
        raise Exception('Not implemented.')
    else:
        uart.eeprom_write(module, device, filename, address, length, reporthook=reporthook)
