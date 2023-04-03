#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import __future__
from time import sleep
from . import SerialPort

__all__ = ["CoreModuleSerialPort", "LoRaModuleSerialPort"]


class CoreModuleSerialPort(SerialPort):
    def boot_sequence(self):
        self.ser.rts = True
        self.ser.dtr = True
        sleep(0.01)

        self.ser.rts = True
        self.ser.dtr = False
        sleep(0.05)

        self.ser.dtr = True
        self.ser.rts = False
        sleep(0.05)

        self.ser.dtr = False

    def reset_sequence(self, timeout=0.1):
        self.ser.rts = True
        self.ser.dtr = False
        sleep(timeout)
        self.ser.rts = False


class LoRaModuleSerialPort(SerialPort):
    '''Serial port on LoRa Module with boot/reset support

    This class represents the serial port on the Hardwario Tower LoRa Module
    board. Under normal circumstances, this port is connected to the LPUART1
    peripheral in the TypeABZ module. The AT command interface runs over that
    interface.

    For firmware development purposes, I (janakj) have the LoRa Modem connected
    to a standalone USB-UART converter with a FTDI chip inside. To be able to
    reset and switch the STM32 MCU inside the TypeABZ module into the
    bootloader, I connect the RTS signal to the reset pin and the DTR signal to
    the boot pin on the TypeABZ module. The reset pin is active low. The boot
    pin is active high.

    The connection is described in the github.com:hardwario/lora-modem Wiki.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The DTR signal on the USB-UART converter is connected to the TypeABZ's
        # boot pin. The boot pin is active high. We set the DTR signal here to
        # False which will set it low, effectively disabling boot mode when the
        # port has been opened.
        self.ser.dtr = True

        # The RTS signal on the USB-UART converter is connected to the TypeABZ's
        # reset pin. The pin is active low. Thus, we set the RTS signal to False
        # which will set the signal high, disabling reset after the port has
        # been opened.
        self.ser.rts = False

    def boot_sequence(self):
        '''Activate the bootloader in the TypeABZ module.

        The following sequence activates the bootloader in the TypeABZ module
        and resets the module. We first set the DTR signal high (which is
        connected to the boot pin), then reset the modem, and then we set the
        DTR signal (boot pin) low again.
        '''
        self.ser.dtr = False
        sleep(0.01)

        self.ser.rts = True
        sleep(0.05)
        self.ser.rts = False
        sleep(0.05)

        self.ser.dtr = True

    def reset_sequence(self, timeout=0.1):
        '''Reset the module into normal operational mode.

        The following sequence resets the LoRa Module to bring it to the normal
        operational mode. We disable the boot mode (DTR = True) in case boot
        mode was activated. Then we shortly bring the RTS signal low to reset
        the TypeABZ module.
        '''
        self.ser.dtr = True

        self.ser.rts = True
        sleep(timeout)
        self.ser.rts = False
