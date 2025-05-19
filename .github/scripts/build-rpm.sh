#!/bin/bash
set -e

if [ -n "$PKG_VERSION_OVERRIDE" ]; then
    PKG_VERSION="$PKG_VERSION_OVERRIDE"
else
    PKG_VERSION=$(grep "^version" pyproject.toml | cut -d'"' -f2)
fi

PKG_NAME="python3-astroquery-cli"
PKG_DESC="CLI for astroquery modules with autocompletion."
RPM_VERSION=$(echo $PKG_VERSION | sed 's/-/_/g')

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

rm -rf ./pkg-rpm
PY_SITE_PACKAGES="./pkg-rpm/usr/lib/python${PYTHON_VERSION}/site-packages"
mkdir -p "${PY_SITE_PACKAGES}"
mkdir -p ./pkg-rpm/usr/bin

pip3 install . --no-deps --target "${PY_SITE_PACKAGES}"

cat > ./pkg-rpm/usr/bin/aqc << EOF
#!/bin/bash
exec python3 -m astroquery_cli.main "\$@"
EOF

chmod +x ./pkg-rpm/usr/bin/aqc

fpm -s dir -t rpm \
    -p "${PKG_NAME}-${RPM_VERSION}-1.x86_64.rpm" \
    -n "${PKG_NAME}" \
    -v "${RPM_VERSION}" \
    --iteration 1 \
    --architecture x86_64 \
    --description "${PKG_DESC}" \
    --maintainer "Developer <dev@example.com>" \
    --depends "python3" \
    --depends "python3-requests" \
    --depends "python3-astroquery" \
    -C ./pkg-rpm \
    usr/

echo "package_name=${PKG_NAME}-${RPM_VERSION}-1.x86_64.rpm" >> $GITHUB_OUTPUT
echo "package_path=${PKG_NAME}-${RPM_VERSION}-1.x86_64.rpm" >> $GITHUB_OUTPUT
