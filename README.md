# astroquery-cli 🚀

A practical command-line interface (CLI) for selected [astroquery](https://astroquery.readthedocs.io/) modules, with basic autocompletion and multi-language support.

---

## Overview ✨

`astroquery-cli` provides command-line access to several astroquery data services, with support for Chinese and Japanese interfaces. The current features focus on core query commands; some advanced features are still under development.

---

## Supported Modules 🧩

- **ALMA**: Basic query
- **ESASky**: Sky region visualization queries
- **Gaia**: Cone search
- **IRSA**: Infrared Science Archive queries
- **Heasarc**: HEASARC Archive queries
- **JPL**: JPL Small-Body Database queries
- **MAST**: Mikulski Archive for Space Telescopes queries
- **ADS**: NASA Astrophysics Data System literature search and BibTeX retrieval, allows simple commands to search for "latest papers" or "highly cited reviews".
- **NED**: NASA/IPAC Extragalactic Database name resolution
- **NIST**: National Institute of Standards and Technology Atomic Spectra Database queries
- **Exoplanet**: NASA Exoplanet Archive queries
- **SDSS**: Sloan Digital Sky Survey queries
- **ESO**: European Southern Observatory queries
- **SIMBAD**: SIMBAD Astronomical Database basic query
- **Splatalogue**: Molecular line queries
- **VizieR**: VizieR Catalogue Database catalog search, basic query

_Some modules and commands are not fully implemented. Aliases are available for some modules (e.g., `sim` for `simbad`, `viz` for `vizier`, `spl` for `splatalogue`, `hea` for `heasarc`, `exo` for `exoplanet`). Please refer to `aqc --help` for the latest status._

---

## Features 🌟

- ⚡ Command autocompletion (manual installation required, see below)
- 🌏 Multi-language support (Simplified Chinese, Japanese; French in progress)
- 📊 Formatted output for query results

---

## Installation 🛠️

### From Source

```bash
git clone https://github.com/yourusername/astroquery-cli.git
cd astroquery-cli
pip install .
```

---

## Shell Autocompletion 🧑‍💻

Install shell autocompletion with:

```bash
aqc --install-completion bash   # Bash
aqc --install-completion zsh    # Zsh
aqc --install-completion fish   # Fish
```

---

## Usage 📚

### 1. View available modules and commands

```bash
aqc --help
aqc <module> --help
```

### 2. Basic query example

Query VizieR for a catalog:

```bash
aqc vizier find-catalogs --keywords "quasar"
aqc vizier query --catalog "VII/118" --ra 12.5 --dec 12.5 --radius 0.1
```

Query SIMBAD for an object:

```bash
aqc simbad query --identifier "M31"
```

Query ALMA for observations:

```bash
aqc alma query --ra 83.633 --dec -5.391 --radius 0.1
```

### 3. Change output language

```bash
aqc --lang zh simbad query --identifier "M31"
```

### 4. Test service connectivity

```bash
aqc --ping
```

### 5. Check available fields for a module

```bash
aqc --field simbad
```

**Common options:**

- `-l`, `--lang` : Set output language (e.g., 'en', 'zh')
- `-p`, `--ping` : Test connectivity to major services (top-level command only)
- `-f`, `--field` : Check field validity for modules (top-level command only)

---

## Internationalization 🌐

- Translation files are located in `locales/<lang>/LC_MESSAGES/messages.po` and compiled to `.mo` files

### Updating Translations

Helper scripts in the `locales/` directory assist with extracting, updating, and compiling translation files. The general workflow is as follows:

1.  **Extract untranslated entries**: Run `locales/extract-untranslated.sh`. This script generates `untranslated_pot.tmp` (for new entries in `messages.pot`) and `untranslated_<lang>.tmp` files (for untranslated entries in language-specific `.po` files).
2.  **Translate `untranslated_pot.tmp`**: Manually translate the entries in `locales/untranslated_pot.tmp`. These are new `msgid` entries that need to be added to all language files.
3.  **Merge translations**: After translating `untranslated_pot.tmp`, merge these translations into the respective `untranslated_<lang>.tmp` files. This step typically involves copying the translated `msgstr` from `untranslated_pot.tmp` to the corresponding entries in `untranslated_<lang>.tmp`.
4.  **Update `.po` files**: Run `locales/update-po.sh` to incorporate the translated entries from the `untranslated_<lang>.tmp` files into the `messages.po` files for each language.
5.  **Check for updates**: Run `locales/check-update.sh` to ensure all translation files are consistent and up-to-date.
6.  **Compile `.mo` files**: After updating `.po` files, compile them into `.mo` files using `locales/compile-mo.sh` (or similar command if not explicitly provided as a script).

Refer to the comments within each script in the `locales/` directory for more detailed instructions.

---

## License 📄

MIT License

---

## Acknowledgements 🙏

- [Astroquery](https://astroquery.readthedocs.io/)
- [Typer](https://typer.tiangolo.com/)
- [Rich](https://github.com/Textualize/rich)
