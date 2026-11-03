import asyncio
import contextlib
import re
from datetime import UTC, datetime, timedelta

from ..package import Package
from .base import BaseBuilder

# CONFIG
MAX_PAGES = 60
PAGE_SIZE = 50
EXCLUDED_PREFIXES = [
    "psr/",
    "psr-discovery/",
    "composer/",
]
EXCLUDED_PARTS = ["polyfill", "compat", "pack"]  # they are meant to be outdated
POPULAR_URL = f"https://packagist.org/explore/popular.json?per_page={PAGE_SIZE}"
PACKAGIST_URL = "https://packagist.org/packages/"


class PHPBuilder(BaseBuilder):
    @property
    def slug(self) -> str:
        return "php"

    async def fetch_popular(self, url):
        response = await self.client.safe_get(url)
        if not response:
            raise RuntimeError("Failed to fetch popular packages")
        return response.json()

    async def fetch_package_details(self, package_name) -> Package | None:
        # --- Package info ---
        url = f"https://packagist.org/packages/{package_name}.json"
        response = await self.client.safe_get(url)
        if not response:
            print(f"Failed to fetch package details for {package_name}")
            return None
        data = response.json()["package"]

        versions = data.get("versions", {})

        # Find latest version by time
        latest_time_str = ""
        for info in versions.values():
            if "time" in info and (
                latest_time_str == "" or info["time"] > latest_time_str
            ):
                latest_time_str = info["time"]

        downloads = data.get("downloads", {})
        maintainers_count = max(1, len(data.get("maintainers", {})))

        return Package(
            name=data.get("name", ""),
            package_url=f"{PACKAGIST_URL}{package_name}",
            description=data.get("description", ""),
            repository=data.get("repository", ""),
            abandoned=data.get("abandoned", False),
            maintainers_count=maintainers_count,
            downloads_total=downloads.get("total", 0),
            downloads_monthly=downloads.get("monthly", 0),
            downloads_daily=downloads.get("daily", 0),
            favers=data.get("favers", 0),
            github_stars=data.get("github_stars", 0),
            github_forks=data.get("github_forks", 0),
            github_open_issues=data.get("github_open_issues", 0),
            dependents=data.get("dependents", 0),
            latest_release=latest_time_str,
        )

    async def fetch_security_advisories_batch(self, package_names) -> dict:
        params = [("packages[]", name) for name in package_names]

        response = await self.client.safe_get(
            "https://packagist.org/api/security-advisories/",
            params=params,
        )
        if not response:
            print("Failed to fetch security advisories batch")
            return {}

        data = response.json()
        advisories_map = data.get("advisories", {})

        # Return dict: {package_name: cves_count}
        return {name: len(advisories_map.get(name, [])) for name in package_names}

    def excluded_package(self, name):
        if any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            return True

        return bool(
            re.search(
                r"(?:^|[-_/])(" + "|".join(EXCLUDED_PARTS) + r")(?:$|[-_/])",
                name,
            )
        )

    async def _safe_details(self, name: str) -> Package | None:
        try:
            return await self.fetch_package_details(name)
        except (ValueError, TypeError, KeyError) as e:
            print(f"- Failed to fetch details for {name}: {e}")
            return None

    def run(self):
        asyncio.run(self._run_async())

    async def _run_async(self):
        all_packages = []
        url = POPULAR_URL
        # Take only packages with a release date older than one year
        cutoff_date = datetime.now(UTC) - timedelta(days=365)
        page_count = 0

        suggestions = self.load_suggestions()

        while url and page_count < MAX_PAGES:
            page_count += 1
            print(f"Fetching popular packages (page {page_count}): {url}")
            data = await self.fetch_popular(url)

            # --- Fetch package details concurrently ---
            names = [
                pkg["name"]
                for pkg in data.get("packages", [])
                if not self.excluded_package(pkg["name"])
            ]

            details_list = await asyncio.gather(*(self._safe_details(n) for n in names))

            packages_this_page = []
            for name, details in zip(names, details_list):
                if not details or details.abandoned:
                    continue

                # --- Add suggested replacement if any ---
                if name in suggestions:
                    details.suggested_package = suggestions[name]
                    details.suggested_package_url = (
                        f"{PACKAGIST_URL}{suggestions[name]}"
                    )

                packages_this_page.append(details)

            # --- Batch CVE fetch ---
            package_names = [p.name for p in packages_this_page]

            if package_names:
                cves_count = await self.fetch_security_advisories_batch(package_names)
                for p in packages_this_page:
                    p.cves_count = cves_count.get(p.name, 0)

            # --- Filter inactive + compute score ---
            for details in packages_this_page:
                latest_release_str = details.latest_release

                if latest_release_str:
                    skip = False
                    with contextlib.suppress(ValueError, TypeError):
                        latest_release_dt = datetime.fromisoformat(latest_release_str)
                        skip = latest_release_dt > cutoff_date
                    if skip:
                        print("- Ignored package (release date):", details.name)
                        continue  # skip active packages

                # Skip packages with no open issues AND no CVEs
                if details.github_open_issues == 0 and details.cves_count == 0:
                    print("- Ignored package (issues and CVEs):", details.name)
                    continue

                details.score = self.compute_score(details)
                all_packages.append(details)

            url = data.get("next")

        self.write_file(all_packages)
