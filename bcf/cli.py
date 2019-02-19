#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import click
import os
import sys
import glob
import tempfile
import zipfile
import shutil
import subprocess
import serial
import platform
from bcf.firmware.FirmwareList import FirmwareList
from bcf import flasher
from bcf.log import log as bcflog
from bcf.utils import *

__version__ = '@@VERSION@@'
SKELETON_URL_ZIP = 'https://codeload.github.com/bigclownlabs/bcf-skeleton/zip/master'
SDK_URL_ZIP = 'https://codeload.github.com/bigclownlabs/bcf-sdk/zip/master'
SDK_GIT = 'https://github.com/bigclownlabs/bcf-sdk.git'
VSCODE_GIT = 'https://github.com/bigclownlabs/bcf-vscode.git'
VSCODE_URL_ZIP = 'https://codeload.github.com/bigclownlabs/bcf-vscode/zip/master'


@click.group()
@click.option('--device', '-d', type=str, help='Device path.')
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, device=None):
    '''BigClown Firmware Tool.'''
    ctx.obj['device'] = device
    if not os.path.exists(user_cache_dir):
        os.makedirs(user_cache_dir)


@cli.command('clean')
def command_clean():
    '''Clean cache.'''
    fwlist = FirmwareList(user_cache_dir)
    fwlist.clear()
    for filename in os.listdir(user_cache_dir):
        os.unlink(os.path.join(user_cache_dir, filename))


@cli.command('create')
@click.argument('name')
@click.option('--no-git', is_flag=True, help='Disable git.')
def command_create(name, no_git=False):
    '''Create new firmware.'''
    if os.path.exists(name):
        print('Directory already exists')
        sys.exit(1)

    skeleton_zip_filename = download_url(SKELETON_URL_ZIP, use_cache=False)
    click.echo()

    tmp_dir = tempfile.mkdtemp()

    zip_ref = zipfile.ZipFile(skeleton_zip_filename, 'r')
    zip_ref.extractall(tmp_dir)
    zip_ref.close()

    skeleton_path = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
    shutil.move(skeleton_path, name)

    os.rmdir(os.path.join(name, 'sdk'))
    os.rmdir(os.path.join(name, '.vscode'))
    os.unlink(os.path.join(name, '.gitmodules'))

    os.chdir(name)

    if no_git:
        sdk_zip_filename = download_url(SDK_URL_ZIP, use_cache=False)
        zip_ref = zipfile.ZipFile(sdk_zip_filename, 'r')
        zip_ref.extractall(tmp_dir)
        zip_ref.close()
        sdk_path = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
        shutil.move(sdk_path, 'sdk')

        sdk_zip_filename = download_url(VSCODE_URL_ZIP, use_cache=False)
        zip_ref = zipfile.ZipFile(sdk_zip_filename, 'r')
        zip_ref.extractall(tmp_dir)
        zip_ref.close()
        sdk_path = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
        shutil.move(sdk_path, '.vscode')

    else:
        os.system('git init')
        os.system('git submodule add --depth 1 "' + SDK_GIT + '" sdk')
        os.system('git submodule add --depth 1 "' + VSCODE_GIT + '" .vscode')

    os.rmdir(tmp_dir)


@cli.command('devices')
@click.option('-v', '--verbose', is_flag=True, help='Show more messages.')
@click.option('-s', '--include-links', is_flag=True, help='Include entries that are symlinks to real devices.')
def command_devices(verbose=False, include_links=False):
    '''Print available devices.'''
    for port, desc, hwid in get_devices(include_links):
        sys.stdout.write("{:20}\n".format(port))
        if verbose:
            sys.stdout.write("    desc: {}\n".format(desc))
            sys.stdout.write("    hwid: {}\n".format(hwid))


@cli.command('eeprom')
@click.option('-d', '--device', type=str, help='Device path.')
@click.option('--erase', is_flag=True, help='Erase eeprom memory.')
@click.option('--dfu', is_flag=True, help='Use dfu mode.')
@click.pass_context
def command_eeprom(ctx, device, erase=False, dfu=False):
    '''Work with EEPROM.'''
    if device is None:
        device = ctx.obj['device']

    device = select_device('dfu' if dfu else device)
    if erase:
        flasher.eeprom_erase(device, reporthook=print_progress_bar)


@cli.command('flash')
@click.argument('what', metavar="<firmware from list|file|url|firmware.bin>", default="firmware.bin")
@click.option('-d', '--device', type=str, help='Device path.')
@click.option('--log', is_flag=True, help='Show all releases.')
@click.option('--dfu', is_flag=True, help='Use dfu mode.')
@click.option('--erase-eeprom', is_flag=True, help='Erase eeprom.')
@click.option('--unprotect', is_flag=True, help='Unprotect.')
@bcflog.click_options
@click.pass_context
def command_flash(ctx, what, device=None, log=False, dfu=False, erase_eeprom=False, unprotect=False, **args):
    '''Flash firmware.'''
    if device is None:
        device = ctx.obj['device']

    if log and (dfu or device) == 'dfu':
        raise Exception("Sorry, Core Module r1.3 doesn't support log functionality.")

    if what.startswith('http'):
        filename = download_url(what)

    elif os.path.exists(what) and os.path.isfile(what):
        filename = what

    else:
        fwlist = FirmwareList(user_cache_dir)
        firmware = fwlist.get_firmware(what)
        if not firmware:
            print('Firmware not found, try updating first, command: bcf update')
            sys.exit(1)
        filename = download_url(firmware['url'])

    try:
        device = select_device('dfu' if dfu else device)

        flasher.flash(filename, device, reporthook=print_progress_bar, run=not log, erase_eeprom=erase_eeprom, unprotect=unprotect)
        if log:
            bcflog.run_args(device, args, reset=True)

    except flasher.serialport.error.ErrorLockDevice as e:
        click.echo(e)
        click.echo("TIP: Maybe the bcg service is running - you need to stop it first.")
        if os.path.exists("/etc/init.d/bcg-ud"):
            click.echo("Try this command:")
            click.echo("/etc/init.d/bcg-ud stop")
        else:
            try:
                process = subprocess.Popen(['pm2', '-m', 'list'], stdout=subprocess.PIPE)
                out, err = process.communicate()
                for line in out.splitlines():
                    if line.startswith(b"+---"):
                        name = line[5:].decode()
                        if 'bcg' in name and name != 'bcg-cm':
                            click.echo("Try this command:")
                            click.echo("pm2 stop %s" % name)
            except Exception as e:
                pass

    except flasher.serialport.error.ErrorOpenDevicePermissionDenied as e:
        click.echo(e)
        if platform.system() == 'Linux':
            groups = subprocess.check_output('groups').decode().strip().split()
            if 'dialout' not in groups:
                click.echo("TIP: Try add permissions on serial port")
                click.echo("Try this command and logout and login back:")
                click.echo("sudo usermod -a -G dialout $USER")


@cli.command('help')
@click.argument('command', required=False)
@click.pass_context
def command_help(ctx, command):
    '''Show help.'''
    cmd = cli.get_command(ctx, command)

    if cmd is None:
        cmd = cli

    click.echo(cmd.get_help(ctx))


@cli.command('list')
@click.option('--all', is_flag=True, help='Show all releases.')
@click.option('--description', is_flag=True, help='Show description.')
@click.option('--show-pre-release', is_flag=True, help='Show pre-release version.')
def command_list(all=False, description=False, show_pre_release=False):
    '''List firmware.'''
    fwlist = FirmwareList(user_cache_dir)
    rows = fwlist.get_firmware_table(all=all, description=description, show_pre_release=show_pre_release)
    if rows:
        print_table([], rows)
    else:
        click.echo('Empty list, try: bcf update')


@cli.command('log')
@click.option('-d', '--device', type=str, help='Device path.')
@bcflog.click_options
@click.pass_context
def command_log(ctx, device=None, log=False, **args):
    '''Show log.'''
    if device is None:
        device = ctx.obj['device']
    if device == 'dfu':
        raise Exception("Sorry, Core Module r1.3 doesn't support log functionality.")

    device = select_device(device)
    bcflog.run_args(device, args, reset=False)


@cli.command('pull')
@click.argument('what', metavar="<firmware from list|url>")
def command_pull(what):
    '''Pull firmware to cache.'''
    if what.startswith('http'):
        download_url(what, True)
    else:

        fwlist = FirmwareList(user_cache_dir)

        if what in ('last', 'latest'):
            for name in fwlist.get_firmware_list():
                firmware = fwlist.get_firmware(name)
                click.echo('pull ' + name)
                download_url(firmware['url'], True)
                click.echo('')
        else:
            firmware = fwlist.get_firmware(what)
            if not firmware:
                print('Firmware not found, try updating first, command: bcf update')
                sys.exit(1)
            download_url(firmware['url'])


@cli.command('read')
@click.argument('filename')
@click.option('-d', '--device', type=str, help='Device path.')
@click.option('--dfu', is_flag=True, help='Use dfu mode.')
@click.option('--length', help='length.', default=196608, type=int)
@click.pass_context
def command_read(ctx, filename, length, device=None, dfu=False):
    '''Download firmware to file.'''
    if device is None:
        device = ctx.obj['device']

    device = select_device('dfu' if dfu else device)

    flasher.uart.clone(device, filename, length, reporthook=print_progress_bar, label='Read')


@cli.command('reset')
@click.option('-d', '--device', type=str, help='Device path.')
@click.option('--log', is_flag=True, help='Show all releases.')
@bcflog.click_options
@click.pass_context
def command_reset(ctx, device=None, log=False, **args):
    '''Reset core module.'''
    if device is None:
        device = ctx.obj['device']

    if device == 'dfu':
        raise Exception("Sorry, Core Module r1.3 doesn't support log functionality.")

    device = select_device(device)

    if log:
        bcflog.run_args(device, args, reset=True)
    else:
        flasher.reset(device)


@cli.command('search')
@click.argument('search')
@click.option('--all', is_flag=True, help='Show all releases.')
@click.option('--description', is_flag=True, help='Show description.')
@click.option('--show-pre-release', is_flag=True, help='Show pre-release version.')
def command_list(search, all=False, description=False, show_pre_release=False):
    '''Search in firmware names and descriptions.'''
    fwlist = FirmwareList(user_cache_dir)
    rows = fwlist.get_firmware_table(search, all=all, description=description, show_pre_release=show_pre_release)
    if rows:
        print_table([], rows)
    else:
        click.echo('Nothing found')


@cli.command('update')
def command_update():
    '''Update list of available firmware.'''
    fwlist = FirmwareList(user_cache_dir)
    fwlist.update()
    click.echo('OK')


def main():
    '''Application entry point.'''
    try:
        cli(obj={}),
    except KeyboardInterrupt:
        pass
    except Exception as e:
        click.echo(str(e), err=True)
        if os.getenv('DEBUG', False):
            raise e
        sys.exit(1)


if __name__ == '__main__':
    main()
