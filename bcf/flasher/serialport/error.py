#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__all__ = ["ErrorOpenDevice", "ErrorLockDevice", "ErrorOpenDevicePermissionDenied"]


class ErrorOpenDevice(Exception):
    pass


class ErrorOpenDevicePermissionDenied(Exception):
    pass


class ErrorLockDevice(Exception):
    pass
