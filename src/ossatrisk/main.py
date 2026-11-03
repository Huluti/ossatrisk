import asyncio
import sys
import time

import click

from . import __version__
from .builders.js import JSBuilder
from .builders.php import PHPBuilder
from .scanner.js import JSScanner
from .scanner.php import PHPScanner


@click.group()
def cli():
    """Main CLI entry point"""


@cli.command()
def version():
    """Show ossatrisk version"""
    print(f"ossatrisk version {__version__}")


@cli.command()
@click.option(
    "--ecosystem",
    type=click.Choice(["php", "js"], case_sensitive=False),
    required=True,
)
def build_data(ecosystem):
    start_time = time.perf_counter()

    if ecosystem == "php":
        print("Launching PHP builder...")
        runner = PHPBuilder()
    elif ecosystem == "js":
        print("Launching JS builder...")
        runner = JSBuilder()
    else:
        print("Unsupported ecosystem.")
        sys.exit(1)

    runner.run()

    elapsed = time.perf_counter() - start_time
    print(f"\nTotal execution time: {elapsed:.2f} seconds")


@cli.command()
@click.option(
    "--ecosystem", type=click.Choice(["php", "js"], case_sensitive=False), required=True
)
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def scan(ecosystem, format):
    results = []
    try:
        if ecosystem.lower() == "php":
            scanner = PHPScanner()
        elif ecosystem.lower() == "js":
            scanner = JSScanner()
        else:
            click.echo("Unsupported ecosystem")
            sys.exit(1)
        results = asyncio.run(scanner.scan())
    except FileNotFoundError as e:
        click.echo(f"ERROR: {e}")
        sys.exit(1)

    # Sort results by score (highest first)
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    if format == "json":
        import json

        print(json.dumps(results, indent=2))
        if results:
            sys.exit(1)

    if not results:
        click.echo("No risky packages found")
        return

    # Table output for text format
    headers = ["Package", "Score", "Abandoned", "Suggested", "CVEs"]
    rows = []

    for pkg in results:
        rows.append(
            [
                pkg.get("name", ""),
                pkg.get("score", ""),
                "Yes" if pkg.get("abandoned") else "No",
                pkg.get("suggested", "") or "",
                pkg.get("cves_count", 0),
            ]
        )

    # Calculate column widths
    col_widths = [
        max(len(str(row[i])) for row in ([headers] + rows)) for i in range(len(headers))
    ]

    def format_row(row):
        return " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * w for w in col_widths)

    click.echo("Risky packages found:\n")
    click.echo(format_row(headers))
    click.echo(separator)
    for row in rows:
        click.echo(format_row(row))

    sys.exit(1)


if __name__ == "__main__":
    cli()
