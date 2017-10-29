import os
import json

try:
    from urllib import urlopen, urlretrieve
except ImportError:  # Python 3
    from urllib.request import urlopen, urlretrieve


class Github_Repos:

    def __init__(self, user_cache_dir):
        self._user_cache_dir = user_cache_dir
        if not os.path.exists(self._user_cache_dir):
            os.makedirs(self._user_cache_dir)
        self._cache_repos = os.path.join(self._user_cache_dir, 'repos.json')
        self._repos = {}
        self._updated = []
        if os.path.exists(self._cache_repos):
            try:
                self._repos = json.load(open(self._cache_repos))
            except Exception as e:
                self._repos = {}

    def get_repos(self):
        return self._repos

    def get_user_cache_dir(self):
        return self._user_cache_dir

    def get_updated(self):
        return self._updated

    def get_firmware_table(self, search='', all=False, description=False, show_pre_release=False):
        table = []
        names = list(self._repos.keys())
        names.sort()
        for name in names:
            repo = self._repos[name]
            if not search or search in name or (description and search in repo['description']):
                for release in repo['releases']:

                    if release.get('prerelease', False) and not show_pre_release:
                        continue

                    for i, firmware in enumerate(release['firmwares']):
                        if firmware['name'].startswith(name) and firmware['name'].endswith(release['tag_name'] + ".bin"):
                            tmp = firmware['name'][:firmware['name'].rfind(release['tag_name']) - 1]
                        else:
                            tmp = name + ':' + firmware['name']

                        n = 'bigclownlabs/' + tmp + ':' + release['tag_name']

                        row = [n]

                        if description:
                            row.append(repo['description'])
                        table.append(row)
                    if not all:
                        break
        return table

    def get_firmware_list(self, show_pre_release=False):
        table = []
        names = list(self._repos.keys())
        names.sort()
        for name in names:
            repo = self._repos[name]
            for release in repo['releases']:

                if release.get('prerelease', False) and not show_pre_release:
                    continue

                for firmware in release['firmwares']:
                    if firmware['name'].startswith(name) and firmware['name'].endswith(release['tag_name'] + ".bin"):
                        tmp = firmware['name'][:firmware['name'].rfind(release['tag_name']) - 1]
                        table.append('bigclownlabs/' + tmp + ':latest')
                    else:
                        table.append('bigclownlabs/' + name + ':' + firmware['name'] + ':latest')
                break
        return table

    def get_firmware(self, name):
        name = name.split('/', 1)

        if len(name) != 2 or name[0] != 'bigclownlabs':
            return

        if name[1].endswith(".bin"):
            name[1] += ":latest"

        name = name[1].split(':')

        if len(name) == 2:
            tag_name = name[1]
            firmware_name = name[0]

            for name in self._repos:
                if firmware_name.startswith(name):
                    repo = self._repos[name]
                    for release in repo['releases']:
                        for firmware in release['firmwares']:
                            tmp = firmware['name'][:firmware['name'].rfind(release['tag_name']) - 1]
                            if tmp == firmware_name and (tag_name == 'latest' or tag_name == release['tag_name']):
                                return firmware

        elif len(name) == 3:
            tag_name = name[2]
            firmware_name = name[1]
            repo = self._repos.get(name[0], None)
            if repo is None:
                return

            for release in repo['releases']:
                if (tag_name == 'latest' and not release.get('prerelease', False)) or tag_name == release['tag_name']:
                    for firmware in release['firmwares']:
                        if firmware['name'] == firmware_name:
                            return firmware
                    return
            else:
                return

    def api_get(self, url):
        response = urlopen(url)
        v = response.read()
        try:
            return json.loads(v.decode('utf-8'))
        except ValueError as e:
            print(e)
            print("-=[begin:server returned:")
            print(v)
            print("-=[end:server returned:")
            return json.loads("{}".decode('utf-8'))

    def update(self):
        save = False
        page = 1
        while True:
            gh_repos = self.api_get('https://api.github.com/orgs/bigclownlabs/repos?page=%d' % page)
            if not gh_repos:
                break
            for gh_repo in gh_repos:
                if gh_repo['name'].startswith('bcf') and gh_repo['name'] != 'bcf-sdk-core-module':

                    repo = self._repos.get(gh_repo['name'], {'pushed_at': None, 'releases': [{'tag_name': None}]})
                    if repo['pushed_at'] != gh_repo['pushed_at']:

                        print('update data for repo', 'bigclownlabs/' + gh_repo['name'])

                        new_repo = {
                            'name': gh_repo['name'],
                            'pushed_at': gh_repo['pushed_at'],
                            'description': gh_repo['description'],
                            'tag': None
                        }

                        releases = []

                        for gh_release in self.api_get(gh_repo['releases_url'][:-5]):
                            release = None
                            for gh_assets in gh_release.get('assets', []):
                                if gh_assets['browser_download_url'].endswith(".bin"):
                                    if not release:
                                        release = {
                                            'tag_name': gh_release['tag_name'],
                                            'published_at': gh_release['published_at'],
                                            'firmwares': [],
                                            'prerelease': gh_release['prerelease']
                                        }

                                    release['firmwares'].append({
                                        'id': str(gh_assets['id']),
                                        'download_url': gh_assets['browser_download_url'],
                                        'size': gh_assets['size'],
                                        'name': gh_assets['name'],

                                    })

                                    if repo:
                                        self._updated.append(str(gh_assets['id']))

                            if release:
                                releases.append(release)

                        if releases:
                            if releases[0]['tag_name'] != repo['releases'][0]['tag_name']:
                                new_repo['releases'] = releases
                                self._repos[gh_repo['name']] = new_repo
                                save = True
            page += 1
        if save:
            with open(self._cache_repos, 'w') as fp:
                json.dump(self._repos, fp, sort_keys=True, indent=2)

            print('save to ', self._cache_repos)

    def clear(self):
        self._repos = {}
        if os.path.exists(self._cache_repos):
            os.unlink(self._cache_repos)

    def download_firmware(self, firmware_id):
        filename_bin = os.path.join(self._user_cache_dir, str(firmware_id) + '.bin')

        firmware = self.get_firmware(firmware_id)
        if not firmware:
            raise Exception("Firmware id not found")

        if not os.path.exists(filename_bin) or os.path.getsize(filename_bin) != firmware['size']:
            print('download firmware from', firmware['download_url'])
            print('save as', filename_bin)

            urlretrieve(firmware['download_url'], filename_bin)

        return filename_bin
