"""Capture a fully pinned transitive runtime lock from the reviewed development environment."""

from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def main() -> None:
    pending = [Requirement(line) for line in Path("requirements.in").read_text().splitlines() if line]
    seen: set[tuple[str, tuple[str, ...]]] = set()
    versions: dict[str, str] = {}
    while pending:
        req = pending.pop()
        name = canonicalize_name(req.name)
        key = (name, tuple(sorted(req.extras)))
        if key in seen:
            continue
        seen.add(key)
        dist = distribution(name)
        versions[name] = dist.version
        for dependency in dist.requires or []:
            child = Requirement(dependency)
            if child.marker is None or any(
                child.marker.evaluate({"extra": extra}) for extra in (req.extras or {""})
            ):
                pending.append(child)
    Path("requirements.lock").write_text(
        "# Exact runtime resolution; Python 3.10. Refresh deliberately and rerun CI.\n"
        + "\n".join(f"{name}=={version}" for name, version in sorted(versions.items()))
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
