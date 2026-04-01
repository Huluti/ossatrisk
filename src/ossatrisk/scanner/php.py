import json
import time
from pathlib import Path
from .base import BaseScanner

DATA_URL = (
    "https://raw.githubusercontent.com/Huluti/ossatrisk/main/data/php-packages.json"
)
CACHE_TTL = 24 * 3600  # 24 hours in seconds


class PHPScanner(BaseScanner):
    def __init__(self):
        super().__init__()

        self.project_path = Path.cwd()
        self.composer_file = self._find_composer_file()
        if not self.composer_file:
            raise FileNotFoundError(
                "composer.json not found in current folder or any parent directories"
            )

        # Set up cache directory
        self.cache_dir = Path.home() / ".cache" / "ossatrisk"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "php-packages.json"

    def _find_composer_file(self) -> Path | None:
        """Search current folder and parents for composer.json"""
        path = self.project_path
        while path != path.parent:
            candidate = path / "composer.json"
            if candidate.exists():
                return candidate
            path = path.parent
        return None

    def _load_composer_packages(self) -> set[str]:
        if self.composer_file is None:
            raise FileNotFoundError(
                "composer.json not found in current folder or any parent directories"
            )
        with open(self.composer_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        require = data.get("require", {})
        require_dev = data.get("require-dev", {})
        return set(list(require.keys()) + list(require_dev.keys()))

    def _load_risk_db(self) -> dict[str, dict]:
        # Use cache if exists and is fresh
        if self.cache_file.exists():
            mtime = self.cache_file.stat().st_mtime
            if time.time() - mtime < CACHE_TTL:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {pkg["name"]: pkg for pkg in data}

        # Download from DATA_URL
        response = self.client.get(DATA_URL)
        response.raise_for_status()
        data = response.json()

        # Save to cache
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return {pkg["name"]: pkg for pkg in data}

    def scan(self) -> list[dict]:
        composer_packages = self._load_composer_packages()
        risk_db = self._load_risk_db()

        results = []

        for package in composer_packages:
            if package in risk_db:
                pkg_data = risk_db[package]
                results.append(
                    {
                        "name": package,
                        "score": pkg_data.get("score"),
                        "cves_count": pkg_data.get("cves_count"),
                        "abandoned": pkg_data.get("abandoned"),
                        "suggested": pkg_data.get("suggested_package"),
                    }
                )

        return results
