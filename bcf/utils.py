#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import serial
import click
import requests
import hashlib
import appdirs
import re
try:
    from packaging.version import parse as parse_version
except ImportError:
    from distutils.version import LooseVersion as parse_version

from bcf.firmware.FirmwareList import FirmwareList

user_cache_dir = appdirs.user_cache_dir('bcf')
user_config_dir = appdirs.user_config_dir('bcf')

pyserial_34 = parse_version(serial.VERSION) >= parse_version("3.4.0")


def get_fwlist():
    return FirmwareList(user_cache_dir, user_config_dir)


def get_devices(include_links=False):
    if os.name == 'nt' or sys.platform == 'win32':
        from serial.tools.list_ports_windows import comports
    elif os.name == 'posix':
        from serial.tools.list_ports_posix import comports

    if pyserial_34:
        ports = comports(include_links=include_links)
    else:
        ports = comports()

    return sorted(ports)


def select_device(device):
    if device is not None:
        return device

    ports = get_devices()
    if not ports:
        raise Exception("No device")

    # Search for devices with a serial string that starts with "bc-" or "hio-".
    # If exactly once such device is found, select it automatically. This should
    # hopefully simplify the common case where a developer has only one BigClown
    # device connected to the host. Not having to specify the character device
    # in this case works well with systems where the pathname of the character
    # device is dynamic.
    bc_ports = [port for port in ports if re.search(r"SER=(bc|hio)-", port[2])]

    if len(bc_ports) == 1:
        return bc_ports[0][0]
    else:
        for i, port in enumerate(ports):
            sn = ""
            g = re.search(r"SER=([^\s]*)", port[2])
            if g:
                sn = g.group(1)
            click.echo("%i: %s %s" % (i, port[0], sn), err=True)
        d = click.prompt('Please choose device (line number)')

    for port in ports:
        if port[0] == d:
            device = port[0]
            break
    else:
        try:
            device = ports[int(d)][0]
        except Exception as e:
            raise Exception("Unknown device")

    return device


def download_url_reporthook(count, blockSize, totalSize):
    print_progress_bar('Download', count * blockSize, totalSize)


def download_url(url, use_cache=True):
    if url.startswith("https://github.com/bigclownlabs/bcf-"):
        filename = url.rsplit('/', 1)[1]
    else:
        filename = hashlib.sha256(url.encode()).hexdigest()
    filename_bin = os.path.join(user_cache_dir, filename)

    if use_cache and os.path.exists(filename_bin):
        return filename_bin

    click.echo('Download firmware from ' + url)
    click.echo('Save as' + filename_bin)

    try:
        response = requests.get(url, stream=True, allow_redirects=True)
        total_length = response.headers.get('content-length')
        with open(filename_bin, "wb") as f:
            if total_length is None:  # no content length header
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    download_url_reporthook(1, dl, total_length)
    except Exception as e:
        click.echo("Firmware download problem: " + str(e.args[0]))
        sys.exit(1)
    return filename_bin


def print_table(labels, rows):
    if not labels and not rows:
        return

    max_lengths = [0] * (len(rows[0]) if rows else len(labels))
    for i, label in enumerate(labels):
        max_lengths[i] = len(label)

    for row in rows:
        for i, v in enumerate(row):
            if len(v) > max_lengths[i]:
                max_lengths[i] = len(v)

    row_format = "{:<" + "}  {:<".join(map(str, max_lengths)) + "}"

    if labels:
        click.echo(row_format.format(*labels))
        click.echo("=" * (sum(max_lengths) + len(labels) * 2))

    for row in rows:
        click.echo(row_format.format(*row))


def print_progress_bar(title, progress, total, length=20):
    if progress > total:
        progress = total
    filled_length = int(length * progress // total)
    if filled_length < 0:
        filled_length = 0
    bar = '#' * filled_length
    bar += '-' * (length - filled_length)
    percent = 100 * (progress / float(total))
    if percent > 100:
        percent = 100
    elif percent < 0:
        percent = 0
    sys.stdout.write('\r\r')
    sys.stdout.write(title + ' [' + bar + '] ' + "{:5.1f}%".format(percent))
    sys.stdout.flush()
    if percent == 100:
        sys.stdout.write('\n')
        sys.stdout.flush()
