# -*- coding: utf-8 -*-
import os
import sys
import json
import yaml
import requests
from .yml_schema import source_yml_schema

DEFAULT_SOURCE = [
    {
        'type': 'list',
        'url': "https://firmware.bigclown.com/json",
    }
]


class FirmwareList:

    def __init__(self, cache_dir, config_dir):
        self._list = []
        self._source = None

        self._cache_dir = cache_dir
        self._config_dir = config_dir

        os.makedirs(self._cache_dir, exist_ok=True)
        os.makedirs(self._config_dir, exist_ok=True)

        self._load_list_yml()

    def get_firmware(self, name):
        try:
            name, version = name.split(':')
        except Exception as e:
            raise Exception("Bad firmware name")

        for firmware in self._list:
            if name == firmware['name']:
                if 'versions' not in firmware or not firmware['versions']:
                    return

                if version == 'latest':
                    return firmware['versions'][0]

                for v in firmware['versions']:
                    if version == v['name']:
                        return v

    def get_firmware_list(self, startswith=None):
        if startswith:
            array = []
            for firmware in self._list:
                if firmware['name'].startswith(startswith):
                    array.append(firmware['name'] + ':latest')
            return array
        else:
            return [firmware['name'] + ':latest' for firmware in self._list]

    def get_firmware_table(self, search='', all=False, description=False, show_pre_release=False):
        table = []
        for firmware in self._list:
            if 'versions' not in firmware or not firmware['versions']:
                continue

            for version in firmware['versions']:
                n = firmware['name'] + ':' + version['name']

                row = [n]

                if description:
                    row.append(firmware['description'])

                if search:
                    if search in n or (firmware['description'] and search in firmware['description']):
                        table.append(row)
                else:
                    table.append(row)

                if not all:
                    break

        return table

    def update(self):
        self._load_source_yml()
        for source in self._source:
            if source['type'] == 'list':
                print("Download list from %s" % source['url'])

                response = requests.get(source['url'], allow_redirects=True)
                if response.status_code != 200:
                    raise Exception("Response status_code=%d" % response.status_code)

                data = yaml.safe_load(response.text)
                self._extend(data)
        self._save_list_yml()

    def _extend(self, data):
        for new in data['list']:
            for i, old in enumerate(self._list):
                if new['name'] == old['name']:
                    self._list[i] = new
                    break
            else:
                self._list.append(new)

    def clear(self):
        self._list = []
        filename = os.path.join(self._cache_dir, 'firmware_list.yml')
        if os.path.exists(filename):
            os.unlink(filename)

    def _load_list_yml(self):
        filename = os.path.join(self._cache_dir, 'firmware_list.yml')

        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as fd:
                    self._list = yaml.safe_load(fd)
            except Exception as e:
                raise Exception('Error load source yml ' + str(e))
        else:
            self.update()

    def _save_list_yml(self):
        filename = os.path.join(self._cache_dir, 'firmware_list.yml')
        with open(filename, 'w', encoding='utf-8') as fd:
            yaml.safe_dump(self._list, fd, indent=2)

    def _load_source_yml(self):
        if self._source is not None:
            return

        source_yml = DEFAULT_SOURCE
        filename = os.path.join(self._config_dir, 'source.yml')
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as fd:
                    source_yml = yaml.safe_load(fd)
        except Exception as e:
            raise Exception('Error load source yml ' + str(e))

        self._source = source_yml_schema.validate(source_yml)

    def _save_source_yml(self):
        if self._source is None:
            return
        filename = os.path.join(self._config_dir, 'source.yml')
        with open(filename, 'w', encoding='utf-8') as fd:
            yaml.safe_dump(self._list, fd, indent=2)
