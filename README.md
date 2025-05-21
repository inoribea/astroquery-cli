# astroquery-cli

A command-line interface (CLI) for [astroquery](https://astroquery.readthedocs.io/) modules, with autocompletion and multi-language support.

---

## Features

- Unified CLI for querying multiple astronomical data services (ALMA, Gaia, MAST, NED, SIMBAD, VizieR, IRSA, TAP, SIA, SSA, SCS, VO Registry, VO Table, etc.)
- Autocompletion for commands and options (see below for installation)
- Internationalization (i18n): supports Chinese, French, Japanese
- Output formatting with [rich](https://github.com/Textualize/rich)
- Easy packaging for Linux (wheel, deb, rpm, pacman) and Windows

---

## Installation

### From PyPI (when available)

```bash
pip install astroquery-cli
```

### From Source

```bash
git clone https://github.com/yourusername/astroquery-cli.git
cd astroquery-cli
pip install .
```

Or build a wheel:

```bash
pip install poetry
poetry build
pip install dist/astroquery_cli-*.whl
```

---

## Shell Autocompletion

To enable shell autocompletion for `aqc`, run:

**Bash:**
```bash
aqc --install-completion bash
```

**Zsh:**
```bash
aqc --install-completion zsh
```

**Fish:**
```bash
aqc --install-completion fish
```

Restart your shell or source the printed script to activate completion.

---

## Usage

```bash
aqc --help
aqc <module> <command> [options]
```

### Common Options

- `-d`, `--default` : Set the default language for this session (e.g., 'en', 'zh'). 
- `-l`, `--lang` : Set the language for output messages (e.g., 'en', 'zh'). 
- `-p`, `--ping` : Test connectivity to major services (only available at top-level command). 
- `-f`, `--field` : Test field validity for modules (only available at top-level command).
- `--install-completion` ：Install completion for the current shell.    
---

## Internationalization (i18n)

- **Chinese (简体中文)**: All CLI messages and help texts are available in Simplified Chinese.
- **French (Français)**: All CLI messages and help texts are available in French.
- **Japanese (日本語)**: All CLI messages and help texts are available in Japanese.
- Language files are in `locales/<lang>/LC_MESSAGES/messages.po` and compiled to `.mo` files.
- Only compiled `.mo` files are included in the package.

### Update or Add Translations

You can update and compile translations in **two ways**:

**1. Manual pybabel commands**

- Extract new messages and update translation files:
  ```bash
  pybabel extract -F babel.cfg -o locales/messages.pot .
  pybabel update -i locales/messages.pot -d locales
  ```
- Edit the `.po` files in `locales/*` as needed.
- Compile translations:
  ```bash
  pybabel compile -d locales
  ```

**2. Use project helper scripts**

`locales/` directory contains the following scripts for translation workflow:

#### 1. update-po.sh

Extracts translatable strings from the source code and updates all `.po` files using the template.

```bash
bash locales/update-po.sh
```

#### 2. extract-untranslated.sh

Extracts untranslated strings from each `.po` file and generates `untranslated_*.tmp` files for easier collaborative translation.

```bash
bash locales/extract-untranslated.sh
```

#### 3. check-update.sh

Applies translations from `untranslated_*.tmp` files back into the corresponding `.po` files for batch translation updates.
Then Compiled all .po files to .mo files.

```bash
bash locales/check-update.sh
```

#### 4. clean-dedupe.sh

Cleans and deduplicates translation entries in `.po` files.

```bash
bash locales/clean-dedupe.sh
```
**Do not forget to delete entries that may be marked with #, fuzzy, and do not delete the example entries.**

## Modules and Languages

### ALMA
- [x] query
- [ ] advanced options

### Gaia
- [x] cone-search
- [ ] cross-match

### MAST
- [x] query
- [ ] download

### NED
- [x] name-resolve
- [ ] batch-query

### SIMBAD
- [x] query
- [ ] custom-fields

### VizieR
- [x] find-catalogs
- [x] query
- [ ] advanced search

### IRSA
- [ ] query

### TAP
- [x] query

### SIA
- [ ] query

### SSA
- [ ] query

### SCS
- [ ] query

### VO Registry
- [ ] search

### VO Table
- [ ] parse

### Languages
- [x] zh-CN
- [x] ja-JP
- [ ] fr-FR
---

## Development

### Project Structure

```
astroquery_cli/         # Main CLI package
  modules/              # Submodules for each data service
  i18n.py               # i18n utilities
  main.py               # CLI entrypoint
  utils.py              # Shared utilities
locales/                # Translation files (.po/.mo), scripts
.github/                # CI/CD workflows and packaging scripts
pyproject.toml          # Poetry configuration
```

### Running Tests

```bash
pytest
```

### Building Packages

- Wheel: `poetry build`
- Other formats: see `.github/workflows/build-package.yml`

---

## TODO

- [ ] ALMA: implement advanced query options and output formatting
- [ ] Gaia: add cross-match and batch cone search
- [ ] MAST: implement download and filtering
- [ ] NED: add batch query support
- [ ] SIMBAD: support custom output fields
- [ ] VizieR: enhance advanced search and result parsing
- [ ] IRSA: implement query command
- [ ] TAP: add more query options
- [ ] SIA/SSA/SCS: implement query commands
- [ ] VO Registry: implement search
- [ ] VO Table: implement parsing
- [ ] Add unit tests for each module's CLI commands
- [ ] Expand i18n coverage and keep translations up to date (zh, fr, ja)
- [ ] Improve error handling and user feedback in all modules
- [ ] Refactor shared utilities for code reuse across modules

---

## License

MIT License (see `LICENSE` file).

---

## Acknowledgements

- [Astroquery](https://astroquery.readthedocs.io/) developers
- [Typer](https://typer.tiangolo.com/) team
- [Rich](https://github.com/Textualize/rich) for output formatting