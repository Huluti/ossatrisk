import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

from ..package import Package

from .base import BaseBuilder

# CONFIG
MAX_PAGES = 4
PAGE_SIZE = 250
EXCLUDED_PREFIXES = [
    "@types/",
]
EXCLUDED_PARTS = ["polyfill", "compat"]  # they are meant to be outdated
NPM_URL = "https://www.npmjs.com/package/"
REGISTRY_URL = "https://registry.npmjs.org/"
DOWNLOADS_URL = "https://api.npmjs.org/downloads/"
NPMS_SEARCH_URL = "https://api.npms.io/v2/search"
OSV_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"


class JSBuilder(BaseBuilder):
    @property
    def slug(self) -> str:
        return "js"

    def fetch_popular(self, from_offset: int):
        response = self.client.safe_get(
            NPMS_SEARCH_URL,
            params={"size": PAGE_SIZE, "from": from_offset, "q": "not:deprecated"},
        )
        if not response:
            raise Exception("Failed to fetch popular packages")
        return response.json()

    def _get_with_retry(self, url: str, attempts: int = 3):
        # npm APIs rate-limit aggressively; back off and retry before giving up
        for i in range(attempts):
            response = self.client.safe_get(url)
            if response is not None:
                return response
            if i < attempts - 1:
                time.sleep(1 + i)
        return None

    def _downloads_point(self, period: str, package_name: str) -> Optional[int]:
        response = self._get_with_retry(f"{DOWNLOADS_URL}point/{period}/{package_name}")
        if not response:
            return None
        return int(response.json().get("downloads", 0))

    def _downloads_range_year(self, package_name: str) -> Optional[int]:
        # npm has no all-time point query and the full range is too heavy per
        # package, so total = trailing 365 days
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=365)
        response = self._get_with_retry(f"{DOWNLOADS_URL}range/{start}:{end}/{package_name}")
        if not response:
            return None
        return sum(int(d.get("downloads", 0)) for d in response.json().get("downloads", []))

    def fetch_downloads(self, package_name: str):
        monthly = self._downloads_point("last-month", package_name)
        daily = self._downloads_point("last-day", package_name)
        total = self._downloads_range_year(package_name)
        if total is None:
            total = monthly
        return total, monthly, daily

    def _normalize_repository(self, repository) -> str:
        if not repository:
            return ""
        url = repository.get("url", "") if isinstance(repository, dict) else str(repository)
        url = url.replace("git+", "").replace("git://", "https://")
        url = re.sub(r"^git@([^:]+):", r"https://\1/", url)
        url = url.removesuffix(".git")
        if not url.startswith("http"):
            return ""
        return url

    def fetch_package_details(self, package_name) -> Optional[Package]:
        # Full packument (not the abbreviated one) to get maintainers/repository/time
        url = f"{REGISTRY_URL}{quote(package_name, safe='@')}"
        response = self._get_with_retry(url)
        if not response:
            print(f"Failed to fetch package details for {package_name}")
            return None
        data = response.json()

        latest_version = data.get("dist-tags", {}).get("latest", "")
        latest_info = data.get("versions", {}).get(latest_version, {})
        times = data.get("time", {})
        latest_time = times.get(latest_version) or data.get("modified") or ""

        # npm has no "abandoned" flag; a deprecated latest version is the closest signal
        abandoned = bool(latest_info.get("deprecated"))

        downloads_total, downloads_monthly, downloads_daily = self.fetch_downloads(package_name)

        # Stars/forks/open issues and dependents are not available without the
        # GitHub API or a keyed service, so they stay None and the website
        # renders them as unavailable
        return Package(
            name=data.get("name", package_name),
            package_url=f"{NPM_URL}{package_name}",
            description=data.get("description") or "",
            repository=self._normalize_repository(data.get("repository")),
            abandoned=abandoned,
            maintainers_count=max(1, len(data.get("maintainers") or [])),
            downloads_total=downloads_total,
            downloads_monthly=downloads_monthly,
            downloads_daily=downloads_daily,
            favers=None,
            github_stars=None,
            github_forks=None,
            github_open_issues=None,
            dependents=None,
            latest_release=latest_time,
        )

    def fetch_security_advisories_batch(self, package_names) -> dict:
        if not package_names:
            return {}

        response = self.client.safe_post(
            OSV_QUERYBATCH_URL,
            json={
                "queries": [
                    {"package": {"name": name, "ecosystem": "npm"}}
                    for name in package_names
                ]
            },
        )
        if not response:
            print("Failed to fetch security advisories batch")
            return {name: 0 for name in package_names}

        results = response.json().get("results", [])
        return {
            name: len(results[i].get("vulns", [])) if i < len(results) else 0
            for i, name in enumerate(package_names)
        }

    def excluded_package(self, name):
        if any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            return True

        if re.search(
            r"(?:^|[-_/@])(" + "|".join(EXCLUDED_PARTS) + r")(?:$|[-_/])",
            name,
        ):
            return True

        return False

    def run(self):
        all_packages = []
        # Take only packages with a release date older than one year
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
        page_count = 0
        from_offset = 0

        suggestions = self.load_suggestions()

        while page_count < MAX_PAGES:
            page_count += 1
            print(f"Fetching popular packages (page {page_count}): offset {from_offset}")
            data = self.fetch_popular(from_offset)

            results = data.get("results", [])
            if not results:
                break

            packages_this_page = []

            # --- Fetch package details first ---
            for item in results:
                name = item.get("package", {}).get("name", "")
                if not name or self.excluded_package(name):
                    continue

                try:
                    details = self.fetch_package_details(name)
                    if not details or details.abandoned:
                        continue
                except Exception as e:
                    print(f"- Failed to fetch details for {name}: {e}")
                    continue

                # --- Add suggested replacement if any ---
                if name in suggestions:
                    details.suggested_package = suggestions[name]
                    details.suggested_package_url = f"{NPM_URL}{suggestions[name]}"

                packages_this_page.append(details)

            # --- Batch CVE fetch ---
            package_names = [p.name for p in packages_this_page]

            if package_names:
                cves_count = self.fetch_security_advisories_batch(package_names)
                for p in packages_this_page:
                    p.cves_count = cves_count.get(p.name, 0)

            # --- Filter inactive + compute score ---
            for details in packages_this_page:
                latest_release_str = details.latest_release

                if latest_release_str:
                    try:
                        latest_release_dt = datetime.fromisoformat(
                            latest_release_str.replace("Z", "+00:00")
                        )
                        if latest_release_dt > cutoff_date:
                            print("- Ignored package (release date):", details.name)
                            continue  # skip active packages
                    except Exception:
                        pass

                # Open issues are unavailable without the GitHub API, so keep
                # only packages with at least one CVE
                if details.cves_count == 0:
                    print("- Ignored package (no CVEs):", details.name)
                    continue

                details.score = self.compute_score(details)
                all_packages.append(details)

            from_offset += len(results)
            if len(results) < PAGE_SIZE:
                break

        self.write_file(all_packages)
