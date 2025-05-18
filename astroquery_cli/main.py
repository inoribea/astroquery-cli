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
    name="aq",
    help=_("Astroquery Command Line Interface. Provides access to various astronomical data services."),
    invoke_without_command=True, # <--- 主要改变在这里
    no_args_is_help=True,      # 保持这个，以便 `aq` (无参数) 显示帮助
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]}
)

def lang_callback(ctx: typer.Context, value: str):
    if value and value != i18n.get_current_language():
        i18n.init_translation(value)
        global _
        _ = i18n.get_translator()
        # 更新 Typer app 的帮助文本和 main_callback 的 docstring
        current_help = _("Astroquery Command Line Interface. Provides access to various astronomical data services.")
        if ctx.parent: # 在 Typer 0.9.0+ 中，app 是 ctx.parent
            ctx.parent.help = current_help
        elif hasattr(app, 'help'): # 兼容旧版本或直接访问
            app.help = current_help

        current_docstring = _("""
    Astroquery CLI: Your gateway to astronomical data. 🌠

    Use '--lang' or '-l' to set the interface language.
    Example: aq -l zh_CN simbad query-object M31
    """)
        if main_callback.__doc__:
            main_callback.__doc__ = current_docstring
            # 尝试更新 Typer 内部对回调的描述，这可能需要更深层次的操作
            # 但至少 Python 的 __doc__ 是更新了的
    return value

@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str = typer.Option(
        i18n.INITIAL_LANG,
        "-l",
        "--lang",
        "--language",
        help=_("Set the language for output messages (e.g., 'en', 'zh_CN'). Affects help texts and outputs."),
        callback=lang_callback,
        is_eager=True,
        envvar="AQ_LANG",
        show_default=False # 不在帮助中显示默认值，因为它是动态初始化的
    )
):
    """
    Astroquery CLI: Your gateway to astronomical data. 🌠

    Use '--lang' or '-l' to set the interface language.
    Example: aq -l zh_CN simbad query-object M31
    """
    # 如果 main_callback 被调用了，但没有子命令被调用
    if ctx.invoked_subcommand is None:
        # 检查是否只传递了语言选项
        # `ctx.params` 会包含所有解析到的顶级选项，如 {'lang': 'zh_CN'}
        # 如果除了 'lang' 之外还有其他参数被传递但没有被识别为命令，
        # Typer 通常会在之前就报错（除非这些是全局选项）。

        # 如果用户只输入了 `aq -l <lang_code>`
        # `sys.argv` 检查是否只包含程序名、语言选项和其值
        lang_option_flags = ["-l", "--lang", "--language"]
        is_only_lang_option = False
        if len(sys.argv) == 3: # e.g., program -l en
            if sys.argv[1] in lang_option_flags and not sys.argv[2].startswith("-"):
                is_only_lang_option = True
        elif len(sys.argv) == 2 and "=" in sys.argv[1]: # e.g., program --lang=en
             opt_name, opt_val = sys.argv[1].split("=", 1)
             if opt_name in lang_option_flags and not opt_val.startswith("-"):
                 is_only_lang_option = True

        if is_only_lang_option:
            current_set_lang = i18n.get_current_language()
            typer.echo(_("Language active: {lang_code}").format(lang_code=current_set_lang))
            typer.echo(_("Run '{prog_name} --help' or '{prog_name} -h' to see available commands.").format(prog_name=ctx.find_root().info_name))
            raise typer.Exit(code=0)
        else:
            # 如果调用了 `aq` (没有参数)，`no_args_is_help=True` 会先生效，显示帮助并退出，
            # 所以这里通常不会执行到。
            # 如果用户输入了 `aq --some-unknown-global-option` 并且没有命令，
            # Typer 可能会在这里或者之前报错。
            # 如果用户输入了 `aq some_arg_not_a_command -l en` Typer 会报错
            # "Got unexpected extra argument (some_arg_not_a_command)"
            # 基本上，如果到这里且 is_only_lang_option 为 False，可能意味着
            # 用户只输入了 `aq`（已经被 no_args_is_help 处理）
            # 或者有一些不应该出现的情况。
            # 为了安全，如果不是预期的 "仅语言选项" 模式，并且没有子命令，
            # 我们也显示帮助。
            if not ctx.args and not any(arg for arg in sys.argv[1:] if not arg.startswith('-') and arg not in lang_option_flags and arg != lang):
                 # 这意味着除了选项外，没有其他可能是命令的参数
                 # 但也不是 is_only_lang_option 的情况
                 # 例如 `aq -l` (没有值)，Typer 会报错
                 # 如果是 `aq --version` (假设有这个选项)，会执行并退出
                 # 这里主要是捕获那些 invoke_without_command=True 允许的、
                 # 但又不是我们特定处理的 "仅语言选项" 的情况。
                 # 如果没有其他参数，打印帮助可能是最安全的。
                 pass # Typer 的 no_args_is_help 应该已经处理了 `aq` 的情况。
                     # 如果有其他选项但没有命令，Typer 会在解析时报错或执行那些选项。
                     # 此处不再需要特别的 get_help(), 除非 no_args_is_help 被移除。


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
