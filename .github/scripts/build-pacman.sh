#!/bin/bash
set -e

if [ -n "$PKG_VERSION_OVERRIDE" ]; then
    PKG_VERSION="$PKG_VERSION_OVERRIDE"
else
    PKG_VERSION=$(grep "^version" pyproject.toml | cut -d'"' -f2)
fi

PKG_NAME="python-astroquery-cli"
PKG_DESC="CLI for astroquery modules with autocompletion."
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

rm -rf ./pkg
PY_SITE_PACKAGES="./pkg/usr/lib/python${PY_VERSION}/site-packages"
mkdir -p "${PY_SITE_PACKAGES}"
mkdir -p ./pkg/usr/bin

pip3 install . --no-deps --target "${PY_SITE_PACKAGES}"

cat > ./pkg/usr/bin/aqc << EOF
#!/bin/bash
exec python3 -m astroquery_cli.main "\$@"
EOF

chmod +x ./pkg/usr/bin/aqc

PACMAN_VERSION=$(echo $PKG_VERSION | sed 's/-/_/g')

fpm -s dir -t pacman \
    -p "${PKG_NAME}-${PACMAN_VERSION}-1-x86_64.pkg.tar.zst" \
    -n "${PKG_NAME}" \
    -v "${PACMAN_VERSION}" \
    --iteration 1 \
    --architecture x86_64 \
    --description "${PKG_DESC}" \
    --maintainer "Developer <dev@example.com>" \
    --depends "python" \
    --depends "python-requests" \
    --depends "python-astroquery" \
    -C ./pkg \
    usr/

echo "package_name=${PKG_NAME}-${PACMAN_VERSION}-1-x86_64.pkg.tar.zst" >> $GITHUB_OUTPUT
echo "package_path=${PKG_NAME}-${PACMAN_VERSION}-1-x86_64.pkg.tar.zst" >> $GITHUB_OUTPUT
