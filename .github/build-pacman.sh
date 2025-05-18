#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status.

PKG_NAME="python-astroquery-cli"
# Use PKG_VERSION_OVERRIDE from environment if set, otherwise fallback to pyproject.toml
if [[ -n "$PKG_VERSION_OVERRIDE" ]]; then
  PKG_VERSION="$PKG_VERSION_OVERRIDE"
  echo "Using PKG_VERSION from environment: $PKG_VERSION"
else
  PKG_VERSION=$(grep "^version" pyproject.toml | cut -d'"' -f2)
  echo "Using PKG_VERSION from pyproject.toml: $PKG_VERSION"
fi

MODULE_NAME="astroquery_cli"  # Actual Python module name
CMD_NAME="aqc"  # Concise command name

# Ensure PKG_VERSION is set
if [[ -z "$PKG_VERSION" ]]; then
  echo "Error: PKG_VERSION is not set."
  exit 1
fi

echo "Starting packaging for $PKG_NAME version $PKG_VERSION"

# Clean up and create packaging directory
rm -rf ./pkg
mkdir -p ./pkg

# Determine Python version for paths
PYTHON_VERSION_DETECTED=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python version for packaging: $PYTHON_VERSION_DETECTED"

PY_SITEPACKAGES_DIR="./pkg/usr/lib/python${PYTHON_VERSION_DETECTED}/site-packages"
PY_BIN_DIR="./pkg/usr/bin"

mkdir -p "${PY_SITEPACKAGES_DIR}"
mkdir -p "${PY_BIN_DIR}"

# Find the built wheel file. Assumes it's in ./dist/
# Wheel name pattern: ${MODULE_NAME}-${PKG_VERSION}-py3-none-any.whl
# Example: astroquery_cli-0.1.0-py3-none-any.whl
WHEEL_FILE_PATTERN="dist/${MODULE_NAME}-${PKG_VERSION}-py3-none-any.whl"
WHEEL_FILE=$(ls $WHEEL_FILE_PATTERN 2>/dev/null | head -n 1)

if [[ ! -f "$WHEEL_FILE" ]]; then
  echo "Warning: Wheel file matching pattern '$WHEEL_FILE_PATTERN' not found."
  echo "Attempting to find a more generic wheel for ${MODULE_NAME} with version ${PKG_VERSION}..."
  WHEEL_FILE=$(ls dist/${MODULE_NAME}-${PKG_VERSION}-*.whl 2>/dev/null | head -n 1)
  if [[ ! -f "$WHEEL_FILE" ]]; then
    echo "Error: Could not find any wheel file for ${MODULE_NAME} with version ${PKG_VERSION} in dist/ directory."
    echo "Contents of dist/ directory:"
    ls -Rla dist/
    exit 1
  fi
  echo "Found wheel file using alternative pattern: $WHEEL_FILE"
fi
echo "Using wheel file: $WHEEL_FILE"

# Install wheel to target directory
echo "Installing wheel $WHEEL_FILE to ${PY_SITEPACKAGES_DIR}"
pip install --no-deps --target "${PY_SITEPACKAGES_DIR}" "$WHEEL_FILE"

# Create concise launcher script
echo "Creating launcher script at ${PY_BIN_DIR}/${CMD_NAME}"
cat > "${PY_BIN_DIR}/${CMD_NAME}" << EOF
#!/bin/sh
# Launches the application using the Python version it was packaged with.
exec python${PYTHON_VERSION_DETECTED} -m ${MODULE_NAME}.main "\$@"
EOF
chmod +x "${PY_BIN_DIR}/${CMD_NAME}"

# Extract description from pyproject.toml, with a fallback
PKG_DESCRIPTION=$(grep "^description" pyproject.toml | cut -d'"' -f2)
if [[ -z "$PKG_DESCRIPTION" ]]; then
    echo "Warning: Description not found in pyproject.toml. Using a default description."
    PKG_DESCRIPTION="Astroquery CLI application"
fi
echo "Using package description: $PKG_DESCRIPTION"

# FPM packaging parameters
PKG_RELEASE="1" # Arch Linux package release number
PKG_EPOCH="0"   # Arch Linux package epoch
ARCH="x86_64"   # Target architecture

# Define the expected output filename for verification and GitHub Actions output
EXPECTED_FPM_OUTPUT_NAME="${PKG_NAME}-${PKG_VERSION}-${PKG_RELEASE}-${ARCH}.pkg.tar.zst"

echo "Building Pacman package: $EXPECTED_FPM_OUTPUT_NAME"

# Use FPM to create the package
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

# Verify package creation and set outputs for GitHub Actions
if [ -f "$EXPECTED_FPM_OUTPUT_NAME" ]; then
    echo "Successfully created Pacman package: ${EXPECTED_FPM_OUTPUT_NAME}"
    echo "package_name=${EXPECTED_FPM_OUTPUT_NAME}" >> "$GITHUB_OUTPUT"
    echo "package_path=${EXPECTED_FPM_OUTPUT_NAME}" >> "$GITHUB_OUTPUT" # Path is just the name in current dir
else
    echo "Error: Expected package file ${EXPECTED_FPM_OUTPUT_NAME} not found after FPM run."
    echo "Current directory contents:"
    ls -l .
    exit 1
fi


