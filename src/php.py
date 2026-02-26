import json
import numpy as np
from datetime import datetime, timedelta, timezone

from base import Base

# CONFIG
MAX_PAGES = 30
EXCLUDED_PREFIXES = [
    "psr/",
    "psr-discovery/",
    "composer/",
]
EXCLUDED_PARTS = ["polyfill", "-compat", "_compat"]  # they are meant to be outdated
OUTPUT_FILE = "../data/php-packages.json"
POPULAR_URL = "https://packagist.org/explore/popular.json?per_page=50"
MONTHS_INACTIVE = 12


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

        return {
            "name": data.get("name", ""),
            "package_url": f"https://packagist.org/packages/{package_name}",
            "description": data.get("description", ""),
            "repository": data.get("repository", ""),
            "abandoned": data.get("abandoned", False),
            "maintainers_count": maintainers_count,
            "downloads_total": downloads.get("total", 0),
            "downloads_monthly": downloads.get("monthly", 0),
            "downloads_daily": downloads.get("daily", 0),
            "favers": data.get("favers", 0),
            "github_stars": data.get("github_stars", 0),
            "github_forks": data.get("github_forks", 0),
            "github_open_issues": data.get("github_open_issues", 0),
            "dependents": data.get("dependents", 0),
            "latest_release": latest_time_str,
            "cves_count": 0,
        }

    def fetch_security_advisories_batch(self, package_names):
        params = [("packages[]", name) for name in package_names]

        response = self.client.get(
            "https://packagist.org/api/security-advisories/",
            params=params,
        )
        response.raise_for_status()

        data = response.json()
        advisories_map = data.get("advisories", {})

        # Return dict: {package_name: cve_count}
        return {name: len(advisories_map.get(name, [])) for name in package_names}

    def run(self):
        all_packages = []
        url = POPULAR_URL
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=MONTHS_INACTIVE * 30)
        page_count = 0

        while url and page_count < MAX_PAGES:
            page_count += 1
            print(f"Fetching popular packages (page {page_count}): {url}")
            data = self.fetch_popular(url)

            packages_this_page = []

            # --- Fetch package details first ---
            for pkg in data.get("packages", []):
                name = pkg["name"]

                if any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
                    continue

                if any(part in name for part in EXCLUDED_PARTS):
                    continue

                try:
                    details = self.fetch_package_details(name)
                    if details["abandoned"]:
                        continue
                except Exception as e:
                    print(f"Failed to fetch details for {name}: {e}")
                    continue

                packages_this_page.append(details)

            # --- Batch CVE fetch ---
            package_names = [p["name"] for p in packages_this_page]

            if package_names:
                try:
                    cve_counts = self.fetch_security_advisories_batch(package_names)
                    for p in packages_this_page:
                        p["cves_count"] = cve_counts.get(p["name"], 0)
                except Exception as e:
                    print(f"Failed to fetch security advisories batch: {e}")

            # --- Filter inactive + compute score ---
            for details in packages_this_page:
                latest_release_str = details.get("latest_release")

                if latest_release_str:
                    try:
                        latest_release_dt = datetime.fromisoformat(
                            latest_release_str.replace("Z", "+00:00")
                        )
                        if latest_release_dt > cutoff_date:
                            continue  # skip active packages
                    except Exception:
                        pass

                details["score"] = self.compute_score(details)
                all_packages.append(details)

            url = data.get("next")

        # --- Normalize scores ---
        raw_scores = np.array([p["score"] for p in all_packages])

        for i, p in enumerate(all_packages):
            p["raw_score"] = raw_scores[i]
            percentile = (raw_scores < raw_scores[i]).sum() / len(raw_scores)
            p["score"] = max(1, round(percentile * 100))

        # --- Sort descending by normalized score  ---
        all_packages.sort(key=lambda p: p["score"], reverse=True)

        # --- Save minified JSON ---
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_packages, f, ensure_ascii=False, separators=(",", ":"))

        print(f"Saved {len(all_packages)} packages to {OUTPUT_FILE}")
