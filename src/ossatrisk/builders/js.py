import asyncio
import contextlib
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from ..package import Package
from .base import BaseBuilder

# CONFIG
MAX_PAGES = 4
PAGE_SIZE = 250
DOWNLOADS_CONCURRENCY = 4  # api.npmjs.org rate-limits hard under load
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

    async def fetch_popular(self, from_offset: int):
        response = await self.client.safe_get(
            NPMS_SEARCH_URL,
            params={"size": PAGE_SIZE, "from": from_offset, "q": "not:deprecated"},
        )
        if not response:
            raise RuntimeError("Failed to fetch popular packages")
        return response.json()

    async def _downloads_point(self, period: str, package_name: str) -> int | None:
        response = await self.client.safe_get(
            f"{DOWNLOADS_URL}point/{period}/{package_name}"
        )
        if not response:
            return None
        return int(response.json().get("downloads", 0))

    async def _downloads_range_year(self, package_name: str) -> int | None:
        # npm has no all-time point query and the full range is too heavy per
        # package, so total = trailing 365 days
        end = datetime.now(UTC).date()
        start = end - timedelta(days=365)
        response = await self.client.safe_get(
            f"{DOWNLOADS_URL}range/{start}:{end}/{package_name}"
        )
        if not response:
            return None
        return sum(
            int(d.get("downloads", 0)) for d in response.json().get("downloads", [])
        )

    async def fetch_downloads(self, package_name: str):
        # daily downloads are not used downstream, so only fetch monthly + total
        monthly, total = await asyncio.gather(
            self._downloads_point("last-month", package_name),
            self._downloads_range_year(package_name),
        )
        if total is None:
            total = monthly
        return total, monthly

    def _normalize_repository(self, repository) -> str:
        if not repository:
            return ""
        url = (
            repository.get("url", "")
            if isinstance(repository, dict)
            else str(repository)
        )
        url = url.replace("git+", "").replace("git://", "https://")
        url = re.sub(r"^git@([^:]+):", r"https://\1/", url)
        url = url.removesuffix(".git")
        if not url.startswith("http"):
            return ""
        return url

    async def fetch_packument(self, package_name: str) -> dict | None:
        # Full packument (not the abbreviated one) to get maintainers/repository/time
        url = f"{REGISTRY_URL}{quote(package_name, safe='@')}"
        response = await self.client.safe_get(url)
        if not response:
            return None
        return response.json()

    async def _safe_packument(self, name: str) -> dict | None:
        try:
            return await self.fetch_packument(name)
        except (ValueError, TypeError, KeyError) as e:
            print(f"- Failed to fetch details for {name}: {e}")
            return None

    def build_package(self, package_name: str, data: dict) -> Package:
        latest_version = data.get("dist-tags", {}).get("latest", "")
        latest_info = data.get("versions", {}).get(latest_version, {})
        times = data.get("time", {})
        latest_time = times.get(latest_version) or data.get("modified") or ""

        # npm has no "abandoned" flag; a deprecated latest version is the closest signal
        abandoned = bool(latest_info.get("deprecated"))

        # Stars/forks/open issues and dependents are not available without the
        # GitHub API or a keyed service, so they stay None and the website
        # renders them as unavailable. Downloads are fetched later, only for
        # packages that survive the filters, because api.npmjs.org is the
        # most rate-limited endpoint.
        return Package(
            name=data.get("name", package_name),
            package_url=f"{NPM_URL}{package_name}",
            description=data.get("description") or "",
            repository=self._normalize_repository(data.get("repository")),
            abandoned=abandoned,
            maintainers_count=max(1, len(data.get("maintainers") or [])),
            downloads_total=None,
            downloads_monthly=None,
            downloads_daily=None,
            favers=None,
            github_stars=None,
            github_forks=None,
            github_open_issues=None,
            dependents=None,
            latest_release=latest_time,
        )

    async def fetch_security_advisories_batch(self, package_names) -> dict:
        if not package_names:
            return {}

        response = await self.client.safe_post(
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

        return bool(
            re.search(
                r"(?:^|[-_/@])(" + "|".join(EXCLUDED_PARTS) + r")(?:$|[-_/])",
                name,
            )
        )

    def run(self):
        asyncio.run(self._run_async())

    async def _run_async(self):
        all_packages = []
        # Take only packages with a release date older than one year
        cutoff_date = datetime.now(UTC) - timedelta(days=365)
        page_count = 0
        from_offset = 0

        suggestions = self.load_suggestions()
        downloads_sem = asyncio.Semaphore(DOWNLOADS_CONCURRENCY)

        while page_count < MAX_PAGES:
            page_count += 1
            print(
                f"Fetching popular packages (page {page_count}): offset {from_offset}"
            )
            data = await self.fetch_popular(from_offset)

            results = data.get("results", [])
            if not results:
                break

            # --- Fetch packuments concurrently (registry.npmjs.org is lenient) ---
            names = [item.get("package", {}).get("name", "") for item in results]
            names = [n for n in names if n and not self.excluded_package(n)]

            packuments = await asyncio.gather(*(self._safe_packument(n) for n in names))
            pairs = [(n, d) for n, d in zip(names, packuments) if d]

            # --- Batch CVE fetch for all candidates at once ---
            cves_count = (
                await self.fetch_security_advisories_batch([n for n, _ in pairs])
                if pairs
                else {}
            )

            # --- Filter on cheap signals before any downloads call ---
            packages_this_page = []
            for name, packument in pairs:
                details = self.build_package(name, packument)
                if details.abandoned:
                    continue

                details.cves_count = cves_count.get(name, 0)

                latest_release_str = details.latest_release
                if latest_release_str:
                    skip = False
                    with contextlib.suppress(ValueError, TypeError):
                        latest_release_dt = datetime.fromisoformat(latest_release_str)
                        skip = latest_release_dt > cutoff_date
                    if skip:
                        print("- Ignored package (release date):", details.name)
                        continue  # skip active packages

                # Open issues are unavailable without the GitHub API, so keep
                # only packages with at least one CVE
                if details.cves_count == 0:
                    print("- Ignored package (no CVEs):", details.name)
                    continue

                # --- Add suggested replacement if any ---
                if name in suggestions:
                    details.suggested_package = suggestions[name]
                    details.suggested_package_url = f"{NPM_URL}{suggestions[name]}"

                packages_this_page.append(details)

            # --- Downloads only for survivors, at low concurrency ---
            async def with_downloads(p: Package) -> Package:
                async with downloads_sem:
                    total, monthly = await self.fetch_downloads(p.name)
                p.downloads_total = total
                p.downloads_monthly = monthly
                return p

            if packages_this_page:
                packages_this_page = list(
                    await asyncio.gather(
                        *(with_downloads(p) for p in packages_this_page)
                    )
                )

            for details in packages_this_page:
                details.score = self.compute_score(details)
                all_packages.append(details)

            from_offset += len(results)
            if len(results) < PAGE_SIZE:
                break

        self.write_file(all_packages)
