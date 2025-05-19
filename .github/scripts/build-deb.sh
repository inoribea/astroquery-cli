#!/bin/bash

set -e

REPO_PKG_NAME="python-astroquery-cli"
DEB_PKG_NAME="python3-astroquery-cli"

if [[ -n "$PKG_VERSION_OVERRIDE" ]]; then
  PKG_VERSION="$PKG_VERSION_OVERRIDE"
  echo "Using PKG_VERSION from environment: $PKG_VERSION"
else
  PKG_VERSION=$(grep "^version" pyproject.toml | cut -d'"' -f2)
  echo "Using PKG_VERSION from pyproject.toml: $PKG_VERSION"
fi

MODULE_NAME="astroquery_cli"
CMD_NAME="aqc"

if [[ -z "$PKG_VERSION" ]]; then
  echo "Error: PKG_VERSION is not set."
  exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

rm -rf ./pkg-deb
PY_DISTPACKAGES_DIR="./pkg-deb/usr/lib/python${PYTHON_VERSION}/dist-packages"
PY_BIN_DIR="./pkg-deb/usr/bin"
mkdir -p "${PY_DISTPACKAGES_DIR}"
mkdir -p "${PY_BIN_DIR}"

pip3 install . --no-deps --target "${PY_DISTPACKAGES_DIR}"

cat
