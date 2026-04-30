from abc import ABC, abstractmethod

import json
import time
from pathlib import Path
from ossatrisk.http_client import HttpClient

CACHE_TTL = 24 * 3600  # 24 hours in seconds


class BaseScanner(ABC):
    DATA_URL: str
    CACHE_FILENAME: str

    def __init__(self):
        self.client = HttpClient()

        self.project_path = Path.cwd()

        # Set up cache directory
        self.cache_dir = Path.home() / ".cache" / "ossatrisk"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def scan(self) -> list[dict]:
        """Run the scan and return results"""
        pass

    def _read_cache(self, cache_file: Path) -> dict | None:
        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < CACHE_TTL:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
        return None

    def _write_cache(self, cache_file: Path, data: dict):
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_risk_db(self) -> dict[str, dict]:
        cache_file = self.cache_dir / self.CACHE_FILENAME

        data = self._read_cache(cache_file)
        if data:
            print(f"Using cached data: {cache_file}")
            return {pkg["name"]: pkg for pkg in data}

        print(f"Downloading data from: {self.DATA_URL}")

        response = self.client.safe_get(self.DATA_URL)
        if not response:
            print("Failed to download risk database")
            return {}

        data = response.json()
        self._write_cache(cache_file, data)

        return {pkg["name"]: pkg for pkg in data}
