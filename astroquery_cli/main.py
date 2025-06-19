import os
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LANGUAGE'] = 'zh_CN.UTF-8'

import sys
import typer
import builtins

import logging
from astropy.logger import AstropyLogger

logging.setLoggerClass(AstropyLogger)
logging.getLogger('astroquery').setLevel(logging.INFO)

# Monkey patch astroquery DummyLogger: add getEffectiveLevel to avoid AttributeError
try:
    import importlib
    aq_logger_mod = importlib.import_module("astroquery.logger")
    if hasattr(aq_logger_mod, "DummyLogger"):
        def _dummy_getEffectiveLevel(self):
            return logging.INFO
        aq_logger_mod.DummyLogger.getEffectiveLevel = _dummy_getEffectiveLevel
except Exception:
    pass
from io import StringIO
from contextlib import redirect_stdout
from astropy.config import get_config_dir, get_config
from rich.console import Console # Import Console
from rich.text import Text # Import Text
import re # Import re
import logging # Import logging

# Suppress astroquery log messages globally (moved to __init__.py for earlier execution)
# Monkey patch for astroquery.logger._init_log (moved to __init__.py for earlier execution)

from astroquery_cli import config # Import config first
# Load configuration from ~/.aqc/config.ini
config.load_config()

# Force early translation initialization (will be re-initialized in callback)
from astroquery_cli import i18n
i18n.init_translation(i18n.INITIAL_LANG)
builtins._ = i18n._

from astroquery_cli.debug import debug_manager


def save_default_lang(lang):
    config.set_language(lang.strip())

def load_default_lang():
    return config.get_language()


app = typer.Typer(
    name="aqc",
    help=i18n._("Astroquery CLI"),
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False, # Set to False to remove global completion commands
    context_settings={"help_option_names": ["-h", "--help"]},
)

def setup_subcommands():
    import logging
    # Suppress astroquery log messages during import
    logging.getLogger('astroquery').setLevel(logging.CRITICAL)

    # Import all subcommands
    from .modules import (
        simbad_cli, alma_cli, esasky_cli, gaia_cli, irsa_cli, jpl_cli,
        mast_cli, ads_cli, ned_cli, splatalogue_cli, vizier_cli,
        heasarc_cli, sdss_cli, eso_cli, nist_cli, exoplanet_cli
    )
    # Restore astroquery log level after import
    logging.getLogger('astroquery').setLevel(logging.NOTSET)

    app.add_typer(alma_cli.get_app(), name="alma")
    app.add_typer(esasky_cli.get_app(), name="esasky")
    app.add_typer(gaia_cli.get_app(), name="gaia")
    app.add_typer(irsa_cli.get_app(), name="irsa")
    app.add_typer(jpl_cli.get_app(), name="jpl") # Updated for jpl
    app.add_typer(mast_cli.get_app(), name="mast")
    app.add_typer(ads_cli.get_app(), name="ads")
    app.add_typer(ned_cli.get_app(), name="ned")
    app.add_typer(simbad_cli.get_app(), name="simbad")
    app.add_typer(splatalogue_cli.get_app(), name="splatalogue")
    app.add_typer(vizier_cli.get_app(), name="vizier")
    app.add_typer(heasarc_cli.get_app(), name="heasarc")
    app.add_typer(sdss_cli.get_app(), name="sdss")
    app.add_typer(eso_cli.get_app(), name="eso")
    app.add_typer(nist_cli.get_app(), name="nist")
    app.command(name="exoplanet", help=builtins._("Query the NASA Exoplanet Archive."))(exoplanet_cli.get_app())

@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str = typer.Option(
        None,
        "-l",
        "--lang",
        help=i18n._("Set the language for output messages (e.g., 'en', 'zh'). Affects help texts and outputs."),
        is_eager=True,
        envvar="AQC_LANG",
        show_default=False
    ),
    ping: bool = typer.Option(
        False,
        "-p",
        "--ping",
        help=i18n._("Test connectivity to major services (only available at top-level command).")
    ),
    field: bool = typer.Option(
        False,
        "-f",
        "--field",
        help=i18n._("Test field validity for modules (only available at top-level command).")
    ),
    debug: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help=i18n._("Enable debug mode with verbose output."),
        envvar="AQC_DEBUG"
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help=i18n._("Enable verbose output.")
    )
):
    _ = builtins._
    ctx.obj = ctx.obj or {}

    # Initialize console for general use
    console = Console()

    # Set debug and verbose flags in context
    ctx.obj["debug"] = debug
    ctx.obj["verbose"] = verbose or debug
    
    # Enable debug manager
    if debug:
        debug_manager.enable_debug()
    if verbose:
        debug_manager.enable_verbose()

    if lang:
        save_default_lang(lang)
        debug_manager.verbose(f"Default language set to: {lang}")

    config_lang = load_default_lang()
    selected_lang = lang or config_lang or i18n.INITIAL_LANG
    ctx.obj["lang"] = selected_lang

    # Print configuration information
    config_info = {
        "Debug Mode": debug,
        "Verbose Mode": verbose or debug,
        "Selected Language": selected_lang,
        "Config Path": config.CONFIG_FILE_PATH, # Use the correct config path from astroquery_cli.config
        "Config File Exists": os.path.exists(config.CONFIG_FILE_PATH),
        "Config Content": config_lang if config_lang else "None"
    }
    debug_manager.print_config_info(config_info)
    debug_manager.print_environment_info()
    debug_manager.print_system_info()

    # Re-initialize translation in callback to handle runtime language changes
    i18n.init_translation(selected_lang)
    builtins._ = i18n._ # Update builtins._ after re-initialization
    
    # Print translation information
    translation_info = {
        "Language Code": selected_lang,
        "Locale Directory": i18n.LOCALE_BASE_DIR,
        "Text Domain": i18n.TEXT_DOMAIN,
        "Current Language": i18n.translator_instance.get_current_language()
    }
    debug_manager.print_translation_info(selected_lang, translation_info)

    # Try to inject our translations into Click's gettext domain
    try:
        import gettext
        import click
        
        _ = i18n.get_translator()
        
        def custom_gettext(message):
            if debug:
                console.print(f"[dim cyan]DEBUG: Click requesting translation for: '{message}'[/dim cyan]")
            
            translated = _(message)
            
            if debug:
                console.print(f"[dim cyan]DEBUG: Our translation result: '{translated}'[/dim cyan]")
            
            if translated != message:
                if debug:
                    console.print(f"[dim green]DEBUG: Using our translation: '{translated}'[/dim green]")
                return translated
            if debug:
                console.print(f"[dim yellow]DEBUG: Using original message: '{message}'[/dim yellow]")
            return message
        
        click.core._ = custom_gettext
        if debug:
            console.print("[dim green]DEBUG: Replaced Click's gettext function[/dim green]")
        
    except Exception as e:
        if debug:
            console.print(f"[dim red]DEBUG: Failed to replace Click's gettext function: {e}[/dim red]")

    if ping:
        from astroquery_cli.options.ping import run_ping
        run_ping()
        raise typer.Exit()
    if field:
        from astroquery_cli.options.field import run_field
        run_field()
        raise typer.Exit()

    # Dynamically modify the help text for completion commands
    if hasattr(app, 'registered_commands') and isinstance(app.registered_commands, dict):
        debug_manager.debug("Dynamically modifying help texts for completion commands.")
        for command_name, command_obj in app.registered_commands.items():
            original_help = command_obj.help
            if command_name == "install-completion":
                command_obj.help = i18n._("Install completion for the current shell.")
            elif command_name == "show-completion":
                command_obj.help = i18n._("Show completion for the current shell, to copy it or customize the installation.")
            elif command_name == "help":
                command_obj.help = i18n._("Show this message and exit.")
            
            if debug_manager.debug_enabled:
                debug_manager.debug(f"Command '{command_name}': Original help='{original_help}', New help='{command_obj.help}'")

    # If no subcommand is invoked and no explicit help is requested,
    # display only the "Commands" section.
    if ctx.invoked_subcommand is None and \
       not any(arg in ["-h", "--help"] for arg in sys.argv):
        if not ping and not field:
            # Capture the full help output by explicitly calling the app with --help
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    # Call the app with --help to get the full help output
                    # sys.argv[1:] will be empty if no arguments are passed to the main script
                    # so this effectively calls app(["--help"])
                    app(sys.argv[1:] + ["--help"])
                except SystemExit:
                    # Typer exits after showing help, catch the SystemExit exception
                    pass
            full_help_text = help_output_capture.getvalue()

            # Remove the gaia_message from the captured help text if it's present
            # This is to prevent duplication if Typer's help also includes it
            import re
            full_help_text = re.sub(r"Please note that the Gaia ESA Archive has been rolled back to version 3\.7\..*?release-notes\)?\n?", "", full_help_text, flags=re.DOTALL)

            # Extract only the "Commands" section using regex, including the full bottom border
            commands_match = re.search(r'╭─ Commands ─.*?(\n(?:│.*?\n)*)╰─.*─╯', full_help_text, re.DOTALL)
            if commands_match:
                commands_section = commands_match.group(0)
                # This is a fallback in case Typer's internal help generation includes it
                filtered_commands_section = "\n".join([
                    line for line in commands_section.splitlines() if "Usage:" not in line
                ])
                console.print(filtered_commands_section)
            else:
                # Fallback: if commands section not found, print full help
                console.print(full_help_text)
            raise typer.Exit()

def cli():
    from rich.console import Console # Import Console here
    try:
        # Check for debug flag early to configure debug_manager before module imports
        if "--debug" in sys.argv or "-d" in sys.argv:
            debug_manager.enable_debug()
            # Print a message indicating debug mode is enabled
            console = Console()
            console.print("[bold green]Debug mode enabled.[/bold green]")
        # Removed the "Debug mode disabled" message as per user request.

        setup_subcommands()
        app()
    except KeyboardInterrupt:
        _ = i18n.get_translator()
        console = Console()
        console.print(f"[bold yellow]{_('User interrupted the query. Exiting safely.')}[bold yellow]")
        sys.exit(130)

if __name__ == "__main__":
    cli()
