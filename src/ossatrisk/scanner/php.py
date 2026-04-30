import json
from pathlib import Path
from .base import BaseScanner


class PHPScanner(BaseScanner):
    DATA_URL = (
        "https://raw.githubusercontent.com/Huluti/ossatrisk/main/data/php-packages.json"
    )
    CACHE_FILENAME = "php-packages.json"

    def __init__(self):
        super().__init__()

        self.composer_file = self._find_composer_file()
        if not self.composer_file:
            raise FileNotFoundError(
                "composer.json not found in current folder or any parent directories"
            )

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

    def scan(self) -> list[dict]:
        composer_packages = self._load_composer_packages()
        risk_db = self._load_risk_db()
        if len(risk_db) == 0:
            raise Exception("Failed to load risk database")

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
