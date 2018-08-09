#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import os
import sys
import json
from datetime import datetime, timedelta
import hashlib
from collections import OrderedDict
import copy
import logging
import re
import yaml

if sys.version_info[0] == 3:
    from urllib.request import urlopen, urlretrieve, Request
    from urllib.error import HTTPError
else:
    from urllib2 import urlopen, HTTPError, Request
    from urllib import urlretrieve

logger = logging.getLogger(__name__)


class GithubApi:

    def __init__(self, oauth_token=None, cache_dir=None):
        self._oauth_token = oauth_token
        self._cache_dir = cache_dir

        self._response_headers = None

        if self._cache_dir and not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    def get_cache_dir(self):
        return self._cache_dir

    def api_get(self, url):

        if self._cache_dir:
            filename = hashlib.sha256(url.encode()).hexdigest()
            filename_cache = os.path.join(self._cache_dir, filename)
            if os.path.exists(filename_cache):
                c = json.load(open(filename_cache))
                self._response_headers = c['response_headers']
                return c['data']

        try:
            headers = {}
            if self._oauth_token:
                headers["Authorization"] = "token " + self._oauth_token
            req = Request(url, headers=headers)
            response = urlopen(req)
        except HTTPError as e:
            if e.getcode() == 403:
                print("Github API rate limit exceeded, more info https://developer.github.com/v3/#rate-limiting")
                ts = e.headers.get('X-RateLimit-Reset', None)
                if ts:
                    print('Rate limit will be reset in', datetime.fromtimestamp(float(ts)))
            else:
                print(e)
            sys.exit(1)

        self._response_headers = dict(response.headers)

        body = response.read()

        data = json.loads(body.decode('utf-8'))

        if self._cache_dir:
            json.dump({"data": data, "response_headers": self._response_headers}, open(filename_cache, 'w'))

        return data

    def iter_repos(self, owner):
        page = 1
        while True:
            gh_repos = self.api_get('https://api.github.com/users/%s/repos?page=%d' % (owner, page))
            if not gh_repos:
                return

            for gh_repo in gh_repos:
                yield gh_repo

            page += 1

    def make_firmware_list_for_owner(self, owner):
        firmware_list = []

        for repo in self.iter_repos(owner):
            if repo['name'].startswith("bcf-") and repo['name'] not in {"bcf-sdk", "bcf-vscode", "bcf-skeleton"}:
                logging.debug('repo %s/%s', owner, repo['name'])

                firmware_list += self._make_firmware_list(owner, repo['name'])

        return firmware_list

    def make_firmware_list_from_repo(self, url_or_name):
        match = re.search("(?:https://github.com/)?(.+)/(.+)", url_or_name)
        if not match:
            raise "Bad repo url or name format"

        owner, repo = match.groups()

        return self._make_firmware_list(owner, repo)

    def _make_firmware_list(self, owner, repo):

        owner_repo = owner + '/' + repo

        firmware_dict = {}

        firmware = {}
        firmware['name'] = ""
        firmware['description'] = ""
        firmware['repository'] = "https://github.com/" + owner_repo
        firmware['versions'] = []

        for content in self.api_get("https://api.github.com/repos/" + owner_repo + "/contents"):
            if content["name"] == "meta.yml":
                meta_yaml = yaml.load(urlopen(content['download_url']))
                firmware.update(meta_yaml)

        for release in self.api_get("https://api.github.com/repos/" + owner_repo + "/releases"):
            for assets in release.get('assets', []):
                if assets["name"].endswith(".bin") and assets["name"].startswith(repo):
                    name = assets["name"][:-4]
                    if name.endswith(release["tag_name"]):
                        name = owner + "/" + name[:-len(release["tag_name"]) - 1]

                        if name not in firmware_dict:
                            firmware_dict[name] = copy.deepcopy(firmware)
                            firmware_dict[name]['name'] = name

                        firmware_dict[name]['versions'].append({
                            "name": release["tag_name"],
                            "prerelease": release['prerelease'],
                            "url": assets['browser_download_url'],
                            "date": release['published_at']
                        })

        return list(firmware_dict.values())


if __name__ == "__main__":
    from pprint import pprint

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

    ga = GithubApi()

    firmware_list = ga.make_firmware_list_for_owner("bigclownlabs")

    with open('firmware.yml', 'w') as f:
        yaml.safe_dump(firmware_list, f, indent=2, default_flow_style=False)

    # pprint(ga.make_firmware_list_from_repo("https://github.com/bigclownlabs/bcf-radio-power-controller"))

    # pprint(ga.make_firmware_list_from_repo("bigclownlabs/bcf-radio-push-button"))
