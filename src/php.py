import json
import math
import time
from datetime import datetime, timedelta, timezone

import requests

# CONFIG
MAX_PAGES = 15
EXCLUDE_PREFIXES = [
    "symfony/",
    "laravel/",
    "psr/",
    "composer/",
]  # generally well maintained packages
OUTPUT_FILE = "../data/php-packages.json"
POPULAR_URL = "https://packagist.org/explore/popular.json?per_page=100"
MONTHS_INACTIVE = 12


def fetch_popular(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_package_details(package_name):
    url = f"https://packagist.org/packages/{package_name}.json"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()["package"]

    versions = data.get("versions", {})

    # Find latest version by time
    latest_version = None
    latest_time_str = ""
    for version, info in versions.items():
        if "time" in info:
            if latest_time_str == "" or info["time"] > latest_time_str:
                latest_time_str = info["time"]
                latest_version = info

    downloads = data.get("downloads", {})
    maintainers_count = max(1, len(data.get("maintainers", {})))

    # Author email from latest version
    author_email = ""
    if latest_version:
        authors = latest_version.get("authors", [])
        if authors:
            author_email = authors[0].get("email", "")

    return {
        "name": data.get("name", ""),
        "package_url": f"https://packagist.org/packages/{package_name}",
        "description": data.get("description", ""),
        "repository": data.get("repository", ""),
        "abandoned": data.get("abandoned", False),
        "maintainers_count": maintainers_count,
        "author_email": author_email,
        "downloads_total": downloads.get("total", 0),
        "downloads_monthly": downloads.get("monthly", 0),
        "downloads_daily": downloads.get("daily", 0),
        "favers": data.get("favers", 0),
        "github_stars": data.get("github_stars", 0),
        "github_forks": data.get("github_forks", 0),
        "github_open_issues": data.get("github_open_issues", 0),
        "dependents": data.get("dependents", 0),
        "latest_release": latest_time_str,  # ISO string
    }


def compute_score(pkg):
    """
    Score = monthly downloads weighted by recency of last release
    and adjusted for maintainers count.
    Packages with only 1 maintainer are penalized.
    """
    monthly = pkg.get("downloads_monthly", 0)
    latest_str = pkg.get("latest_release")
    maintainers = pkg.get("maintainers_count")

    recency_factor = 1.0
    if latest_str:
        try:
            latest_dt = datetime.fromisoformat(latest_str.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - latest_dt).days
            # give more importance to recent releases, capped to 5 years
            recency_factor += max(
                0, (5 * 365 - days_since) / 365
            )  # max recency factor = 6
        except Exception:
            pass

    # logarithmic scaling for downloads
    base_score = math.log1p(monthly) * recency_factor

    # maintainers factor
    if maintainers <= 1:
        maintainers_factor = 0.5  # penalize single maintainer
    else:
        maintainers_factor = 1 + math.log(maintainers)  # increase with more maintainers

    final_score = base_score * maintainers_factor
    return final_score


def main():
    all_packages = []
    url = POPULAR_URL
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=MONTHS_INACTIVE * 30)
    page_count = 0

    while url and page_count < MAX_PAGES:
        page_count += 1
        print(f"Fetching popular packages (page {page_count}): {url}")
        data = fetch_popular(url)

        for pkg in data.get("packages", []):
            name = pkg["name"]
            if any(name.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
                continue

            try:
                details = fetch_package_details(name)
                if details["abandoned"]:
                    continue
            except Exception as e:
                print(f"Failed to fetch details for {name}: {e}")
                continue

            # Filter inactive packages (>12 months)
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

            # Compute score
            details["score"] = compute_score(details)

            all_packages.append(details)

        url = data.get("next")
        time.sleep(0.2)  # polite delay

    # After computing raw scores for all packages
    raw_scores = [compute_score(p) for p in all_packages]
    min_score = min(raw_scores)
    max_score = max(raw_scores)

    for i, p in enumerate(all_packages):
        p["raw_score"] = raw_scores[i]
        # normalized 0–100, but avoid 0 by using a small offset
        normalized = (raw_scores[i] - min_score) / (max_score - min_score) * 100
        p["score"] = max(1, round(normalized))  # ensure at least 1

    # Now sort packages descending by normalized score
    all_packages.sort(key=lambda p: p["score"], reverse=True)

    # Save minified JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_packages, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved {len(all_packages)} packages to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
