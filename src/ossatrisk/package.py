from dataclasses import dataclass
from typing import Optional


@dataclass
class Package:
    name: str
    package_url: str
    description: str
    repository: str
    abandoned: bool
    maintainers_count: int
    downloads_total: int
    downloads_monthly: int
    downloads_daily: int
    favers: int
    github_stars: int
    github_forks: int
    github_open_issues: int
    dependents: int
    latest_release: str
    cves_count: int = 0
    suggested_package: Optional[str] = None
    suggested_package_url: Optional[str] = None
    score: Optional[float] = None
    raw_score: Optional[float] = None

    def to_dict(self):
        """Convert object to serializable dict"""
        return self.__dict__
