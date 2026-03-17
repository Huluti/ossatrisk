import sys
import time

import click

from builders.php import PHP
from scanner.php import PHPScanner


@click.group()
def cli():
    """Main CLI entry point"""
    pass


@cli.command()
@click.option(
    "--ecosystem",
    type=click.Choice(["php"], case_sensitive=False),
    required=True,
)
def build_data(ecosystem):
    start_time = time.perf_counter()

    if ecosystem == "php":
        print("Launching PHP runner...")
        runner = PHP()
        runner.run()
    else:
        print("Unsupported language. Only 'php' is supported.")
        sys.exit(1)

    elapsed = time.perf_counter() - start_time
    print(f"\nTotal execution time: {elapsed:.2f} seconds")


@cli.command()
@click.option(
    "--ecosystem",
    type=click.Choice(["php"], case_sensitive=False),
    required=True,
)
def scan(ecosystem):
    try:
        if ecosystem == "php":
            scanner = PHPScanner()
        else:
            print("Unsupported ecosystem")
            sys.exit(1)

        results = scanner.scan()

    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    if not results:
        print("✅ No risky packages found")
        return

    print("⚠️ Risky packages found:\n")
    for pkg in results:
        print(f"- {pkg['name']} (score: {pkg['score']})")
        if pkg["abandoned"]:
            print("  ⚠️ Abandoned package")
        if pkg["suggested"]:
            print(f"  👉 Suggested alternative: {pkg['suggested']}")
        print()


if __name__ == "__main__":
    cli()
