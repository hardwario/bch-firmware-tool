#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from . import uart
from . import dfu


def flash(filename, device=None, reporthook=None, run=True, erase_eeprom=False, unprotect=False, skip_verify=False, diff=False, baudrate=921600):
    if device == 'dfu':
        if filename.endswith(".hex"):
            raise Exception("DFU not support hex.")
        if unprotect:
            raise Exception("DFU not support Unprotect.")
        dfu.flash(filename, reporthook=reporthook, erase_eeprom=erase_eeprom)
    else:
        uart.flash(device, filename, run=run, reporthook=reporthook, erase_eeprom=erase_eeprom, unprotect=unprotect, skip_verify=skip_verify, diff=diff, baudrate=baudrate)


def reset(device):
    uart.reset(device)


def eeprom_erase(device, reporthook):
    if device == 'dfu':
        dfu.eeprom_erase(reporthook=reporthook)
    else:
        uart.eeprom_erase(device, reporthook=reporthook, run=True)
