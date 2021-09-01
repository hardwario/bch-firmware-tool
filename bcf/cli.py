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
import re
from bcf import flasher
from bcf.log import log as bcflog
from bcf.utils import *
import bcf.firmware.utils as futils
from bcf import ftdi


__version__ = '@@VERSION@@'
SDK_URL_ZIP = 'https://codeload.github.com/hardwario/bcf-sdk/zip/master'
SDK_GIT = 'https://github.com/hardwario/bcf-sdk.git'
VSCODE_GIT = 'https://github.com/hardwario/bcf-vscode.git'
VSCODE_URL_ZIP = 'https://codeload.github.com/hardwario/bcf-vscode/zip/master'


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
    fwlist = get_fwlist()
    fwlist.clear()
    for filename in os.listdir(user_cache_dir):
        os.unlink(os.path.join(user_cache_dir, filename))


def _create_get_firmware_list(ctx, args, incomplete):
    if 'bigclownlabs/bcf-skeleton'.startswith(incomplete):
        return ['bigclownlabs/bcf-skeleton'] + get_fwlist().get_firmware_list(startswith=incomplete, add_latest=False)
    else:
        return get_fwlist().get_firmware_list(startswith=incomplete, add_latest=False)


@cli.command('create')
@click.argument('name')
@click.option('--no-git', is_flag=True, help='Disable git.')
@click.option('--from', '_from', help='Disable git.', default='hardwario/bcf-skeleton', autocompletion=_create_get_firmware_list)
@click.option('--depth', 'depth', help='Set git submodule clone depth.')
def command_create(name, no_git, _from, depth):
    '''Create new firmware.'''

    if os.path.exists(name):
        print('Directory already exists')
        sys.exit(1)

    _from = _from.rstrip('/')

    if _from == 'hardwario/bcf-skeleton':
        repository = 'https://github.com/hardwario/bcf-skeleton'
    elif re.match('^https://github.com/[^/]+/[^/]+$', _from):
        repository = _from
    else:
        fwlist = get_fwlist()
        fw = fwlist.get_firmware(_from)
        if not fw:
            raise Exception('Firmware not found.')
        repository = fw['repository']

    repo_zip_file = repository.replace('github.com', 'codeload.github.com') + '/zip/master'

    zip_filename = download_url(repo_zip_file, use_cache=False)
    click.echo()

    tmp_dir = tempfile.mkdtemp()

    zip_ref = zipfile.ZipFile(zip_filename, 'r')
    zip_ref.extractall(tmp_dir)
    zip_ref.close()

    skeleton_path = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
    shutil.move(skeleton_path, name)

    shutil.rmtree(os.path.join(name, 'sdk'), ignore_errors=True)
    shutil.rmtree(os.path.join(name, '.vscode'), ignore_errors=True)
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
        depth = '' if not depth else ' --depth ' + str(depth)
        os.system('git submodule add' + depth + ' "' + SDK_GIT + '" sdk')
        os.system('git submodule add' + depth + ' "' + VSCODE_GIT + '" .vscode')

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
@click.option('--read', type=str, help='Read EEPROM and save to file.', metavar='FILE')
@click.option('--erase', is_flag=True, help='Erase EEPROM.')
@click.option('--write', type=str, help='Read file adn write to EEPROM.', metavar='FILE')
@click.option('--dfu', is_flag=True, help='Use dfu mode.')
@click.pass_context
def command_eeprom(ctx, device, read, erase, write, dfu):
    '''Work with EEPROM.'''
    if device is None:
        device = ctx.obj['device']

    if not read and not erase and not write:
        click.echo(ctx.get_help())
        return

    device = select_device('dfu' if dfu else device)

    if read:
        flasher.eeprom_read(device, read, address=0, length=6144, reporthook=print_progress_bar)

    if erase:
        flasher.eeprom_erase(device, reporthook=print_progress_bar)

    if write:
        flasher.eeprom_write(device, write, address=0, length=6144, reporthook=print_progress_bar)


def _flash_get_firmware_list(ctx, args, incomplete):
    files = list(filter(lambda name: name.startswith(incomplete), glob.glob('*.bin')))
    return files + get_fwlist().get_firmware_list(startswith=incomplete)


@cli.command('flash')
@click.argument('what', metavar="<firmware from list|file|url|firmware.bin>", default="firmware.bin", autocompletion=_flash_get_firmware_list)
@click.option('-d', '--device', type=str, help='Device path.')
@click.option('--log', is_flag=True, help='Show all releases.')
@click.option('--dfu', is_flag=True, help='Use dfu mode.')
@click.option('--erase-eeprom', is_flag=True, help='Erase eeprom.')
@click.option('--unprotect', is_flag=True, help='Unprotect.')
@click.option('--skip-verify', is_flag=True, help='Skip verify.')
@click.option('--diff', is_flag=True, help='Flash only different pages.')
@click.option('--slow', is_flag=True, help='Slow flash, same as --baudrate 115200.')
@click.option('--baudrate', type=int, help='Baudrate (default 921600).', default=921600)
@bcflog.click_options
@click.pass_context
def command_flash(ctx, what, device, log, dfu, erase_eeprom, unprotect, skip_verify, diff, slow, baudrate, **args):
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
        fwlist = get_fwlist()
        firmware = fwlist.get_firmware_version(what)
        if not firmware:
            raise Exception('Firmware not found, try updating first, command: bcf update')
            sys.exit(1)
        filename = download_url(firmware['url'])

    try:
        device = select_device('dfu' if dfu else device)

        if slow:
            baudrate = 115200

        flasher.flash(filename, device, reporthook=print_progress_bar, run=not log, erase_eeprom=erase_eeprom, unprotect=unprotect, skip_verify=skip_verify, diff=diff, baudrate=baudrate)
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
    fwlist = get_fwlist()
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

        fwlist = get_fwlist()

        if what in ('last', 'latest'):
            for name in fwlist.get_firmware_list():
                firmware = fwlist.get_firmware_version(name)
                click.echo('pull ' + name)
                download_url(firmware['url'], True)
                click.echo('')
        else:
            firmware = fwlist.get_firmware_version(what)
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
    fwlist = get_fwlist()
    rows = fwlist.get_firmware_table(search, all=all, description=description, show_pre_release=show_pre_release)
    if rows:
        print_table([], rows)
    else:
        click.echo('Nothing found')


@cli.command('update')
def command_update():
    '''Update list of available firmware.'''
    fwlist = get_fwlist()
    fwlist.update()


@cli.group('source')
def source():
    '''Firmware source.'''


@source.command('list')
def command_source_list():
    '''List firmware source.'''
    for name in get_fwlist().source_get_list():
        click.echo(name)


@source.command('add')
@click.argument('url', metavar="URL")
def command_source_add(url):
    '''Add firmware source.'''
    get_fwlist().source_add(url)
    click.secho('OK', fg='green')


@source.command('remove')
@click.option('--no-remove-from-list', 'remove_from_list', is_flag=True, help='Flag for remove from the bcf list.', default=True)
@click.argument('url', metavar="URL")
def command_source_remove(remove_from_list, url):
    '''Remove firmware source.'''
    get_fwlist().source_remove(url, remove_from_list)
    click.secho('OK', fg='green')


@source.command('test')
def command_source_test():
    '''Test firmware source.'''
    for name in get_fwlist().source_get_list():
        click.echo(name)
        data = futils.load_source_from_url(name)
        if data:
            for fwdata in data['list']:
                click.echo(fwdata['repository'])
                futils.test_firmware_resources(fwdata)


@cli.command('test')
@click.argument('path', metavar="PATH", default='.')
@click.option('--skip-url', 'skip_url', is_flag=True, help='Skip testing the availability of urls.')
def command_test(path, skip_url):
    '''Test firmware source.'''
    meta_yml_filename = os.path.join(path, 'meta.yml')

    click.echo('Test %s' % meta_yml_filename)

    with open(meta_yml_filename, 'r') as fd:
        meta_yaml = futils.load_meta_yaml(fd)

    click.echo("  - file is valid")

    if not skip_url:
        futils.test_firmware_resources(meta_yaml)


@cli.command('ftdi')
@click.option('-d', '--device', 'sn', type=str, help='FTDI device serial number (or regex).')
@click.option('-m', '--manufacturer', type=str, help='Update the USB manufacturer string.')
@click.option('-p', '--product', type=str, help='Update the USB product string.')
@click.option('-s', '--serial', type=str, help='Update the USB serial string.')
@click.option('-r', '--reset', is_flag=True, help='Force USB device reset.')
def command_ftdi(sn, manufacturer=None, product=None, serial=None, reset=False):
    '''Update USB descriptors in the FTDI chip.'''

    if manufacturer is not None or product is not None or serial is not None or reset:
        ftdi.update_eeprom(sn, manufacturer, product, serial, reset)
    else:
        ftdi.list_devices(sn)


def main():
    '''Application entry point.'''
    try:
        cli(obj={}),
    except KeyboardInterrupt:
        pass
    except Exception as e:
        click.secho(str(e), err=True, fg='red')
        if os.getenv('DEBUG', False):
            raise e
        sys.exit(1)


if __name__ == '__main__':
    main()
