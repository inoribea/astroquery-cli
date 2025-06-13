import sys
import os
import typer
import builtins
from astroquery_cli import i18n
from astroquery_cli.debug import debug_manager
from io import StringIO
from contextlib import redirect_stdout

CONFIG_PATH = os.path.expanduser("~/.aqc_config")

def save_default_lang(lang):
    with open(CONFIG_PATH, "w") as f:
        f.write(lang.strip())

def load_default_lang():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return f.read().strip()
    return None

builtins._ = i18n._

app = typer.Typer(
    name="aqc",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)

_captured_stdout_during_import = "" # Initialize global variable at module level

def setup_subcommands():
    global _captured_stdout_during_import # Declare global here
    f = StringIO()
    with redirect_stdout(f):
        from .modules import (
            simbad_cli, alma_cli, esasky_cli, gaia_cli, irsa_cli, irsa_dust_cli,
            jplhorizons_cli, jplsbdb_cli, mast_cli, nasa_ads_cli, ned_cli,
            splatalogue_cli, vizier_cli
        )
    _captured_stdout_during_import = f.getvalue()

    app.add_typer(simbad_cli.get_app(), name="simbad")
    app.add_typer(alma_cli.get_app(), name="alma")
    app.add_typer(esasky_cli.get_app(), name="esasky")
    app.add_typer(gaia_cli.get_app(), name="gaia")
    app.add_typer(irsa_cli.get_app(), name="irsa")
    app.add_typer(irsa_dust_cli.get_app(), name="irsa_dust")
    app.add_typer(jplhorizons_cli.get_app(), name="jplhorizons")
    app.add_typer(jplsbdb_cli.get_app(), name="jplsbdb")
    app.add_typer(mast_cli.get_app(), name="mast")
    app.add_typer(nasa_ads_cli.get_app(), name="nasa_ads")
    app.add_typer(ned_cli.get_app(), name="ned")
    app.add_typer(splatalogue_cli.get_app(), name="splatalogue")
    app.add_typer(vizier_cli.get_app(), name="vizier")

@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str = typer.Option(
        i18n.INITIAL_LANG,
        "--language", # Removed -l and --lang
        help=i18n._("Set the language for output messages (e.g., 'en', 'zh'). Affects help texts and outputs."),
        is_eager=True,
        envvar="AQC_LANG",
        show_default=False
    ),
    default_lang: str = typer.Option(
        None,
        "-l", # Changed from -d to -l
        "--default",
        help=i18n._("Set the default language for this session (e.g., 'en', 'zh').")
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
        "-t",
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
    global _captured_stdout_during_import
    _ = builtins._
    ctx.obj = ctx.obj or {}
    
    # Set debug and verbose flags in context
    ctx.obj["debug"] = debug
    ctx.obj["verbose"] = verbose or debug
    
    # Enable debug manager
    if debug:
        debug_manager.enable_debug()
    if verbose:
        debug_manager.enable_verbose()

    if default_lang:
        ctx.obj["default_lang"] = default_lang
        save_default_lang(default_lang)
        lang = default_lang 
        debug_manager.verbose(f"Default language set to: {default_lang}")

    config_lang = load_default_lang()
    selected_lang = lang or ctx.obj.get("default_lang") or config_lang or i18n.INITIAL_LANG
    ctx.obj["lang"] = selected_lang

    # Print configuration information
    config_info = {
        "Debug Mode": debug,
        "Verbose Mode": verbose or debug,
        "Selected Language": selected_lang,
        "Config Path": CONFIG_PATH,
        "Config File Exists": os.path.exists(CONFIG_PATH),
        "Config Content": config_lang if config_lang else "None"
    }
    debug_manager.print_config_info(config_info)
    debug_manager.print_environment_info()
    debug_manager.print_system_info()

    i18n.init_translation(selected_lang)
    
    # Print translation information
    translation_info = {
        "Language Code": selected_lang,
        "Locale Directory": i18n.LOCALE_BASE_DIR,
        "Text Domain": i18n.TEXT_DOMAIN,
        "Current Language": i18n.translator_instance.get_current_language()
    }
    debug_manager.print_translation_info(selected_lang, translation_info)

    # Process captured stdout messages after translation is initialized
    if _captured_stdout_during_import:
        lines = _captured_stdout_during_import.splitlines()
        for line in lines:
            if "Gaia ESA Archive has been rolled back" in line:
                translated_message = _(
                    "Please note that the Gaia ESA Archive has been rolled back to version 3.7. "
                    "Please find the release notes at https://www.cosmos.esa.int/web/gaia-users/archive/release-notes"
                )
                print(translated_message)
            else:
                print(line)
        _captured_stdout_during_import = ""

    # Try to inject our translations into Click's gettext domain
    try:
        import gettext
        import click
        
        _ = i18n.get_translator()
        
        def custom_gettext(message):
            if debug:
                from rich.console import Console
                console = Console()
                console.print(f"[dim cyan]DEBUG: Click requesting translation for: '{message}'[/dim cyan]")
            
            translated = _(message)
            
            if debug:
                console.print(f"[dim cyan]DEBUG: Our translation result: '{translated}'[/dim cyan]")
            
            if translated != message:
                if debug:
                    console.print(f"[dim green]DEBUG: Using our translation: '{translated}'[/dim green]")
                return translated
            if debug:
                console = Console()
                console.print(f"[dim yellow]DEBUG: Using original message: '{message}'[/dim yellow]")
            return message
        
        click.core._ = custom_gettext
        if debug:
            from rich.console import Console
            console = Console()
            console.print("[dim green]DEBUG: Replaced Click's gettext function[/dim green]")
        
    except Exception as e:
        if debug:
            from rich.console import Console
            console = Console()
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

if __name__ == "__main__":
    try:
        setup_subcommands()
        app()
    except KeyboardInterrupt:
        from rich.console import Console
        _ = i18n.get_translator()
        console = Console()
        console.print(f"[bold yellow]{_('User interrupted the query. Exiting safely.')}[/bold yellow]")
        sys.exit(130)
