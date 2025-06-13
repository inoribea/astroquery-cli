import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import sys
import traceback
from typing import Any, Dict, Optional

class DebugManager:
    def __init__(self):
        self.console = Console()
        self._debug_enabled = os.getenv("AQC_DEBUG", "").lower() in ("1", "true", "yes")
        self._verbose_enabled = os.getenv("AQC_VERBOSE", "").lower() in ("1", "true", "yes")
    
    @property
    def debug_enabled(self) -> bool:
        return self._debug_enabled
    
    @property
    def verbose_enabled(self) -> bool:
        return self._verbose_enabled or self._debug_enabled
    
    def enable_debug(self):
        self._debug_enabled = True
        os.environ["AQC_DEBUG"] = "1"
    
    def enable_verbose(self):
        self._verbose_enabled = True
        os.environ["AQC_VERBOSE"] = "1"
    
    def debug(self, message: str, prefix: str = "DEBUG"):
        if self.debug_enabled:
            self.console.print(f"[dim cyan]{prefix}: {message}[/dim cyan]")
    
    def verbose(self, message: str, prefix: str = "INFO"):
        if self.verbose_enabled:
            self.console.print(f"[dim]{prefix}: {message}[/dim]")
    
    def success(self, message: str):
        if self.verbose_enabled:
            self.console.print(f"[dim green]SUCCESS: {message}[/dim green]")
    
    def warning(self, message: str):
        if self.verbose_enabled:
            self.console.print(f"[dim yellow]WARNING: {message}[/dim yellow]")
    
    def error(self, message: str, exception: Optional[Exception] = None):
        if self.verbose_enabled:
            self.console.print(f"[dim red]ERROR: {message}[/dim red]")
            if exception and self.debug_enabled:
                self.console.print(f"[dim red]Exception: {str(exception)}[/dim red]")
                if hasattr(exception, '__traceback__'):
                    tb_lines = traceback.format_tb(exception.__traceback__)
                    for line in tb_lines:
                        self.console.print(f"[dim red]{line.strip()}[/dim red]")
    
    def print_config_info(self, config_data: Dict[str, Any]):
        if not self.verbose_enabled:
            return
        
        table = Table(title="Configuration Information", show_header=True, header_style="bold blue")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in config_data.items():
            table.add_row(str(key), str(value))
        
        self.console.print(table)
    
    def print_environment_info(self):
        if not self.debug_enabled:
            return
        
        env_vars = {k: v for k, v in os.environ.items() if k.startswith("AQC_")}
        
        table = Table(title="Environment Variables", show_header=True, header_style="bold blue")
        table.add_column("Variable", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in env_vars.items():
            table.add_row(key, value)
        
        if not env_vars:
            table.add_row("No AQC_* variables found", "")
        
        self.console.print(table)
    
    def print_system_info(self):
        if not self.debug_enabled:
            return
        
        import platform
        
        info = {
            "Python Version": platform.python_version(),
            "Platform": platform.platform(),
            "Architecture": platform.architecture()[0],
            "Working Directory": os.getcwd(),
            "Script Path": sys.argv[0] if sys.argv else "Unknown"
        }
        
        table = Table(title="System Information", show_header=True, header_style="bold blue")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in info.items():
            table.add_row(key, str(value))
        
        self.console.print(table)
    
    def print_translation_info(self, lang_code: str, translator_info: Dict[str, Any]):
        if not self.debug_enabled:
            return
        
        table = Table(title=f"Translation Information ({lang_code})", show_header=True, header_style="bold blue")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in translator_info.items():
            table.add_row(str(key), str(value))
        
        self.console.print(table)
    
    def trace_function_call(self, func_name: str, args: tuple = (), kwargs: dict = None):
        if not self.debug_enabled:
            return
        
        kwargs = kwargs or {}
        args_str = ", ".join([repr(arg) for arg in args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        
        all_args = ", ".join(filter(None, [args_str, kwargs_str]))
        self.debug(f"Calling {func_name}({all_args})", "TRACE")

# Global debug manager instance
debug_manager = DebugManager()

# Convenience functions
def debug(message: str, prefix: str = "DEBUG"):
    debug_manager.debug(message, prefix)

def verbose(message: str, prefix: str = "INFO"):
    debug_manager.verbose(message, prefix)

def success(message: str):
    debug_manager.success(message)

def warning(message: str):
    debug_manager.warning(message)

def error(message: str, exception: Optional[Exception] = None):
    debug_manager.error(message, exception)

def trace_call(func_name: str, args: tuple = (), kwargs: dict = None):
    debug_manager.trace_function_call(func_name, args, kwargs)

def is_debug_enabled() -> bool:
    return debug_manager.debug_enabled

def is_verbose_enabled() -> bool:
    return debug_manager.verbose_enabled
