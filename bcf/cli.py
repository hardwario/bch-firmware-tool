#!/usr/bin/env python3

import argparse
import os
import subprocess
import hashlib

from .github_repos import Github_Repos, __version__
from .lang import tab as lang_tab
import appdirs

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


def dfu(filename_bin, lang):
    dfu = "dfu-util"
    try:
        subprocess.check_output([dfu, "--version"])
    except Exception:
        print("Please install dfu-util:")
        print("sudo apt install dfu-util")
        print("Or from https://sourceforge.net/projects/dfu-util/files/?source=navbar")
        return False

    cmd = [dfu, "-s", "0x08000000:leave", "-d", "0483:df11", "-a", "0", "-D", filename_bin]

    status = subprocess.call(cmd)

    if status:
        print("=" * 60)
        print(lang_tab[lang]['dfu-help'])
        return False


def flesh(filename_bin, use_dfu, lang):
    if use_dfu:
        dfu(filename_bin, lang)
    else:
        print("use --dfu")
        exit()


def download_url(url, user_cache_dir):
    filename = hashlib.sha256(url.encode()).hexdigest() + '.bin'
    filename_bin = os.path.join(user_cache_dir, filename)

    print('download firmware from', url)
    print('save as', filename_bin)

    urlretrieve(url, filename_bin)

    return filename_bin


def main():
    argp = argparse.ArgumentParser(description='BigClown flesh')
    argp.add_argument('--dfu', help='Use dfu mode', action='store_true')
    argp.add_argument('--id', help='Download and flash firmware with id')
    argp.add_argument('--url', help='Download and flash firmware')
    argp.add_argument('-s', '--search', help='Search')
    argp.add_argument('-d', '--description', help='Show description', action='store_true')
    argp.add_argument('-a', '--all', help='Show all releases', action='store_true')
    argp.add_argument('--clear', help='Clear cache', action='store_true')
    argp.add_argument('--no-update', help='Disable update', action='store_true')
    argp.add_argument("--lang", default='en', choices=['en', 'cs'])
    argp.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
    argp.add_argument("FILENAME", nargs='?')
    args = argp.parse_args()

    user_cache_dir = appdirs.user_cache_dir('bcf')

    repos = Github_Repos(user_cache_dir)

    if args.clear:
        repos.clear()
        repos.clear()

    if not args.no_update and not args.FILENAME and not args.url:
        repos.update()

    if args.id:

        try:
            filename_bin = repos.download_firmware(args.id)
        except Exception as e:
            print(e)
            exit()

        flesh(filename_bin, args.dfu, args.lang)

    elif args.FILENAME:
        flesh(args.FILENAME, args.dfu, args.lang)

    elif args.url:
        filename_bin = download_url(args.url, user_cache_dir)
        flesh(filename_bin, args.dfu, args.lang)

    else:
        name_max_length = max(map(len, repos.get_repos().keys()))

        row_format = "{:<"+str(name_max_length)+"} {}"

        labels = ['Id', 'Name', 'Version', 'Bin']
        if args.description:
            labels.append('description')

        rows = repos.get_firmwares_table(search=args.search, all=args.all, description=args.description)

        print_table(labels, rows)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
