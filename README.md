# ossatrisk

**ossatrisk** surfaces widely-used open source packages that carry silent risk:
abandoned maintenance, unpatched CVEs, or single-maintainer bus factor.

Starting with the **PHP ecosystem**. More ecosystems planned.

## Risk signals tracked

| Signal | Ready |
|---|---|
| No activity for 12+ months | ✔️|
| Known unpatched CVEs | ❌ |
| Single maintainer | ✔️|

A package is flagged when it scores high on at least one signal **and** is widely depended upon - obscure abandoned packages are not the target.

## Contributing

Contributions welcome - especially:
- Improving the scoring logic
- Improving the project structure
- Adding new ecosystems

## License

MIT
