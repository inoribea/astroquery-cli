
import typer
from typing_extensions import Annotated

from . import __version__
from .modules import (
    simbad_cli,
    vizier_cli,
    jplhorizons_cli,
    gaia_cli,
    irsa_dust_cli,
    alma_cli,
    esasky_cli,
    irsa_cli,
    jplsbdb_cli,
    mast_cli,
    nasa_ads_cli,
    ned_cli,
    splatalogue_cli,
    # Add other module CLIs here if you create more
)

app = typer.Typer(
    name="aq",
    help="Astroquery CLI: Access astronomical data services from your terminal.",
    add_completion=False,
    no_args_is_help=True
)

def version_callback(value: bool):
    if value:
        print(f"Astroquery-CLI Version: {__version__}")
        raise typer.Exit()

@app.callback()
def main_options(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
):
    """
    Manage Astroquery CLI options.
    """
    pass


# Register subcommands (modules)
app.add_typer(simbad_cli.app, name="simbad", help=simbad_cli.app.info.help if simbad_cli.app.info else "Query the SIMBAD astronomical database.")
app.add_typer(ned_cli.app, name="ned", help=ned_cli.app.info.help if ned_cli.app.info else "Query the NASA/IPAC Extragalactic Database (NED).")
app.add_typer(vizier_cli.app, name="vizier", help=vizier_cli.app.info.help if vizier_cli.app.info else "Query the VizieR catalog service.")
app.add_typer(jplhorizons_cli.app, name="jplhorizons", help=jplhorizons_cli.app.info.help if jplhorizons_cli.app.info else "Query JPL Horizons ephemeris service.")
app.add_typer(jplsbdb_cli.app, name="jplsbdb", help=jplsbdb_cli.app.info.help if jplsbdb_cli.app.info else "Query the JPL Small-Body Database.")
app.add_typer(gaia_cli.app, name="gaia", help=gaia_cli.app.info.help if gaia_cli.app.info else "Query the Gaia mission archive.")
app.add_typer(irsa_cli.app, name="irsa", help=irsa_cli.app.info.help if irsa_cli.app.info else "Query the NASA/IPAC Infrared Science Archive (IRSA).")
app.add_typer(irsa_dust_cli.app, name="irsa-dust", help=irsa_dust_cli.app.info.help if irsa_dust_cli.app.info else "Query IRSA dust maps.")
app.add_typer(alma_cli.app, name="alma", help=alma_cli.app.info.help if alma_cli.app.info else "Query the ALMA science archive.")
app.add_typer(splatalogue_cli.app, name="splatalogue", help=splatalogue_cli.app.info.help if splatalogue_cli.app.info else "Query the Splatalogue spectral line database.")
app.add_typer(nasa_ads_cli.app, name="ads", help=nasa_ads_cli.app.info.help if nasa_ads_cli.app.info else "Query the NASA Astrophysics Data System (ADS).")
app.add_typer(esasky_cli.app, name="esasky", help=esasky_cli.app.info.help if esasky_cli.app.info else "Query the ESASky science archive portal.")
app.add_typer(mast_cli.app, name="mast", help=mast_cli.app.info.help if mast_cli.app.info else "Query the Mikulski Archive for Space Telescopes (MAST).")

# Add other modules here in the same way:
# app.add_typer(your_new_module_cli.app, name="newmodule", help="Help text for new module.")


def main():
    app()

if __name__ == "__main__":
    main()
