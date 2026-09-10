#!/usr/bin/env python3
"""Replace registry.redhat.io image repositories in the bundle CSV with Konflux mirrors."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


MAPPING_ENTRY = re.compile(
    r"^\s*-\s+mirrors:\s*$\n"
    r"\s+-\s+(?P<mirror>[^\s#]+)\s*$\n"
    r"\s+source:\s+(?P<source>[^\s#]+)\s*$",
    re.MULTILINE,
)
IMAGE_REFERENCE = re.compile(r"(?P<repository>[^\s'\"]+)@(?P<digest>sha256:[0-9a-fA-F]{64})")


def read_mapping(path: Path) -> dict[str, str]:
    """Read source-to-mirror pairs from the ImageDigestMirrorSet YAML."""
    text = path.read_text(encoding="utf-8")
    mapping = {
        match.group("source"): match.group("mirror")
        for match in MAPPING_ENTRY.finditer(text)
    }
    if not mapping:
        raise ValueError(f"no mirror mappings found in {path}")
    return mapping


def replace_images(csv: str, mapping: dict[str, str]) -> tuple[str, int]:
    """Replace mapped repositories while leaving image digests unchanged."""
    replacements = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacements
        repository = match.group("repository")
        mirror = mapping.get(repository)
        if mirror is None:
            return match.group(0)
        replacements += 1
        return f"{mirror}@{match.group('digest')}"

    return IMAGE_REFERENCE.sub(replace, csv), replacements


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace mapped registry.redhat.io image repositories in an operator bundle CSV with Konflux mirrors."
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path(".tekton/images-mirror-set.yaml"),
        help="ImageDigestMirrorSet YAML (default: .tekton/images-mirror-set.yaml)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("bundle/manifests/serverless-functions.clusterserviceversion.yaml"),
        help="Bundle CSV to update",
    )
    args = parser.parse_args()

    mapping = read_mapping(args.mapping)
    original = args.csv.read_text(encoding="utf-8")
    updated, replacements = replace_images(original, mapping)
    args.csv.write_text(updated, encoding="utf-8")
    print(f"replaced {replacements} image reference(s) in {args.csv}")


if __name__ == "__main__":
    main()
