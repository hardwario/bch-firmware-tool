#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
from __future__ import print_function, unicode_literals
import argcomplete
import argparse
import os
import sys
import logging
import hashlib
import glob
import tempfile
import zipfile
import shutil
import platform
import subprocess
import appdirs
import serial
from distutils.version import LooseVersion
from bcf.github_repos import Github_Repos
from bcf import flasher
from bcf.log import log

try:
    from urllib import urlretrieve
except ImportError:  # Python 3
    from urllib.request import urlretrieve

__version__ = '@@VERSION@@'
SKELETON_URL_ZIP = 'https://github.com/bigclownlabs/bcf-skeleton/archive/master.zip'
SDK_URL_ZIP = 'https://github.com/bigclownlabs/bcf-sdk/archive/master.zip'
SDK_GIT = 'https://github.com/bigclownlabs/bcf-sdk.git'

pyserial_34 = LooseVersion(serial.VERSION) >= LooseVersion("3.4.0")

user_cache_dir = appdirs.user_cache_dir('bcf')
user_config_dir = appdirs.user_config_dir('bcf')


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
        print(row_format.format(*labels))
        print("=" * (sum(max_lengths) + len(labels) * 2))

    for row in rows:
        print(row_format.format(*row))


def print_progress_bar(title, progress, total, length=20):
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

    print('download firmware from', url)
    print('save as', filename_bin)

    try:
        urlretrieve(url, filename_bin, reporthook=download_url_reporthook)
    except Exception as e:
        print("Firmware download problem:", e.args[0])
        sys.exit(1)
    return filename_bin


class FirmwareChoicesCompleter(object):
    def __init__(self, find_bin):
        self._find_bin = find_bin

    def __call__(self, **kwargs):
        repos = Github_Repos(user_config_dir, user_cache_dir)
        firmwares = repos.get_firmware_list()
        if self._find_bin:
            firmwares += glob.glob('*.bin')
        return firmwares


def command_devices(verbose=False, include_links=False):
    if os.name == 'nt' or sys.platform == 'win32':
        from serial.tools.list_ports_windows import comports
    elif os.name == 'posix':
        from serial.tools.list_ports_posix import comports

    if pyserial_34:
        ports = comports(include_links=include_links)
    else:
        ports = comports()

    sorted(ports)

    for port, desc, hwid in ports:
        sys.stdout.write("{:20}\n".format(port))
        if verbose:
            sys.stdout.write("    desc: {}\n".format(desc))
            sys.stdout.write("    hwid: {}\n".format(hwid))


def command_flash(args, repos):
    if args.what.startswith('http'):
        filename_bin = download_url(args.what)

    elif os.path.exists(args.what) and os.path.isfile(args.what):
        filename_bin = args.what

    else:
        firmware = repos.get_firmware(args.what)
        if not firmware:
            print('Firmware not found, try updating first')
            sys.exit(1)
        filename_bin = download_url(firmware['download_url'])

    try:
        flasher.flash(filename_bin, args.device, reporthook=print_progress_bar, use_dfu=args.dfu, run=not args.log)
        if args.log:
            log.run_args(args, reset=True)
    except KeyboardInterrupt as e:
        print("")
        sys.exit(1)
    except Exception as e:
        print(e)
        if isinstance(e, flasher.serialport.error.ErrorLockDevice):
            print("TIP: Maybe the bcg service is running - you need to stop it first.")
            if os.path.exists("/etc/init.d/bcg-ud"):
                print("Try this command:")
                print("/etc/init.d/bcg-ud stop")
            else:
                try:
                    process = subprocess.Popen(['pm2', '-m', 'list'], stdout=subprocess.PIPE)
                    out, err = process.communicate()
                    for line in out.splitlines():
                        if line.startswith(b"+---"):
                            name = line[5:].decode()
                            if 'bcg' in name and name != 'bcg-cm':
                                print("Try this command:")
                                print("pm2 stop %s" % name)
                except Exception as e:
                    pass
        if os.getenv('DEBUG', False):
            raise e
        sys.exit(1)


def command_reset(args):
    try:
        if args.log:
            log.run_args(args, reset=True)
        else:
            flasher.reset(args.device)

    except KeyboardInterrupt as e:
        sys.exit(1)
    except Exception as e:
        print(e)
        if os.getenv('DEBUG', False):
            raise e
        sys.exit(1)


def test_log_argumensts(args, parser):
    if not args.log and (args.time or args.no_color or args.record):
        parser.error('--log is required when use --time or --no-color or --record.')


def main():
    parser = argparse.ArgumentParser(description='BigClown Firmware Tool')

    subparsers = {}
    subparser = parser.add_subparsers(dest='command', metavar='COMMAND')

    subparsers['update'] = subparser.add_parser('update', help="update list of available firmware")

    subparsers['list'] = subparser.add_parser('list', help="list firmware")
    subparsers['list'].add_argument('--all', help='show all releases', action='store_true')
    subparsers['list'].add_argument('--description', help='show description', action='store_true')
    subparsers['list'].add_argument('--show-pre-release', help='show pre-release version', action='store_true')

    subparsers['flash'] = subparser.add_parser('flash', help="flash firmware",
                                               usage='%(prog)s\n       %(prog)s <firmware>\n       %(prog)s <file>\n       %(prog)s <url>')
    subparsers['flash'].add_argument('what', help=argparse.SUPPRESS, nargs='?',
                                     default="firmware.bin").completer = FirmwareChoicesCompleter(True)
    subparsers['flash'].add_argument('--device', help='device', required='--dfu' not in sys.argv)
    group = subparsers['flash'].add_mutually_exclusive_group()
    group.add_argument('--dfu', help='use dfu mode', action='store_true')
    group.add_argument('--log', help='run log', action='store_true')
    group_log = subparsers['flash'].add_argument_group('optional for --log arguments')
    log.add_arguments(group_log)

    subparsers['devices'] = subparser.add_parser('devices', help="show devices")
    subparsers['devices'].add_argument('-v', '--verbose', action='store_true', help='show more messages')
    subparsers['devices'].add_argument('-s', '--include-links', action='store_true', help='include entries that are symlinks to real devices' if pyserial_34 else argparse.SUPPRESS)

    subparsers['search'] = subparser.add_parser('search', help="search in firmware names and descriptions")
    subparsers['search'].add_argument('pattern', help='search pattern')
    subparsers['search'].add_argument('--all', help='show all releases', action='store_true')
    subparsers['search'].add_argument('--description', help='show description', action='store_true')
    subparsers['search'].add_argument('--show-pre-release', help='show pre-release version', action='store_true')

    subparsers['pull'] = subparser.add_parser('pull', help="pull firmware to cache",
                                              usage='%(prog)s <firmware>\n       %(prog)s <url>')
    subparsers['pull'].add_argument('what', help=argparse.SUPPRESS).completer = FirmwareChoicesCompleter(False)

    subparsers['clean'] = subparser.add_parser('clean', help="clean cache")

    subparsers['create'] = subparser.add_parser('create', help="create new firmware")
    subparsers['create'].add_argument('name', help=argparse.SUPPRESS)
    subparsers['create'].add_argument('--no-git', help='disable git', action='store_true')

    subparsers['read'] = subparser.add_parser('read', help="download firmware to file")
    subparsers['read'].add_argument('filename', help=argparse.SUPPRESS)
    subparsers['read'].add_argument('--device', help='device', required=True)
    subparsers['read'].add_argument('--length', help='length', default=196608, type=int)

    subparsers['log'] = subparser.add_parser('log', help="show log")
    subparsers['log'].add_argument('--device', help='device', required=True)
    log.add_arguments(subparsers['log'])

    subparsers['reset'] = subparser.add_parser('reset', help="reset core module, not work for r1.3")
    subparsers['reset'].add_argument('--device', help='device', required=True)
    subparsers['reset'].add_argument('--log', help='run log', action='store_true')
    group_log = subparsers['reset'].add_argument_group('optional for --log arguments')
    log.add_arguments(group_log)

    subparser_help = subparser.add_parser('help', help="show help")
    subparser_help.add_argument('what', help=argparse.SUPPRESS, nargs='?', choices=subparsers.keys())
    subparser_help.add_argument('--all', help='show help for all commands', action='store_true')

    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit()

    if args.command == 'help':
        if args.what:
            subparsers[args.what].print_help()
        else:
            parser.print_help()
            print("  --all          show help for all commands")
            if args.all:
                print("=" * 60 + os.linesep)
                for subparser in subparser.choices:
                    if subparser in subparsers:
                        subparsers[subparser].print_help()
                        print(os.linesep)
        sys.exit()

    repos = Github_Repos(user_config_dir, user_cache_dir)

    if args.command == 'list' or args.command == 'search':
        # labels = ['Name:Bin:Version']
        # if args.description:
        #     labels.append('description')

        rows = repos.get_firmware_table(search=args.pattern if args.command == 'search' else None,
                                        all=args.all,
                                        description=args.description,
                                        show_pre_release=args.show_pre_release)

        if rows:
            print_table([], rows)
        elif args.command == 'list':
            print('Nothing found, try updating first')
        else:
            print('Nothing found')

    elif args.command == 'flash':
        test_log_argumensts(args, subparsers['flash'])
        command_flash(args, repos)

    elif args.command == 'update':
        repos.update()

    elif args.command == 'devices':
        command_devices(verbose=args.verbose, include_links=args.include_links)

    elif args.command == 'pull':
        if args.what == 'last':
            for name in repos.get_firmware_list():
                firmware = repos.get_firmware(name)
                print('pull', name)
                download_url(firmware['download_url'], True)
                print()

        elif args.what.startswith('http'):
            download_url(args.what, True)
        else:
            firmware = repos.get_firmware(args.what)
            if not firmware:
                print('Firmware not found, try updating first, command: bcf update')
                sys.exit(1)
            download_url(firmware['download_url'], True)

    elif args.command == 'clean':
        repos.clear()
        for filename in os.listdir(user_cache_dir):
            os.unlink(os.path.join(user_cache_dir, filename))

    elif args.command == 'create':
        name = args.name

        if os.path.exists(name):
            print('Directory already exists')
            sys.exit(1)

        skeleton_zip_filename = download_url(SKELETON_URL_ZIP)
        print()

        tmp_dir = tempfile.mkdtemp()

        zip_ref = zipfile.ZipFile(skeleton_zip_filename, 'r')
        zip_ref.extractall(tmp_dir)
        zip_ref.close()

        skeleton_path = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
        shutil.move(skeleton_path, name)

        os.rmdir(os.path.join(name, 'sdk'))
        os.chdir(name)

        if args.no_git:
            sdk_zip_filename = download_url(SDK_URL_ZIP)
            zip_ref = zipfile.ZipFile(sdk_zip_filename, 'r')
            zip_ref.extractall(tmp_dir)
            zip_ref.close()

            sdk_path = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
            shutil.move(sdk_path, 'sdk')

        else:

            os.system('git init')
            os.system('git submodule add --depth 1 "' + SDK_GIT + '" sdk')

        os.rmdir(tmp_dir)

    elif args.command == 'read':
        flasher.uart.clone(args.device, args.filename, args.length, reporthook=print_progress_bar)

    elif args.command == 'log':
        log.run_args(args)

    elif args.command == 'reset':
        test_log_argumensts(args, subparsers['reset'])
        command_reset(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
