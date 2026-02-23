# ossatrisk

**ossatrisk** surfaces widely-used open source packages that carry silent risk:
abandoned maintenance, unpatched CVEs, or single-maintainer bus factor.

Starting with the **PHP ecosystem**. More ecosystems planned.

## Risk signals tracked

| Signal |
|---|
| No activity for 6+ months |
| Known unpatched CVEs |
| Single maintainer |
| High dependents count |

A package is flagged when it scores high on at least one signal **and** is widely depended upon - obscure abandoned packages are not the target.

## Contributing

Contributions welcome - especially:
- Adding packages to the watchlist
- Improving the scoring logic
- Adding new ecosystems

## License

MIT
