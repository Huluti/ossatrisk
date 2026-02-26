import sys
import time
from php import PHP

if __name__ == "__main__":
    start_time = time.perf_counter()

    if len(sys.argv) < 2:
        print("Usage: python script.py <language>")
        print("Example: python script.py php")
        sys.exit(1)

    language = sys.argv[1].lower()

    if language == "php":
        print("Launching PHP runner...")
        runner = PHP()
        runner.run()
    else:
        print("Unsupported language. Only 'php' is supported.")
        sys.exit(1)

    elapsed = time.perf_counter() - start_time
    print(f"\nTotal execution time: {elapsed:.2f} seconds")
