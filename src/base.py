import httpx
import math
import json
import numpy as np

from datetime import datetime, timezone

from package import Package


OUTPUT_FOLDER = "../data/"


class Base:
    def __init__(self):
        self.client = httpx.Client(http2=True)

    def compute_score(self, pkg: Package):
        """
        Compute a risk score where HIGHER score = higher risk.

        Factors:
        - Recency: older releases = higher risk
        - CVEs: more CVEs = higher risk
        - Maintainers: single maintainer = higher risk
        - Downloads: higher downloads = higher risk (more widely used → bigger impact)
        - Open GitHub issues: more open issues = higher risk
        """
        monthly = int(pkg.downloads_monthly or 0)
        total_downloads = int(pkg.downloads_total or 0)
        maintainers = int(pkg.maintainers_count or 1)
        cves_count = int(pkg.cves_count or 0)
        open_issues = int(pkg.github_open_issues or 0)

        latest_str = pkg.latest_release or ""

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
        risk_score = (
            recency_risk * cve_risk * maintainer_risk * download_risk * issues_risk
        )
        return risk_score

    def write_file(self, packages):
        # --- Normalize scores ---
        raw_scores = np.array([p.score for p in packages])

        for i, p in enumerate(packages):
            p.raw_score = raw_scores[i]
            percentile = (raw_scores < raw_scores[i]).sum() / len(raw_scores)
            p.score = max(1, round(percentile * 100))

        # --- Sort descending by normalized score  ---
        packages.sort(key=lambda p: p.score, reverse=True)

        # --- Save minified JSON ---
        output =  f"{OUTPUT_FOLDER}{self.__class__.__name__.lower()}-packages.json"
        with open(output, "w", encoding="utf-8") as f:
            json.dump(
                [p.to_dict() for p in packages],
                f,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        print(f"Saved {len(packages)} packages to {output}")
