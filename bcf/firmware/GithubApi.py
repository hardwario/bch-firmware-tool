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
import requests
from .yml_schema import meta_yml_schema, validate

logger = logging.getLogger(__name__)


class GithubApi:

    def __init__(self, oauth_token=None, cache_dir=None):
        self._cache_dir = cache_dir

        self._response_headers = None

        if self._cache_dir and not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

        self._session = requests.Session()

        if oauth_token:
            self._session.headers.update({'Authorization': "token " + oauth_token})

    def get_cache_dir(self):
        return self._cache_dir

    def api_get(self, url):
        logger.debug("api_get %s", url)

        if self._cache_dir:
            filename = hashlib.sha256(url.encode()).hexdigest()
            filename_cache = os.path.join(self._cache_dir, filename)
            if os.path.exists(filename_cache):
                c = json.load(open(filename_cache))
                self._response_headers = c['response_headers']
                return c['data']

        response = self._session.get(url)

        self._response_headers = dict(response.headers)

        if response.status_code == 200:
            data = response.json()

            if self._cache_dir:
                json.dump({"data": data, "response_headers": self._response_headers}, open(filename_cache, 'w'))

            return data

        if response.status_code == 403:
            print("Github API rate limit exceeded, more info https://developer.github.com/v3/#rate-limiting")
            ts = self._response_headers.get('X-RateLimit-Reset', None)
            if ts:
                print('Rate limit will be reset in', datetime.fromtimestamp(float(ts)))
                sys.exit(1)

        print("Response status_code %d" % response.status_code)
        sys.exit(1)

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
                logger.debug('repo %s/%s', owner, repo['name'])

                firmware_list += self._make_firmware_list(owner, repo['name'], repo_obj=repo)

        return firmware_list

    def make_firmware_list_from_repo(self, url_or_name):
        match = re.search("(?:https://github.com/)?(.+)/(.+)", url_or_name)
        if not match:
            raise "Bad repo url or name format"

        owner, repo = match.groups()

        return self._make_firmware_list(owner, repo)

    def _make_firmware_list(self, owner, repo, repo_obj=None):
        owner_repo = owner + '/' + repo

        logger.info(owner_repo)

        firmware_dict = {}

        firmware = {}
        firmware['name'] = ""
        firmware['description'] = repo_obj['description'] if repo_obj and repo_obj['description'] else ""
        firmware['repository'] = "https://github.com/" + owner_repo
        firmware['versions'] = []

        for content in self.api_get("https://api.github.com/repos/" + owner_repo + "/contents"):
            if content["name"] == "meta.yml":
                response = self._session.get(content['download_url'])
                meta_yaml = yaml.safe_load(response.content)

                try:
                    validate(meta_yml_schema, meta_yaml)

                    firmware.update(meta_yaml)
                except Exception as e:
                    logger.warning(str(e))

                break
        else:
            logger.warning("No meta.yml file found.")

        for release in self.api_get("https://api.github.com/repos/" + owner_repo + "/releases"):
            for assets in release.get('assets', []):
                if assets["name"].endswith(".bin"):
                    if not assets["name"].startswith(repo):
                        logger.warning('file "%s" does not start the same as the repository name', assets["name"])
                        continue

                    name = assets["name"][:-4]

                    if not name.endswith(release["tag_name"]):
                        logger.warning('file %s does not end with the version name %s', assets["name"], release["tag_name"])
                        continue

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
