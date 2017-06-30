import os
import json

try:
    from urllib import urlopen, urlretrieve
except ImportError:  # Python 3
    from urllib.request import urlopen, urlretrieve

__version__ = '@@VERSION@@'


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

    def get_firmwares_table(self, search='', all=False, description=False):
        table = []
        names = list(self._repos.keys())
        names.sort()
        for name in names:
            repo = self._repos[name]
            if not search or search in name or (description and search in repo['description']):
                for release in repo['releases']:
                    for i, firmware in enumerate(release['firmwares']):
                        n = 'bigclownlabs/' + name + ':' + firmware['name'] + ':' + release['tag_name']
                        row = [n]

                        if description:
                            row.append(repo['description'])
                        table.append(row)
                    if not all:
                        break
        return table

    def get_firmwares(self):
        table = []
        names = list(self._repos.keys())
        names.sort()
        for name in names:
            repo = self._repos[name]
            for release in repo['releases']:
                for i, firmware in enumerate(release['firmwares']):
                    table.append('bigclownlabs/' + name + ':' + firmware['name'])
                    break
        return table

    def get_firmware(self, name):
        name = name.split('/', 1)

        if len(name) != 2 or name[0] != 'bigclownlabs':
            return

        name = name[1].split(':')

        tag_name = None
        if len(name) == 2:
            tag_name = 'latest'
        elif len(name) == 3:
            tag_name = name[2]
        else:
            return

        firmware_name = name[1]

        repo = self._repos.get(name[0], None)
        if repo is None:
            return

        for release in repo['releases']:
            if tag_name == 'latest' or tag_name == release['tag_name']:
                for firmware in release['firmwares']:
                    if firmware['name'] == firmware_name:
                        return firmware
                return

    def api_get(self, url):
        response = urlopen(url)
        return json.loads(response.read().decode('utf-8'))

    def update(self):
        save = False
        for gh_repo in self.api_get('https://api.github.com/orgs/bigclownlabs/repos'):
            if gh_repo['name'].startswith('bcf') and gh_repo['name'] != 'bcf-sdk-core-module':

                repo = self._repos.get(gh_repo['name'], None)
                if not repo or repo['updated_at'] != gh_repo['updated_at']:
                    save = True

                    print('update data for repo', gh_repo['name'])

                    self._repos[gh_repo['name']] = {
                        'name': gh_repo['name'],
                        'updated_at': gh_repo['updated_at'],
                        'description': gh_repo['description'],
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
                                        'firmwares': []
                                    }

                                release['firmwares'].append({
                                    'id': str(gh_assets['id']),
                                    'download_url': gh_assets['browser_download_url'],
                                    'size': gh_assets['size'],
                                    'name': gh_assets['name']
                                })

                                if repo:
                                    self._updated.append(str(gh_assets['id']))

                        if release:
                            releases.append(release)

                    self._repos[gh_repo['name']]['releases'] = releases

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
