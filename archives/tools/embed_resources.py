#!/usr/bin/env python3
"""Create a C++ header with gzip-compressed embedded resources."""

from __future__ import annotations

import argparse
import gzip
import re
from pathlib import Path


def ident(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_").lower()


def byte_array(data: bytes) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = ", ".join(f"0x{b:02x}" for b in data[i : i + 16])
        lines.append(f"    {chunk},")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    resources: list[tuple[str, bytes, bytes]] = []

    story = root / "assets" / "story.gal"
    resources.append(("story.gal", story.read_bytes(), gzip.compress(story.read_bytes(), compresslevel=9)))

    for path in sorted((root / "ansi_art").glob("*.ans")):
        raw = path.read_bytes()
        resources.append((f"ansi_art/{path.name}", raw, gzip.compress(raw, compresslevel=9)))

    out = [
        "#pragma once",
        "#include <cstddef>",
        "#include <cstdint>",
        "",
        "namespace artygal::embedded {",
        "struct Resource {",
        "  const char* name;",
        "  const std::uint8_t* gzip_data;",
        "  std::size_t gzip_size;",
        "  std::size_t original_size;",
        "};",
        "",
    ]

    table = []
    for name, raw, compressed in resources:
        var = f"res_{ident(name)}"
        out.append(f"inline constexpr std::uint8_t {var}[] = {{")
        out.append(byte_array(compressed))
        out.append("};")
        out.append("")
        table.append(f'  {{"{name}", {var}, sizeof({var}), {len(raw)}}},')

    out.append("inline constexpr Resource kResources[] = {")
    out.extend(table)
    out.append("};")
    out.append("}  // namespace artygal::embedded")
    out.append("")

    args.out.write_text("\n".join(out), encoding="utf-8")
    total_raw = sum(len(raw) for _, raw, _ in resources)
    total_gzip = sum(len(comp) for _, _, comp in resources)
    print(f"embedded {len(resources)} resources: {total_raw} -> {total_gzip} bytes")


if __name__ == "__main__":
    main()
