import typer
import sys
from . import i18n

app = typer.Typer(
    name="aqc",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]}
)

def setup_subcommands(_):
    from .modules import (
        simbad_cli, alma_cli, esasky_cli, gaia_cli, irsa_cli, irsa_dust_cli,
        jplhorizons_cli, jplsbdb_cli, mast_cli, nasa_ads_cli, ned_cli,
        splatalogue_cli, vizier_cli
    )
    app.add_typer(simbad_cli.get_app(_), name="simbad", help=_("SIMBAD astronomical database."))
    app.add_typer(alma_cli.get_app(_), name="alma", help=_("Query the ALMA archive."))
    app.add_typer(esasky_cli.get_app(_), name="esasky", help=_("Query the ESA Sky archive."))
    app.add_typer(gaia_cli.get_app(_), name="gaia", help=_("Query the Gaia archive."))
    app.add_typer(irsa_cli.get_app(_), name="irsa", help=_("Query NASA/IPAC Infrared Science Archive (IRSA)."))
    app.add_typer(irsa_dust_cli.get_app(_), name="irsa_dust", help=_("Query IRSA dust maps."))
    app.add_typer(jplhorizons_cli.get_app(_), name="jplhorizons", help=_("Query JPL Horizons ephemeris service."))
    app.add_typer(jplsbdb_cli.get_app(_), name="jplsbdb", help=_("Query JPL Small-Body Database (SBDB)."))
    app.add_typer(mast_cli.get_app(_), name="mast", help=_("Query the Mikulski Archive for Space Telescopes (MAST)."))
    app.add_typer(nasa_ads_cli.get_app(_), name="nasa_ads", help=_("Query the NASA Astrophysics Data System (ADS)."))
    app.add_typer(ned_cli.get_app(_), name="ned", help=_("Query the NASA/IPAC Extragalactic Database (NED)."))
    app.add_typer(splatalogue_cli.get_app(_), name="splatalogue", help=_("Query the Splatalogue spectral line database."))
    app.add_typer(vizier_cli.get_app(_), name="vizier", help=_("Query the VizieR astronomical catalog service."))

@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str = typer.Option(
        i18n.INITIAL_LANG,
        "-l",
        "--lang",
        "--language",
        help="Set the language for output messages (e.g., 'en', 'zh'). Affects help texts and outputs.",
        callback=lambda ctx, value: i18n.init_translation(value) or value,
        is_eager=True,
        envvar="AQ_LANG",
        show_default=False
    )
):
    pass

def main():
    lang = i18n.INITIAL_LANG
    for idx, arg in enumerate(sys.argv):
        if arg in ("-l", "--lang", "--language") and idx + 1 < len(sys.argv):
            lang = sys.argv[idx + 1]
            break
    i18n.init_translation(lang)
    _ = i18n.get_translator()
    setup_subcommands(_)
    app()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        from rich.console import Console
        _ = i18n.get_translator()
        console = Console()
        console.print(f"[bold yellow]{_('User interrupted the query. Exiting safely.')}[/bold yellow]")
        sys.exit(130)