import re
import sys
import click
from pyftdi.ftdi import Ftdi
from pyftdi.eeprom import FtdiEeprom


def load_eeprom(vid, pid, sn):
    ftdi = Ftdi()
    eeprom = FtdiEeprom()
    ftdi.open(vid, pid, serial=sn)
    eeprom.connect(ftdi)
    return eeprom


def scan_devices(sn):
    ftdi = Ftdi()
    devices = [d[0] for d in ftdi.list_devices()]

    # Keep only devices with a serial number
    devices = [d for d in devices if len(d.sn.strip()) and d.sn != '""']

    # If the caller gave us a serial or a regex, keep only matching devices
    if sn:
        devices = [d for d in devices if re.search(sn, d.sn)]

    # Sorty devices by their serials so that the presentation order does not
    # depend on the order in which the devices were connected or reset.
    devices = sorted(devices, key=lambda d: d.sn)

    # Construct the FtdiEeprom object for each matching device
    devices = [load_eeprom(d.vid, d.pid, d.sn) for d in devices]

    return devices


def print_devices(devices):
    for i, device in enumerate(devices):
        serial = device.serial.strip()

        product = device.product.strip()
        if product == '""':
            product = None

        manufacturer = device.manufacturer.strip()
        if manufacturer == '""':
            manufacturer = None

        s = "%i: serial: %s" % (i, serial)
        if product:
            s += ", product: %s" % product

        if manufacturer:
            s += ", manufacturer: %s" % manufacturer

        click.echo(s)


def select_device(sn):
    devices = scan_devices(sn)

    # We found no device we could work with, bail.
    if len(devices) == 0:
        raise Exception("No compatible/matching FTDI devices found")

    # No need to ask the user to confirm the selection if we only have one device left.
    if len(devices) == 1:
        return devices[0]

    print_devices(devices)

    d = int(click.prompt('Please choose device (line number)'))
    return devices[d]


def update_eeprom(sn, manufacturer=None, product=None, serial=None, reset=False):
    eeprom = select_device(sn)
    updated = False

    if manufacturer is not None and manufacturer != eeprom.manufacturer:
        eeprom.set_manufacturer_name(manufacturer)
        updated = True

    if product is not None and product != eeprom.product:
        eeprom.set_product_name(product)
        updated = True

    if serial is not None and serial != eeprom.serial:
        eeprom.set_serial_number(serial)
        updated = True

    if updated:
        eeprom.commit(dry_run=False)
        click.echo("The FTDI device EEPROM was updated.")

    # On Darwin (Mac OS) we need to reset the USB device if the EEPROM was
    # updated in order for the USB host to pick up the new USB descriptors.

    if reset or (updated and sys.platform == 'darwin'):
        click.echo("Resetting the USB device.")
        eeprom.reset_device()

    # On Linux, modifying the EEPROM or resetting the USB device will cause the
    # kernel to unbind the ftdio_sio driver from the device. Thus, the character
    # device ttyUSBx will not be available. To remedy this situation, one needs
    # to either unplug and replug the device or write to
    # /sys/bus/usb/drivers/ftdi_sio/bind to manually rebind the driver to the
    # USB device.
    if (reset or updated) and sys.platform == 'linux':
        click.echo("You may need to disconnect and reconnect the device.")


def list_devices(sn):
    devices = scan_devices(sn)

    if len(devices) == 0:
        click.echo("No compatible/matching FTDI devices found.")
    else:
        print_devices(devices)
