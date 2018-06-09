#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from . import uart
from . import dfu


def flash(filename_bin, device=None, reporthook=None, run=True, erase_eeprom=False):
    if device == 'dfu':
        dfu.flash(filename_bin, reporthook=reporthook, erase_eeprom=erase_eeprom)
    else:
        uart.flash(device, filename_bin, run=run, reporthook=reporthook, erase_eeprom=erase_eeprom)


def reset(device):
    uart.reset(device)


def eeprom_erase(device, reporthook):
    if device == 'dfu':
        dfu.eeprom_erase(reporthook=reporthook)
    else:
        uart.eeprom_erase(device, reporthook=reporthook, run=True)
