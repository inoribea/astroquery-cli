#!/bin/bash

set -e 

PKG_NAME="python-astroquery-cli"
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

echo "Starting packaging for $PKG_NAME version $PKG_VERSION"


rm -rf ./pkg
mkdir -p ./pkg

PYTHON_VERSION_DETECTED=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python version for packaging: $PYTHON_VERSION_DETECTED"

PY_SITEPACKAGES_DIR="./pkg/usr/lib/python${PYTHON_VERSION_DETECTED}/site-packages"
PY_BIN_DIR="./pkg/usr/bin"

mkdir -p "${PY_SITEPACKAGES_DIR}"
mkdir -p "${PY_BIN_DIR}"

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

echo "Installing wheel $WHEEL_FILE to ${PY_SITEPACKAGES_DIR}"
pip install --no-deps --target "${PY_SITEPACKAGES_DIR}" "$WHEEL_FILE"

echo "Creating launcher script at ${PY_BIN_DIR}/${CMD_NAME}"
cat > "${PY_BIN_DIR}/${CMD_NAME}" << EOF

#!/bin/sh

exec python${PYTHON_VERSION_DETECTED} -m ${MODULE_NAME}.main "\$@"
EOF
chmod +x "${PY_BIN_DIR}/${CMD_NAME}"

PKG_DESCRIPTION=$(grep "^description" pyproject.toml | cut -d'"' -f2)
if [[ -z "$PKG_DESCRIPTION" ]]; then
    echo "Warning: Description not found in pyproject.toml. Using a default description."
    PKG_DESCRIPTION="Astroquery CLI application"
fi
echo "Using package description: $PKG_DESCRIPTION"

PKG_RELEASE="1" 
PKG_EPOCH="0"   
ARCH="x86_64"   

EXPECTED_FPM_OUTPUT_NAME="${PKG_NAME}-${PKG_VERSION}-${PKG_RELEASE}-${ARCH}.pkg.tar.zst"

echo "Building Pacman package: $EXPECTED_FPM_OUTPUT_NAME"

fpm -s dir -t pacman \
    -n "${PKG_NAME}" \
    -v "${PKG_VERSION}" \
    --epoch "${PKG_EPOCH}" \
    --iteration "${PKG_RELEASE}" \
    --architecture "${ARCH}" \
    --description "${PKG_DESCRIPTION}" \
    --maintainer "inoribea <inoribea@outlook.com>" \
    --url "https://github.com/inoribea/${PKG_NAME}" \
    --license "MIT" \
    --depends "python>=3.8" \
    --depends "python-typer" \
    --depends "python-click" \
    --depends "python-rich" \
    --depends "python-astroquery" \
    --depends "python-astropy" \
    --pacman-compression zstd \
    -C ./pkg \
    usr

if [ -f "$EXPECTED_FPM_OUTPUT_NAME" ]; then
    echo "Successfully created Pacman package: ${EXPECTED_FPM_OUTPUT_NAME}"
    echo "package_name=${EXPECTED_FPM_OUTPUT_NAME}" >> "$GITHUB_OUTPUT"
    echo "package_path=${EXPECTED_FPM_OUTPUT_NAME}" >> "$GITHUB_OUTPUT" 
else
    echo "Error: Expected package file ${EXPECTED_FPM_OUTPUT_NAME} not found after FPM run."
    echo "Current directory contents:"
    ls -l .
    exit 1
fi

