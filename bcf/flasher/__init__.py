#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from . import uart
from . import dfu


def flash(filename_bin, device=None, reporthook=None, use_dfu=False, run=True):
    if use_dfu:
        dfu.flash(filename_bin, reporthook=reporthook)
    else:
        uart.flash(device, filename_bin, run=run, reporthook=reporthook)


def reset(device):
    uart.reset(device)
