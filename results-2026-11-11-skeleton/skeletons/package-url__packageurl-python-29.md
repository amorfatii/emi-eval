# Skeleton change
- ADD `src/packageurl/__init__.py::PackageURL.__hash__(self) -> int` — returns a hash derived from the canonical purl string (`to_string()`), so equal PackageURLs hash equally and instances can live in sets/dict keys despite the `qualifiers` field being a dict
