import re
from datetime import datetime, timedelta, timezone

from base import Base
from package import Package

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


class PHP(Base):
    def fetch_popular(self, url):
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def fetch_package_details(self, package_name):
        # --- Package info ---
        url = f"https://packagist.org/packages/{package_name}.json"
        response = self.client.get(url)
        response.raise_for_status()
        data = response.json()["package"]

        versions = data.get("versions", {})

        # Find latest version by time
        latest_time_str = ""
        for version, info in versions.items():
            if "time" in info:
                if latest_time_str == "" or info["time"] > latest_time_str:
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

    def fetch_security_advisories_batch(self, package_names):
        params = [("packages[]", name) for name in package_names]

        response = self.client.get(
            "https://packagist.org/api/security-advisories/",
            params=params,
        )
        response.raise_for_status()

        data = response.json()
        advisories_map = data.get("advisories", {})

        # Return dict: {package_name: cves_count}
        return {name: len(advisories_map.get(name, [])) for name in package_names}

    def excluded_package(self, name):
        if any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            return True

        if re.search(
            r"(?:^|[-_/])(" + "|".join(EXCLUDED_PARTS) + r")(?:$|[-_/])",
            name,
        ):
            return True

        return False

    def run(self):
        all_packages = []
        url = POPULAR_URL
        # Take only packages with a release date older than one year
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
        page_count = 0

        suggestions = self.load_suggestions()

        while url and page_count < MAX_PAGES:
            page_count += 1
            print(f"Fetching popular packages (page {page_count}): {url}")
            data = self.fetch_popular(url)

            packages_this_page = []

            # --- Fetch package details first ---
            for pkg in data.get("packages", []):
                name = pkg["name"]
                if self.excluded_package(name):
                    continue

                try:
                    details = self.fetch_package_details(name)
                    if details.abandoned:
                        continue
                except Exception as e:
                    print(f"- Failed to fetch details for {name}: {e}")
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
                try:
                    cves_count = self.fetch_security_advisories_batch(package_names)
                    for p in packages_this_page:
                        p.cves_count = cves_count.get(p.name, 0)
                except Exception as e:
                    print(f"- Failed to fetch security advisories batch: {e}")

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

                # Skip packages with no open issues AND no CVEs
                if details.github_open_issues == 0 and details.cves_count == 0:
                    print("- Ignored package (issues and CVEs):", details.name)
                    continue

                details.score = self.compute_score(details)
                all_packages.append(details)

            url = data.get("next")

        self.write_file(all_packages)
