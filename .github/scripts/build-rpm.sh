#!/bin/bash

set -e

REPO_PKG_NAME="python-astroquery-cli"
RPM_PKG_NAME="python3-astroquery-cli"

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

if [[ -z "$WHEEL_FILENAME_ENV" ]]; then
  echo "Error: WHEEL_FILENAME_ENV environment variable is not set."
  exit 1
fi

WHEEL_FILE="dist/${WHEEL_FILENAME_ENV}"
echo "Expecting wheel file at: $WHEEL_FILE"

if [[ ! -f "$WHEEL_FILE" ]]; then
  echo "Error: Wheel file '$WHEEL_FILE' not found in dist/ directory."
  echo "Contents of dist/ directory:"
  ls -Rla dist/
  exit 1
fi
echo "Using wheel file: $WHEEL_FILE"

echo "Starting RPM packaging for $RPM_PKG_NAME version $PKG_VERSION"

rm -rf ./pkg-rpm
mkdir -p ./pkg-rpm

PYTHON_VERSION_DETECTED=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python version for packaging: $PYTHON_VERSION_DETECTED"

# RPM typically uses site-packages
PY_SITEPACKAGES_DIR="./pkg-rpm/usr/lib/python${PYTHON_VERSION_DETECTED}/site-packages"
PY_BIN_DIR="./pkg-rpm/usr/bin"

mkdir -p "${PY_SITEPACKAGES_DIR}"
mkdir -p "${PY_BIN_DIR}"

echo "Installing wheel $WHEEL_FILE to ${PY_SITEPACKAGES_DIR}"
pip3 install --no-deps --target "${PY_SITEPACKAGES_DIR}" "$WHEEL_FILE"

echo "Creating launcher script at ${PY_BIN_DIR}/${CMD_NAME}"
cat > "${PY_BIN_DIR}/${CMD_NAME}" << EOF
#!/bin/sh
exec python3 -m ${MODULE_NAME}.main "\$@"
EOF
chmod +x "${PY_BIN_DIR}/${CMD_NAME}"

PKG_DESCRIPTION=$(grep "^description" pyproject.toml | cut -d'"' -f2)
if [[ -z "$PKG_DESCRIPTION" ]]; then
    PKG_DESCRIPTION="Astroquery CLI application"
fi
echo "Using package description: $PKG_DESCRIPTION"

echo "Building RPM package for $RPM_PKG_NAME version $PKG_VERSION"

# RPM-specific variables
RPM_RELEASE="1"
ARCH="x86_64"

fpm -s dir -t rpm \
    -n "${RPM_PKG_NAME}" \
    -v "${PKG_VERSION}" \
    --architecture "${ARCH}" \
    --description "${PKG_DESCRIPTION}" \
    --maintainer "inoribea <inoribea@outlook.com>" \
    --url "https://github.com/inoribea/${REPO_PKG_NAME}" \
    --license "MIT" \
    --rpm-digest sha256 \
    --rpm-os linux \
    --iteration "${RPM_RELEASE}" \
    --depends "python3 >= 3.8" \
    --depends "python3-typer" \
    --depends "python3-click" \
    --depends "python3-rich" \
    --depends "python3-astroquery" \
    --depends "python3-astropy" \
    -C ./pkg-rpm \
    usr

GENERATED_RPM_FILE=$(ls ${RPM_PKG_NAME}-${PKG_VERSION}-*.rpm 2>/dev/null | head -n 1)

if [ -f "$GENERATED_RPM_FILE" ]; then
    echo "Successfully created RPM package: ${GENERATED_RPM_FILE}"
    echo "package_name=${GENERATED_RPM_FILE}" >> "$GITHUB_OUTPUT"
    echo "package_path=${GENERATED_RPM_FILE}" >> "$GITHUB_OUTPUT"
else
    echo "Error: Expected RPM package file not found after FPM run."
    echo "Looking for pattern: ${RPM_PKG_NAME}-${PKG_VERSION}-*.rpm"
    echo "Current directory contents:"
    ls -l .
    exit 1
fi

