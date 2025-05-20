import subprocess
import sys
import time

DEFAULT_COMMANDS = [
    ["esasky", "list-catalogs"],
    ["vizier", "--help"],
    ["simbad", "--help"],
    ["irsa", "--help"],
    ["ned", "--help"],
    ["alma", "--help"],
    ["mast", "--help"],
    ["nasa-ads", "--help"],
    ["jplsbdb", "--help"],
    ["jplhorizons", "--help"],
    ["irsa-dust", "--help"],
    ["splatalogue", "--help"],
]

def run_test(commands=None):
    """
    commands: list of list, e.g. [["esasky", "list-catalogs"], ...]
    If None, use DEFAULT_COMMANDS.
    """
    cli = [sys.executable, "-m", "astroquery_cli.main"]
    if commands is None:
        commands = DEFAULT_COMMANDS
    for args in commands:
        cmd = cli + args
        start = time.perf_counter()
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        elapsed = time.perf_counter() - start
        print(f"Command: {' '.join(cmd)}")
        print(f"Elapsed: {elapsed:.3f} s")
        print(f"Return code: {proc.returncode}")
        if proc.returncode != 0:
            print("Warning: Non-zero return code")
        if elapsed >= 60:
            print("Warning: Command took too long (>60s)")
        print("-" * 40)

if __name__ == "__main__":
    run_test()
