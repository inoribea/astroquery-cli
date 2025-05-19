#!/bin/bash
set -e

if [ -n "$PKG_VERSION_OVERRIDE" ]; then
    PKG_VERSION="$PKG_VERSION_OVERRIDE"
else
    PKG_VERSION=$(grep "^version" pyproject.toml | cut -d'"' -f2)
fi

PKG_NAME="python-astroquery-cli"
DEB_PKG_NAME="python3-astroquery-cli"
PKG_DESC="CLI for astroquery modules with autocompletion."
MAINTAINER="Developer <dev@example.com>"
PYTHON_DEB_DEPENDS="python3, python3-requests, python3-astroquery"

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

PKG_ROOT="./pkg"
PY_DIST_PACKAGES="${PKG_ROOT}/usr/lib/python${PY_VERSION}/dist-packages"
BIN_DIR="${PKG_ROOT}/usr/bin"

rm -rf "$PKG_ROOT"
mkdir -p "$PY_DIST_PACKAGES" "$BIN_DIR"

pip3 install . --no-deps --target "$PY_DIST_PACKAGES"

cat > "${BIN_DIR}/aqc" << EOF
#!/bin/bash
exec python3 -m astroquery_cli.main "\$@"
EOF

chmod +x "${BIN_DIR}/aqc"

DEB_VERSION=$(echo $PKG_VERSION | sed 's/-/+/g')

fpm -s dir -t deb \
    -p "${DEB_PKG_NAME}_${DEB_VERSION}_all.deb" \
    -n "$DEB_PKG_NAME" \
    -v "$DEB_VERSION" \
    --iteration 1 \
    --architecture all \
    --description "$PKG_DESC" \
    --maintainer "$MAINTAINER" \
    --depends "python3" \
    --depends "python3-requests" \
    --depends "python3-astroquery" \
    -C "$PKG_ROOT" \
    usr/

# 输出结果给 Github Actions
echo "package_name=${DEB_PKG_NAME}_${DEB_VERSION}_all.deb" >> $GITHUB_OUTPUT
echo "package_path=${DEB_PKG_NAME}_${DEB_VERSION}_all.deb" >> $GITHUB_OUTPUT
