import sys
import os
from astroquery_cli import i18n
import builtins
import typer

app = typer.Typer(
    name="aqc",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)

# ... 你的 set_builtin_translation、save_default_lang、load_default_lang 等函数 ...

def setup_subcommands():
    from .modules import (
        simbad_cli, alma_cli, esasky_cli, gaia_cli, irsa_cli, irsa_dust_cli,
        jplhorizons_cli, jplsbdb_cli, mast_cli, nasa_ads_cli, ned_cli,
        splatalogue_cli, vizier_cli
    )
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

@ app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str = typer.Option(
        i18n.INITIAL_LANG,
        "-l",
        "--lang",
        "--language",
        help=builtins._("Set the language for output messages (e.g., 'en', 'zh'). Affects help texts and outputs."),
        is_eager=True,
        envvar="AQC_LANG",
        show_default=False
    ),
    default_lang: str = typer.Option(
        None,
        "-d",
        "--default",
        help=builtins._("Set the default language for this session (e.g., 'en', 'zh').")
    ),
    ping: bool = typer.Option(
        False,
        "-p",
        "--ping",
        help=builtins._("Test connectivity to major services (only available at top-level command).")
    ),
    field: bool = typer.Option(
        False,
        "-f",
        "--field",
        help=builtins._("Test field validity for modules (only available at top-level command).")
    )
):
    ctx.obj = ctx.obj or {}
    ctx.obj["lang"] = default_lang or lang

    # Handle options
    if ping:
        from astroquery_cli.options.ping import run_ping
        run_ping()
        raise typer.Exit()
    if field:
        from astroquery_cli.options.field import run_field
        run_field()
        raise typer.Exit()

setup_subcommands()

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        from rich.console import Console
        _ = i18n.get_translator()
        console = Console()
        console.print(f"[bold yellow]{_('User interrupted the query. Exiting safely.')}[/bold yellow]")
        sys.exit(130)