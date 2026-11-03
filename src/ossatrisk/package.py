from dataclasses import dataclass


@dataclass
class Package:
    name: str
    package_url: str
    description: str
    repository: str
    abandoned: bool
    maintainers_count: int
    downloads_total: int | None
    downloads_monthly: int | None
    downloads_daily: int | None
    favers: int | None
    github_stars: int | None
    github_forks: int | None
    github_open_issues: int | None
    dependents: int | None
    latest_release: str
    cves_count: int = 0
    suggested_package: str | None = None
    suggested_package_url: str | None = None
    score: float | None = None
    raw_score: float | None = None

    def to_dict(self):
        """Convert object to serializable dict"""
        return self.__dict__
