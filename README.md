# ossatrisk

**ossatrisk** surfaces widely-used open source packages with hidden risks, like abandoned maintenance, unpatched CVEs, or a single-maintainer bus factor.

Only packages with high impact and broad usage are flagged.

The goal is not to name and shame, but to understand the ecosystem and suggest remediation—contacting maintainers, contributing fixes, or forking when needed.

- Starting with the **PHP ecosystem**. More ecosystems planned.
- Datasets are updated daily.

## Package Risk Assessment Algorithm

This project evaluates the **risk level of software packages** based on several key factors, helping developers identify dependencies that may pose potential stability or security issues.

### 1. Package Selection

1. We **fetch popular packages** from public package registries (e.g., Packagist, PyPI, npm).
2. From these, we **filter packages that have not had a release in the last 12 months**, as older packages are generally more likely to have maintenance or security issues. Only these packages are considered for risk scoring.

### 2. Risk Scoring Algorithm

For each selected package, a **risk score** is computed where higher scores indicate higher risk. The algorithm considers multiple factors:

| Factor                    | Description                                                             | Weight / Logic                                                                                                                                                                                                |
| ------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Recency**               | Time since the latest release                                           | Older releases are riskier. The risk increases exponentially with age. If the package has very few open issues, recency is weighted less. If the package has many open issues, recency is slightly increased. |
| **Known Vulnerabilities** | Number of publicly reported security vulnerabilities (CVEs, advisories) | Each vulnerability significantly increases the risk.                                                                                                                                                          |
| **Maintainers**           | Number of maintainers contributing to the package                       | Packages with few maintainers are considered riskier. Risk decreases as the number of maintainers increases.                                                                                                  |
| **Popularity**            | Downloads or usage metrics                                              | Highly used packages have larger potential impact if issues arise. Risk is scaled logarithmically with download counts or usage statistics.                                                                   |
| **Open Issues**           | Number of unresolved issues in the package repository                   | More open issues indicate potential instability or lack of maintenance.                                                                                                                                       |

### 3. Risk Score Calculation

The final **risk score** is calculated as:

```text
risk_score = recency_risk * vulnerability_risk * maintainer_risk * popularity_risk * issues_risk
```

This approach ensures that packages which are **older, have known vulnerabilities, few maintainers, widely used, and many unresolved issues** receive higher scores, flagging them as higher-risk dependencies.

## Contributing

Contributions welcome - especially:

- Improving the scoring logic
- Improving the project structure
- Adding new ecosystems

## Stargazers over time
[![Stargazers over time](https://starchart.cc/Huluti/ossatrisk.svg?variant=adaptive)](https://starchart.cc/Huluti/ossatrisk)

## License

MIT
