#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argcomplete
import argparse
import os
import sys
import hashlib

import appdirs
from .github_repos import Github_Repos, __version__
import .flash_dfu
import .flash_serial

try:
    from urllib import urlretrieve
except ImportError:  # Python 3
    from urllib.request import urlretrieve


def print_table(labels, rows):
    max_lengths = [0] * len(labels)
    for i, label in enumerate(labels):
        max_lengths[i] = len(label)

    for row in rows:
        for i, v in enumerate(row):
            if len(v) > max_lengths[i]:
                max_lengths[i] = len(v)

    row_format = "{:<" + "}  {:<".join(map(str, max_lengths)) + "}"

    print(row_format.format(*labels))

    print("=" * (sum(max_lengths) + len(labels) * 2))

    for row in rows:
        print(row_format.format(*row))


def print_progress_bar(title, progress, total, length=20):
    filled_length = int(length * progress // total)
    bar = '#' * filled_length
    bar += '-' * (length - filled_length)
    percent = 100 * (progress / float(total))
    if percent > 100:
        percent = 100
    print('\r', end='\r')
    print(title + ' ['+bar+'] ' + "{:5.1f}%".format(percent), end=' ')
    if percent == 100:
        print()


def download_url_reporthook(count, blockSize, totalSize):
    print_progress_bar('Download', count*blockSize, totalSize)


def download_url(url, user_cache_dir, use_cache=True):
    filename = hashlib.sha256(url.encode()).hexdigest()
    filename_bin = os.path.join(user_cache_dir, filename)

    if use_cache and os.path.exists(filename_bin):
        return filename_bin

    print('download firmware from', url)
    print('save as', filename_bin)

    urlretrieve(url, filename_bin, reporthook=download_url_reporthook)

    return filename_bin


class FlashChoicesCompleter(object):
    def __call__(self, **kwargs):
        user_cache_dir = appdirs.user_cache_dir('bcf')
        repos = Github_Repos(user_cache_dir)
        # search = kwargs.get('prefix', None)
        return repos.get_firmwares()


def main():
    parser = argparse.ArgumentParser(description='BigClown Firmware Flasher')

    subparsers = parser.add_subparsers(dest='command', metavar='COMMAND')

    subparser_list = subparsers.add_parser('help', help="show help")

    subparser_list = subparsers.add_parser('list', help="list firmwares")
    subparser_list.add_argument('--all', help='show all releases', action='store_true')
    subparser_list.add_argument('--description', help='show description', action='store_true')

    subparser_search = subparsers.add_parser('search', help="search in firmwares names and descriptions")
    subparser_search.add_argument('pattern', help='search pattern')
    subparser_search.add_argument('--all', help='show all releases', action='store_true')
    subparser_search.add_argument('--description', help='show description', action='store_true')

    subparsers.add_parser('update', help="update list of available firmwares")

    subparser_flash = subparsers.add_parser('flash', help="flash firmware",
                                            usage='%(prog)s <firmware>\n       %(prog)s <file>\n       %(prog)s <url>')
    subparser_flash.add_argument('what', help=argparse.SUPPRESS).completer = FlashChoicesCompleter()
    subparser_flash.add_argument('--dfu', help='use dfu mode', action='store_true')

    subparser_pull = subparsers.add_parser('pull', help="pull firmware to cache",
                                           usage='%(prog)s <firmware>\n       %(prog)s <url>')
    subparser_pull.add_argument('what', help=argparse.SUPPRESS)

    subparsers.add_parser('clean', help="clean cache")

    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if not args.command or args.command == 'help':
        parser.print_help()
        exit()

    user_cache_dir = appdirs.user_cache_dir('bcf')
    repos = Github_Repos(user_cache_dir)

    if args.command == 'clean':
        repos.clear()

    elif args.command == 'update':
        repos.update()

    elif args.command == 'pull':
        if args.what.startswith('http'):
            url = args.what
        else:
            firmware = repos.get_firmware(args.what)
            if not firmware:
                print('Firmware not found, try updating first')
                exit(1)
            url = firmware['download_url']
        download_url(url, user_cache_dir, False)

    elif args.command == 'flash':
        if args.what.startswith('http'):
            filename_bin = download_url(args.what, user_cache_dir)

        elif os.path.exists(args.what) and os.path.isfile(args.what):
            filename_bin = args.what

        else:
            firmware = repos.get_firmware(args.what)
            if not firmware:
                print('Firmware not found, try updating first')
                exit(1)
            filename_bin = download_url(firmware['download_url'], user_cache_dir)

        if args.dfu:
            flash_dfu.run(filename_bin)
        else:
            flash_serial.run(filename_bin, '/dev/ttyUSB0', reporthook=print_progress_bar)

    elif args.command == 'list' or args.command == 'search':
        labels = ['Name:Bin:Version']
        if args.description:
            labels.append('description')

        if args.command == 'search':
            rows = repos.get_firmwares_table(search=args.pattern, all=args.all, description=args.description)
        else:
            rows = repos.get_firmwares_table(all=args.all, description=args.description)

        print_table(labels, rows)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
