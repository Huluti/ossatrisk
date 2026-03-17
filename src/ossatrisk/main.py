import sys
import time

import click

from . import __version__
from .builders.php import PHPBuilder
from .scanner.php import PHPScanner


@click.group()
def cli():
    """Main CLI entry point"""
    pass


@cli.command()
def version():
    """Show ossatrisk version"""
    print(f"ossatrisk version {__version__}")


@cli.command()
@click.option(
    "--ecosystem",
    type=click.Choice(["php"], case_sensitive=False),
    required=True,
)
def build_data(ecosystem):
    start_time = time.perf_counter()

    if ecosystem == "php":
        print("Launching PHP builder...")
        runner = PHPBuilder()
        runner.run()
    else:
        print("Unsupported language. Only 'php' is supported.")
        sys.exit(1)

    elapsed = time.perf_counter() - start_time
    print(f"\nTotal execution time: {elapsed:.2f} seconds")


@cli.command()
@click.option(
    "--ecosystem", type=click.Choice(["php"], case_sensitive=False), required=True
)
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
@click.option("--ci", is_flag=True, help="CI-friendly output")
def scan(ecosystem, format, ci):
    results = []
    try:
        if ecosystem.lower() == "php":
            scanner = PHPScanner()
        else:
            click.echo("Unsupported ecosystem")
            if ci:
                sys.exit(1)
            return
        results = scanner.scan()
    except FileNotFoundError as e:
        click.echo(f"ERROR: {e}")
        if ci:
            sys.exit(1)
        return

    if format == "json":
        import json

        print(json.dumps(results, indent=2))
        if results and ci:
            sys.exit(1)
        return  # don’t exit in interactive mode

    if not results:
        click.echo("No risky packages found")
        return

    click.echo("Risky packages found:")
    for pkg in results:
        line = f"- {pkg['name']} (score: {pkg['score']})"
        if pkg["abandoned"]:
            line += " [ABANDONED]"
        if pkg["suggested"]:
            line += f" -> Suggested: {pkg['suggested']}"
        click.echo(line)

    if ci:
        sys.exit(1)  # exit only in CI mode


if __name__ == "__main__":
    cli()
