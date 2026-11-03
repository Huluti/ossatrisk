import json
from pathlib import Path
from .base import BaseScanner


class JSScanner(BaseScanner):
    DATA_URL = (
        "https://raw.githubusercontent.com/Huluti/ossatrisk/main/data/js-packages.json"
    )
    CACHE_FILENAME = "js-packages.json"

    def __init__(self):
        super().__init__()

        self.package_file = self._find_package_file()
        if not self.package_file:
            raise FileNotFoundError(
                "package.json not found in current folder or any parent directories"
            )

    def _find_package_file(self) -> Path | None:
        """Search current folder and parents for package.json"""
        path = self.project_path
        while path != path.parent:
            candidate = path / "package.json"
            if candidate.exists():
                return candidate
            path = path.parent
        return None

    def _load_dependencies(self) -> set[str]:
        if self.package_file is None:
            raise FileNotFoundError(
                "package.json not found in current folder or any parent directories"
            )
        with open(self.package_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        deps = {}
        for key in ("dependencies", "devDependencies", "optionalDependencies"):
            deps.update(data.get(key, {}))
        return set(deps.keys())

    def scan(self) -> list[dict]:
        dependencies = self._load_dependencies()
        risk_db = self._load_risk_db()
        if len(risk_db) == 0:
            raise Exception("Failed to load risk database")

        results = []

        for package in dependencies:
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
