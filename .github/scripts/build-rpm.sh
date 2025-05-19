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

# Expect wheel file
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

# Create RPM-safe version (replace dashes with underscores for RPM)
RPM_VERSION=$(echo $PKG_VERSION | sed 's/-/_/g')

# RPM package name
PKG_NAME="python3-astroquery-cli"
echo "Starting RPM packaging for $PKG_NAME version $PKG_VERSION"

# Detect Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python version for packaging: $PYTHON_VERSION"

# Create directories for installation
mkdir -p ./pkg-rpm/usr/lib/python${PYTHON_VERSION}/site-packages
mkdir -p ./pkg-rpm/usr/bin

# Install the wheel into the package directory
echo "Installing wheel $WHEEL_FILE to ./pkg-rpm/usr/lib/python${PYTHON_VERSION}/site-packages"
pip install --target=./pkg-rpm/usr/lib/python${PYTHON_VERSION}/site-packages "$WHEEL_FILE"

# Create the launcher script
echo "Creating launcher script at ./pkg-rpm/usr/bin/aqc"
cat > ./pkg-rpm/usr/bin/aqc << 'EOF'
#!/bin/bash
exec python3 -m astroquery_cli "$@"
EOF
chmod +x ./pkg-rpm/usr/bin/aqc

# Package description
PKG_DESC="CLI for astroquery modules with autocompletion."
echo "Using package description: $PKG_DESC"

# Build the package
echo "Building RPM package for $PKG_NAME version $PKG_VERSION"
fpm -s dir -t rpm \
    -p "${PKG_NAME}-${RPM_VERSION}-1.x86_64.rpm" \
    -n "${PKG_NAME}" \
    -v "${RPM_VERSION}" \
    --iteration 1 \
    --architecture x86_64 \
    --description "${PKG_DESC}" \
    --maintainer "Developer <dev@example.com>" \
    -C ./pkg-rpm \
    usr/

# Verify the package was created
ls -l "${PKG_NAME}-${RPM_VERSION}-1.x86_64.rpm" || { echo "Error: RPM package not created"; exit 1; }

# Set output variables for GitHub Actions
echo "package_name=${PKG_NAME}-${RPM_VERSION}-1.x86_64.rpm" >> $GITHUB_OUTPUT
echo "package_path=${PKG_NAME}-${RPM_VERSION}-1.x86_64.rpm" >> $GITHUB_OUTPUT

