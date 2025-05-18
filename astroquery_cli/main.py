import typer
import os
import sys

from . import i18n

_ = i18n.get_translator()

from .modules import (
    simbad_cli,
    alma_cli,
    esasky_cli,
    gaia_cli,
    irsa_cli,
    irsa_dust_cli,
    jplhorizons_cli,
    jplsbdb_cli,
    mast_cli,
    nasa_ads_cli,
    ned_cli,
    splatalogue_cli,
    vizier_cli
)

app = typer.Typer(
    name="aqc",
    help=_("Astroquery Command Line Interface. Provides access to various astronomical data services."),
    invoke_without_command=True, 
    no_args_is_help=True,     
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]}
)

def lang_callback(ctx: typer.Context, value: str):
    if value and value != i18n.get_current_language():
        i18n.init_translation(value)
        global _
        _ = i18n.get_translator()
        current_help = _("Astroquery Command Line Interface. Provides access to various astronomical data services.")
        if ctx.parent: 
            ctx.parent.help = current_help
        elif hasattr(app, 'help'):
            app.help = current_help

        current_docstring = _("""
    Astroquery CLI: Your gateway to astronomical data. 🌠

    Use '--lang' or '-l' to set the interface language.
    Example: aqc -l zh simbad query-object M31
    """)
        if main_callback.__doc__:
            main_callback.__doc__ = current_docstring
    return value

@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str = typer.Option(
        i18n.INITIAL_LANG,
        "-l",
        "--lang",
        "--language",
        help=_("Set the language for output messages (e.g., 'en', 'zh'). Affects help texts and outputs."),
        callback=lang_callback,
        is_eager=True,
        envvar="AQ_LANG",
        show_default=False 
    )
):

    if ctx.invoked_subcommand is None:
        lang_option_flags = ["-l", "--lang", "--language"]
        is_only_lang_option = False
        if len(sys.argv) == 3: 
            if sys.argv[1] in lang_option_flags and not sys.argv[2].startswith("-"):
                is_only_lang_option = True
        elif len(sys.argv) == 2 and "=" in sys.argv[1]: 
             opt_name, opt_val = sys.argv[1].split("=", 1)
             if opt_name in lang_option_flags and not opt_val.startswith("-"):
                 is_only_lang_option = True

        if is_only_lang_option:
            current_set_lang = i18n.get_current_language()
            typer.echo(_("Language active: {lang_code}").format(lang_code=current_set_lang))
            typer.echo(_("Run '{prog_name} --help' or '{prog_name} -h' to see available commands.").format(prog_name=ctx.find_root().info_name))
            raise typer.Exit(code=0)
        else:
            
            if not ctx.args and not any(arg for arg in sys.argv[1:] if not arg.startswith('-') and arg not in lang_option_flags and arg != lang):
                
                 pass 


app.add_typer(simbad_cli.app, name="simbad", help=_("SIMBAD astronomical database."))
app.add_typer(alma_cli.app, name="alma", help=_("Query the ALMA archive."))
app.add_typer(esasky_cli.app, name="esasky", help=_("Query the ESA Sky archive."))
app.add_typer(gaia_cli.app, name="gaia", help=_("Query the Gaia archive."))
app.add_typer(irsa_cli.app, name="irsa", help=_("Query NASA/IPAC Infrared Science Archive (IRSA)."))
app.add_typer(irsa_dust_cli.app, name="irsa_dust", help=_("Query IRSA dust maps."))
app.add_typer(jplhorizons_cli.app, name="jplhorizons", help=_("Query JPL Horizons ephemeris service."))
app.add_typer(jplsbdb_cli.app, name="jplsbdb", help=_("Query JPL Small-Body Database (SBDB)."))
app.add_typer(mast_cli.app, name="mast", help=_("Query the Mikulski Archive for Space Telescopes (MAST)."))
app.add_typer(nasa_ads_cli.app, name="nasa_ads", help=_("Query the NASA Astrophysics Data System (ADS)."))
app.add_typer(ned_cli.app, name="ned", help=_("Query the NASA/IPAC Extragalactic Database (NED)."))
app.add_typer(splatalogue_cli.app, name="splatalogue", help=_("Query the Splatalogue spectral line database."))
app.add_typer(vizier_cli.app, name="vizier", help=_("Query the VizieR astronomical catalog service."))

if __name__ == "__main__":
    app()
