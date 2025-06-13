import typer
from astroquery_cli import i18n
from astroquery_cli.debug import debug_manager

def add_debug_options(callback_func):
    """Decorator to add common debug and verbose options to a command callback."""
    def wrapper(
        ctx: typer.Context,
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
        ),
        *args,
        **kwargs
    ):
        # Set up debug context
        ctx.obj = ctx.obj or {}
        ctx.obj["debug"] = debug or ctx.obj.get("debug", False)
        ctx.obj["verbose"] = verbose or debug or ctx.obj.get("verbose", False)
        
        # Enable debug manager if needed
        if ctx.obj["debug"]:
            debug_manager.enable_debug()
        if ctx.obj["verbose"]:
            debug_manager.enable_verbose()
        
        # Call the original callback
        return callback_func(ctx, *args, debug=debug, verbose=verbose, **kwargs)
    
    return wrapper

def get_debug_options():
    """Return debug and verbose option definitions for manual use."""
    return [
        typer.Option(
            False,
            "-t",
            "--debug",
            help=i18n._("Enable debug mode with verbose output."),
            envvar="AQC_DEBUG"
        ),
        typer.Option(
            False,
            "-v",
            "--verbose",
            help=i18n._("Enable verbose output.")
        )
    ]

def setup_debug_context(ctx: typer.Context, debug: bool, verbose: bool):
    """Set up debug context for a command."""
    ctx.obj = ctx.obj or {}
    ctx.obj["debug"] = debug or ctx.obj.get("debug", False)
    ctx.obj["verbose"] = verbose or debug or ctx.obj.get("verbose", False)
    
    # Enable debug manager if needed
    if ctx.obj["debug"]:
        debug_manager.enable_debug()
    if ctx.obj["verbose"]:
        debug_manager.enable_verbose()

def is_debug_enabled(ctx: typer.Context) -> bool:
    """Check if debug mode is enabled in the context."""
    return ctx.obj and ctx.obj.get("debug", False)

def is_verbose_enabled(ctx: typer.Context) -> bool:
    """Check if verbose mode is enabled in the context."""
    return ctx.obj and ctx.obj.get("verbose", False)
