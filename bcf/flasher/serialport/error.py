#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__all__ = ["ErrorOpenDevice", "ErrorLockDevice"]


class ErrorOpenDevice(Exception):
    pass


class ErrorLockDevice(Exception):
    pass
