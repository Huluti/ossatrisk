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
    downloads_total: Optional[int]
    downloads_monthly: Optional[int]
    downloads_daily: Optional[int]
    favers: Optional[int]
    github_stars: Optional[int]
    github_forks: Optional[int]
    github_open_issues: Optional[int]
    dependents: Optional[int]
    latest_release: str
    cves_count: int = 0
    suggested_package: Optional[str] = None
    suggested_package_url: Optional[str] = None
    score: Optional[float] = None
    raw_score: Optional[float] = None

    def to_dict(self):
        """Convert object to serializable dict"""
        return self.__dict__
