#!/bin/sh
# vim: set ts=4:
set -eu

VENV_DIR="$(pwd)/.venv"

die() {
	printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2
	shift
	printf '  %s\n' "$@"
	exit 2
}

einfo() {
	printf '\033[1;36m> %s\033[0m\n' "$@" >&2
}

if [ "$(id -u)" -eq 0 ] && [ "$ALLOW_ROOT" != 'yes' ]; then
	die 'Do not run this script as root!'
fi

pkgver_from_git() {
	local desc
	if desc="$(git describe --tags --exact-match --match 'v*' 2>/dev/null)"; then
		echo "${desc#v}" | sed 's/[_-]/~/g'
	elif desc="$(git describe --tags --match 'v*' 2>/dev/null)"; then
		echo "$desc" | sed -En 's/^v([^-]+).*/\1~dev/p'
	else
		return 1
	fi
}

set_version() {
	local ver="$(echo $PKG_VERSION | tr '~' '-')"
	sed -r -i'' "s/@@VERSION@@/$ver/g" "$1"
}

if [ -z "${PKG_VERSION:-}" ]; then
	PKG_VERSION="$(pkgver_from_git)" ||
		die '$PKG_VERSION is not set and could not determine version from git!'
fi

export PATH="$VENV_DIR/bin:$PATH"
unset PYTHONHOME

if [ -z "${TRAVIS_BUILD_DIR:-}" ]; then
    BUILD_DIR="$(pwd)/build"
    echo "$BUILD_DIR"
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    cp -r bcf "$BUILD_DIR"/bcf
    cp setup.py "$BUILD_DIR"/
    cp MANIFEST.in "$BUILD_DIR"/
    cp *.md "$BUILD_DIR"/
    cp LICENSE "$BUILD_DIR"/
    cp requirements.txt "$BUILD_DIR"/
    cd "$BUILD_DIR"
fi

ls -lha

set_version bcf/cli.py
set_version setup.py

python3 setup.py sdist
