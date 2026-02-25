import json
import math
import time
import numpy as np
from datetime import datetime, timedelta, timezone

import httpx

# CONFIG
MAX_PAGES = 15
EXCLUDED_PREFIXES = [
    "psr/",
    "psr-discovery/",
    "composer/",
]
EXCLUDED_PARTS = ["polyfill", "-compat", "_compat"]  # they are meant to be outdated
OUTPUT_FILE = "../data/php-packages.json"
POPULAR_URL = "https://packagist.org/explore/popular.json?per_page=100"
MONTHS_INACTIVE = 12


client = httpx.Client(http2=True)


def fetch_popular(url):
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def fetch_package_details(package_name):
    # --- Package info ---
    url = f"https://packagist.org/packages/{package_name}.json"
    response = client.get(url)
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

    # --- Fetch CVEs ---
    cves_count = 0
    try:
        sec_url = (
            f"https://packagist.org/api/security-advisories/?packages[]={package_name}"
        )
        sec_response = client.get(sec_url)
        sec_response.raise_for_status()
        sec_data = sec_response.json()
        advisories = sec_data.get("advisories", {}).get(package_name, [])
        cves_count = len(advisories)
    except Exception:
        pass  # default 0 if any error

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
        "cves_count": cves_count,
    }


def compute_score(pkg):
    """
    Compute a risk score where HIGHER score = higher risk.

    Factors:
    - Recency: older releases = higher risk
    - CVEs: more CVEs = higher risk
    - Maintainers: single maintainer = higher risk
    - Downloads: higher downloads = higher risk (more widely used → bigger impact)
    - Open GitHub issues: more open issues = higher risk
    """
    monthly = int(pkg.get("downloads_monthly") or 0)
    total_downloads = int(pkg.get("downloads_total") or 0)
    maintainers = int(pkg.get("maintainers_count") or 1)
    cves_count = int(pkg.get("cves_count") or 0)
    open_issues = int(pkg.get("github_open_issues") or 0)

    latest_str = pkg.get("latest_release") or ""

    # --- Recency risk ---
    recency_risk = 1.0
    if latest_str:
        try:
            latest_dt = datetime.fromisoformat(latest_str.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - latest_dt).days
            recency_risk += math.exp(days_since / 365)  # older = higher risk
        except Exception:
            recency_risk += 2  # fallback risk if date missing

    # Adjust recency risk based on open issues
    if open_issues <= 5:
        recency_risk *= 0.5  # lower importance if few issues
    elif open_issues > 20:
        recency_risk *= 1.2  # slightly higher if many issues

    # --- CVE risk ---
    cve_risk = 1 + cves_count * 2

    # --- Maintainer risk ---
    if maintainers <= 1:
        maintainer_risk = 3
    else:
        maintainer_risk = 1 + 1 / math.log(maintainers + 1)

    # --- Downloads risk ---
    download_risk = math.log1p(monthly + total_downloads)

    # --- Open issues risk ---
    issues_risk = 1 + open_issues * 0.5

    # --- Final risk score ---
    risk_score = recency_risk * cve_risk * maintainer_risk * download_risk * issues_risk
    return risk_score


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
            if any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
                continue

            if any(part in name for part in EXCLUDED_PARTS):
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
    raw_scores = np.array([p["score"] for p in all_packages])
    for i, p in enumerate(all_packages):
        p["raw_score"] = raw_scores[i]
        percentile = (raw_scores < raw_scores[i]).sum() / len(
            raw_scores
        )  # fraction of packages below
        p["score"] = max(1, round(percentile * 100))

    # Now sort packages descending by normalized score
    all_packages.sort(key=lambda p: p["score"], reverse=True)

    # Save minified JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_packages, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved {len(all_packages)} packages to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
