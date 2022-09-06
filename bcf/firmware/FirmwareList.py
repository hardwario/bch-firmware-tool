# -*- coding: utf-8 -*-
import os
import sys
import json
import yaml
import requests
import hashlib
import uuid
import click
from .yml_schema import source_yml_schema
from . import utils

DEFAULT_SOURCE_API = 'https://firmware.hardwario.com/tower/api/v1/list'


class FirmwareList:

    def __init__(self, cache_dir, config_dir):
        self._list = []
        self._source = None

        self._cache_dir = cache_dir
        self._config_dir = config_dir

        os.makedirs(self._cache_dir, exist_ok=True)
        os.makedirs(self._config_dir, exist_ok=True)

        self._load_list_yml()

    def firmware_iter(self):
        for row in self._list:
            for fw in row['list']:
                yield fw

    def get_firmware(self, name):
        index = name.find(':')
        if index > -1:
            name = name[:index]
        for firmware in self.firmware_iter():
            if name == firmware['name']:
                return firmware

    def get_firmware_version(self, name):
        try:
            name, version = name.split(':')
        except Exception as e:
            raise Exception("Bad firmware name")

        for firmware in self.firmware_iter():
            if name == firmware['name']:
                if 'versions' not in firmware or not firmware['versions']:
                    return

                if version == 'latest':
                    return firmware['versions'][0]

                for v in firmware['versions']:
                    if version == v['name']:
                        return v

    def get_firmware_list(self, startswith=None, add_latest=True):
        suffix = ':latest' if add_latest else ''
        if startswith:
            array = []
            for firmware in self.firmware_iter():
                if firmware['name'].startswith(startswith):
                    array.append(firmware['name'] + suffix)
            return array
        else:
            return [firmware['name'] + suffix for firmware in self.firmware_iter()]

    def get_firmware_table(self, search='', all=False, description=False, show_pre_release=False):
        table = []
        for firmware in self.firmware_iter():
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
                data = utils.load_source_from_url(source['url'])
                if data:
                    self._list_update(source, data)
            elif source['type'] == 'api':
                data = utils.load_source_from_url(source['url'])
                if data:
                    self._list_update(source, {'list': data})

        self._save_list_yml()

    def _list_update(self, source, data):
        for row in self._list:
            if row['source']['id'] == source['id']:
                row['list'] = data['list']
                break
        else:
            self._list.append({
                'source': {
                    'id': source['id'],
                    'url': source['url'],
                    'type': source['type']
                },
                'list': data['list']
            })

    def clear(self):
        self._list = []
        filename = os.path.join(self._cache_dir, 'firmware_list.yml')
        if os.path.exists(filename):
            os.unlink(filename)

    def source_get_list(self):
        self._load_source_yml()
        return [source['url'] for source in self._source]

    def source_remove(self, url, remove_from_list=True):
        self._load_source_yml()
        for source in self._source:
            if source['url'] == url:
                break
        else:
            raise Exception('This source not exists.')

        if remove_from_list:
            find_i = None
            for i, row in enumerate(self._list):
                if row['source']['id'] == source['id']:
                    find_i = i
                    break

            if find_i:
                del self._list[find_i]
                self._save_list_yml()

        self._source.remove(source)
        self._save_source_yml()

    def source_add(self, url, type):
        self._load_source_yml()
        for source in self._source:
            if source['url'] == url:
                raise Exception('This source alredy exists.')

        source = {
            'type': type,
            'url': url,
        }

        source['id'] = hashlib.sha1(json.dumps(source).encode()).hexdigest()

        response = requests.get(url, allow_redirects=True)
        data = yaml.safe_load(response.text)

        self._source.append(source)
        self._save_source_yml()

        self._list_update(source, data)
        self._save_list_yml()

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
            yaml.safe_dump(self._list, fd, indent=2, default_flow_style=False)

    def _load_source_yml(self):
        if self._source is not None:
            return

        filename = os.path.join(self._config_dir, 'source.yml')
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as fd:
                    source_yml = yaml.safe_load(fd)
                    self._source = source_yml_schema.validate(source_yml)
                    print(self._source)
                    for source in self._source:
                        if source['url'] == 'https://firmware.bigclown.com/json':
                            source['url'] = DEFAULT_SOURCE_API
                            source['type'] = 'api'
                            self.clear()
                            self._save_source_yml()
            else:
                self._source = []
                return self.source_add(DEFAULT_SOURCE_API, 'api')

        except Exception as e:
            raise Exception('Error load source yml ' + str(e))

    def _save_source_yml(self):
        if self._source is None:
            return
        filename = os.path.join(self._config_dir, 'source.yml')
        with open(filename, 'w', encoding='utf-8') as fd:
            yaml.safe_dump(self._source, fd, indent=2, default_flow_style=False)
