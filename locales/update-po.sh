#!/bin/bash
set -e

LOCALES_DIR="$(dirname "$0")"
DOMAIN="messages"

pybabel extract -F "$LOCALES_DIR/../babel.cfg" -o "$LOCALES_DIR/$DOMAIN.pot" "$LOCALES_DIR/.."

pybabel update -i "$LOCALES_DIR/$DOMAIN.pot" -d "$LOCALES_DIR"
pybabel compile -d "$LOCALES_DIR"

echo "Updated .po files and compiled .mo files for all languages."
