#!/bin/bash

set -e

REPO_PKG_NAME="python-astroquery-cli"

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

echo "Starting macOS packaging for $REPO_PKG_NAME version $PKG_VERSION"

# Clean up and create package directories
rm -rf ./pkg-macos
mkdir -p ./pkg-macos
PACKAGE_DIR="./pkg-macos/${REPO_PKG_NAME}-${PKG_VERSION}"
CONTENTS_DIR="${PACKAGE_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"
LIBDIR="${RESOURCES_DIR}/lib"

mkdir -p "${MACOS_DIR}"
mkdir -p "${LIBDIR}"

# Install wheel to package directory
echo "Installing wheel $WHEEL_FILE to ${LIBDIR}"
pip3 install --no-deps --target "${LIBDIR}" "$WHEEL_FILE"

# Create launcher script
echo "Creating launcher script at ${MACOS_DIR}/${CMD_NAME}"
cat > "${MACOS_DIR}/${CMD_NAME}" << EOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="\${SCRIPT_DIR}/../Resources/lib"
python3 -m ${MODULE_NAME}.main "\$@"
EOF
chmod +x "${MACOS_DIR}/${CMD_NAME}"

# Create Info.plist
PKG_DESCRIPTION=$(grep "^description" pyproject.toml | cut -d'"' -f2)
if [[ -z "$PKG_DESCRIPTION" ]]; then
    PKG_DESCRIPTION="Astroquery CLI application"
fi

cat > "${CONTENTS_DIR}/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>Astroquery CLI</string>
    <key>CFBundleExecutable</key>
    <string>${CMD_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.github.inoribea.${REPO_PKG_NAME}</string>
    <key>CFBundleName</key>
    <string>Astroquery CLI</string>
    <key>CFBundleShortVersionString</key>
    <string>${PKG_VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${PKG_VERSION}</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2023 inoribea</string>
</dict>
</plist>
EOF

# Create a README file
cat > "${PACKAGE_DIR}/README.md" << EOF
# ${REPO_PKG_NAME} ${PKG_VERSION}

## Installation

1. Copy the ${CMD_NAME} executable from the Contents/MacOS directory to a location in your PATH, such as:
   \`cp Contents/MacOS/${CMD_NAME} /usr/local/bin/${CMD_NAME}\`

2. Make sure it's executable:
   \`chmod +x /usr/local/bin/${CMD_NAME}\`

3. Run \`${CMD_NAME}\` from your terminal.

## Requirements

- Python 3.8 or later
- Required Python packages (will be automatically installed if missing):
  - typer
  - click
  - rich
  - astroquery
  - astropy
EOF

# Create a tarball
TARBALL_NAME="${REPO_PKG_NAME}-${PKG_VERSION}-macos.tar.gz"
echo "Creating tarball: ${TARBALL_NAME}"
(cd ./pkg-macos && tar -czf "../${TARBALL_NAME}" "${REPO_PKG_NAME}-${PKG_VERSION}")

if [ -f "${TARBALL_NAME}" ]; then
    echo "Successfully created macOS package: ${TARBALL_NAME}"
    echo "package_name=${TARBALL_NAME}" >> "$GITHUB_OUTPUT"
    echo "package_path=${TARBALL_NAME}" >> "$GITHUB_OUTPUT"
else
    echo "Error: Failed to create macOS package ${TARBALL_NAME}"
    echo "Current directory contents:"
    ls -l .
    exit 1
fi

