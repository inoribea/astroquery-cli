#!/bin/bash
set -e

# If PKG_VERSION_OVERRIDE is provided, use it, otherwise use version from pyproject.toml
if [ -n "$PKG_VERSION_OVERRIDE" ]; then
    PKG_VERSION="$PKG_VERSION_OVERRIDE"
    echo "Using PKG_VERSION from environment: $PKG_VERSION"
else
    PKG_VERSION=$(grep "^version" pyproject.toml | cut -d'"' -f2)
    echo "Using PKG_VERSION from pyproject.toml: $PKG_VERSION"
fi

echo "Starting packaging for python-astroquery-cli version $PKG_VERSION"

# Detect Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python version for packaging: $PYTHON_VERSION"

# Ensure wheel file is available
if [ -n "$WHEEL_FILENAME_ENV" ]; then
    WHEEL_FILE="dist/$WHEEL_FILENAME_ENV"
    echo "Expecting wheel file at: $WHEEL_FILE"
else
    WHEEL_FILE=$(ls dist/*-py3-none-any.whl 2>/dev/null | head -n 1)
    if [ -z "$WHEEL_FILE" ]; then
        echo "Error: No wheel file found in dist/ directory"
        exit 1
    fi
    echo "Found wheel file: $WHEEL_FILE"
fi

# Verify the wheel file exists
if [ ! -f "$WHEEL_FILE" ]; then
    echo "Error: Wheel file $WHEEL_FILE not found"
    exit 1
fi

echo "Using wheel file: $WHEEL_FILE"

# Create directories for installation
mkdir -p ./pkg/usr/lib/python${PYTHON_VERSION}/site-packages
mkdir -p ./pkg/usr/bin

# Install the wheel into the package directory
echo "Installing wheel $WHEEL_FILE to ./pkg/usr/lib/python${PYTHON_VERSION}/site-packages"
pip install --target=./pkg/usr/lib/python${PYTHON_VERSION}/site-packages "$WHEEL_FILE"

# Create the launcher script
echo "Creating launcher script at ./pkg/usr/bin/aqc"
cat > ./pkg/usr/bin/aqc << 'EOF'
#!/bin/bash
exec python -m astroquery_cli "$@"
EOF
chmod +x ./pkg/usr/bin/aqc

# Prepare package metadata
PKG_NAME="python-astroquery-cli"
PKG_DESC="CLI for astroquery modules with autocompletion."
echo "Using package description: $PKG_DESC"

# Create pacman-safe version (replace dashes in version with underscores for pacman)
PACMAN_VERSION=$(echo $PKG_VERSION | sed 's/-/_/g')

# Build the package
echo "Building Pacman package: ${PKG_NAME}-${PACMAN_VERSION}-1-x86_64.pkg.tar.zst"
sudo apt-get update && sudo apt-get install -y libarchive-tools

# Build the package with FPM
fpm -s dir -t pacman \
    -p "${PKG_NAME}-${PACMAN_VERSION}-1-x86_64.pkg.tar.zst" \
    -n "${PKG_NAME}" \
    -v "${PACMAN_VERSION}" \
    --iteration 1 \
    --architecture x86_64 \
    --description "${PKG_DESC}" \
    --maintainer "Developer <dev@example.com>" \
    -C ./pkg \
    usr/

# Set output variables for GitHub Actions
echo "package_name=${PKG_NAME}-${PACMAN_VERSION}-1-x86_64.pkg.tar.zst" >> $GITHUB_OUTPUT
echo "package_path=${PKG_NAME}-${PACMAN_VERSION}-1-x86_64.pkg.tar.zst" >> $GITHUB_OUTPUT

