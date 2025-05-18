
# astroquery-cli 

[![PyPI version](https://badge.fury.io/py/astroquery-cli.svg)](https://badge.fury.io/py/astroquery-cli)
[![Python Version](https://img.shields.io/pypi/pyversions/astroquery-cli.svg)](https://pypi.org/project/astroquery-cli/)
<!-- Add other badges like license, build status if you have them -->

**Astroquery Command Line Interface (aqc)** provides convenient command-line access to various astronomical data services powered by the [Astroquery](https://astroquery.readthedocs.io/) Python package. This tool is built using [Typer](https://typer.tiangolo.com/) and supports internationalization for a user-friendly experience in multiple languages.

## Features

*   **Access to Multiple Astronomical Services:** Query well-known astronomical databases and archives directly from your terminal.
*   **Modular Design:** Each Astroquery service is implemented as a subcommand.
*   **User-Friendly CLI:** Powered by Typer, offering helpful messages, auto-completion (shell-dependent), and clear command structures.
*   **Internationalization (i18n):** Supports multiple languages for UI messages and help text. Current translations include English, French (fr), Japanese (ja), and Simplified Chinese (zh).
*   **Easy Language Switching:** Change the interface language on-the-fly using the `--lang` option.

## Installation

You can install `astroquery-cli` using pip:

```bash
pip install astroquery-cli
```

Alternatively, for development or to install from source:

```bash
git clone https://your-repo-url/astroquery-cli.git
cd astroquery-cli
poetry install
# or with pip:
# pip install .
```

## Dependencies

*   **Astroquery:** The core library providing access to astronomical services.
*   **Typer:** For building the command-line interface.
*   Other common scientific Python packages (Astropy, NumPy, Pandas, etc., usually as dependencies of Astroquery).
*   **Babel:** For internationalization (required for adding/updating translations).

## Usage

The basic command structure is:

```bash
aqc [OPTIONS] COMMAND [ARGS]...
```

Or, if you have a shell alias or it's directly on your PATH, you might use `astroquery-cli` instead of `aqc`.

**Getting Help:**

*   For a list of all available services (main commands):
    ```bash
    aqc --help
    ```
*   For help with a specific service (e.g., `simbad`):
    ```bash
    aqc simbad --help
    ```
*   For help with a specific command within a service (e.g., `query-object` in `simbad`):
    ```bash
    aqc simbad query-object --help
    ```

**Changing Language:**

Use the `-l` or `--lang` option to specify the language for the interface and output. This option can be used with any command.

```bash
aqc --lang <language_code> <service> <command> [arguments]
```

Example: Querying M31 using Simbad with output in Simplified Chinese:

```bash
aqc --lang zh simbad query-object M31
```

To see which language is currently active:
```bash
aqc --lang <language_code>
# Example:
aqc --lang fr
# Output: Language active: fr
#         Run 'aqc --help' or 'aqc -h' to see available commands.
```
The language preference can also be set using the `AQ_LANG` environment variable.

## Supported Astroquery Services

`astroquery-cli` currently provides command-line interfaces for the following Astroquery modules:

*   **`alma`**: Query the ALMA (Atacama Large Millimeter/submillimeter Array) archive.
*   **`esasky`**: Query the ESA Sky archive.
*   **`gaia`**: Query the Gaia archive.
*   **`irsa`**: Query NASA/IPAC Infrared Science Archive (IRSA).
*   **`irsa_dust`**: Query IRSA dust maps.
*   **`jplhorizons`**: Query JPL Horizons ephemeris service for solar system objects.
*   **`jplsbdb`**: Query JPL Small-Body Database (SBDB).
*   **`mast`**: Query the Mikulski Archive for Space Telescopes (MAST) (e.g., Hubble, TESS, JWST).
*   **`nasa_ads`**: Query the NASA Astrophysics Data System (ADS).
*   **`ned`**: Query the NASA/IPAC Extragalactic Database (NED).
*   **`simbad`**: Query the SIMBAD astronomical database.
*   **`splatalogue`**: Query the Splatalogue spectral line database.
*   **`vizier`**: Query the VizieR astronomical catalog service.

Example: Querying Simbad for object 'M31':

```bash
aqc simbad query-object M31
```

Example: Getting ephemerides for Mars from JPL Horizons:

```bash
aqc jplhorizons query-object Mars --epochs "2024-01-01" --location "@sun"
```

## Contributing

Contributions are welcome, especially for adding new features, fixing bugs, or improving translations!

### Internationalization (i18n) - Adding/Updating Translations

This project uses `PyBabel` for handling translations. The translatable strings are defined in the Python code (e.g., `_("Some text")`).

**Prerequisites:**
Ensure `Babel` is installed:
```bash
pip install Babel
```

**Workflow for adding a new language or updating existing translations:**

1.  **Extract Translatable Strings:**
    This command scans the source code (as defined in `babel.cfg`) and creates/updates a template file `locales/messages.pot`.
    ```bash
    pybabel extract -F babel.cfg -o locales/messages.pot .
    ```

2.  **Initialize a New Language (if adding a new one):**
    For example, to add Spanish (`es`):
    ```bash
    pybabel init -i locales/messages.pot -d locales -l es
    ```
    This will create a new file: `locales/es/LC_MESSAGES/messages.po`.

3.  **Update Existing Language Files:**
    If you've added new translatable strings to the code and want to update existing `.po` files (e.g., for `fr`, `ja`, `zh`):
    ```bash
    pybabel update -i locales/messages.pot -d locales
    ```

4.  **Translate the Messages:**
    Edit the `.po` file for the language you are working on (e.g., `locales/es/LC_MESSAGES/messages.po`). For each `msgid` (original string), provide the translation in the `msgstr` field.
    Example snippet from a `.po` file:
    ```po
    #: astroquery_cli/main.py:12
    msgid "Astroquery Command Line Interface. Provides access to various astronomical data services."
    msgstr "Interfaz de Línea de Comandos de Astroquery. Proporciona acceso a varios servicios de datos astronómicos."
    ```

5.  **Compile Translations:**
    After translating, compile the `.po` files into `.mo` files, which are binary files used by the application at runtime.
    ```bash
    pybabel compile -d locales
    ```
    This will create/update `.mo` files (e.g., `locales/es/LC_MESSAGES/messages.mo`).

6.  **Test:**
    Run the application with the new/updated language:
    ```bash
    aqc --lang es <some-command> --help
    ```

7.  **Commit Changes:**
    Add the updated/new `.po` and `.mo` files, as well as the `messages.pot` file, to your Git commit.
    ```bash
    git add locales/
    git commit -m "Add/Update Spanish translation"
    ```

## License

This project is licensed under the MIT License. (Consider adding a `LICENSE` file to your project root).

## Acknowledgements

*   The [Astroquery](https://astroquery.readthedocs.io/) developers for creating and maintaining the core library.
*   The [Typer](https://typer.tiangolo.com/) team for the excellent CLI framework.
```
