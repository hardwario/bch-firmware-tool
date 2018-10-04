import os
import sys
import json
import requests

FIRMWARE_JSON_URL = "https://firmware.bigclown.com/json"


class FirmwareList:

    def __init__(self, cache_dir):
        self._list = []
        self._cache_dir = cache_dir

        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

        bigclown_json = os.path.join(self._cache_dir, 'bigclown.json')
        if os.path.exists(bigclown_json):
            self._extend(json.load(open(bigclown_json)))

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

    def get_firmware_list(self):
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
        print("Download list from %s" % FIRMWARE_JSON_URL)
        bigclown_json = os.path.join(self._cache_dir, 'bigclown.json')
        response = requests.get(FIRMWARE_JSON_URL, allow_redirects=True)
        if response.status_code != 200:
            raise Exception("Response status_code=%d" % response.status_code)
        try:
            data = response.json()
        except Exception as e:
            raise Exception("Bad json format")

        json.dump(data, open(bigclown_json, 'w'))

        self._extend(data)

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
        bigclown_json = os.path.join(self._cache_dir, 'bigclown.json')
        if os.path.exists(bigclown_json):
            os.unlink(bigclown_json)
