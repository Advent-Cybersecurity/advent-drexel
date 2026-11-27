"""Create the current Project Drexel evidence snapshot for one Zenodo deposit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
VERSION = "v0.4"
CORE_FILES = (
    "paper/drexel-feasibility-v0.4.pdf",
    "paper/drexel-feasibility-v0.4.tex",
    "paper/README.md",
    "paper/make_zenodo_bundle.py",
    "README.md",
)
EVIDENCE_DIRS = ("docs", "data", "scripts")


def bundle_file_names() -> list[str]:
    names = set(CORE_FILES)
    for directory in EVIDENCE_DIRS:
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and not any(
                part.startswith(".") or part == "__pycache__"
                for part in path.relative_to(ROOT).parts
            ):
                names.add(path.relative_to(ROOT).as_posix())
    return sorted(names)


def add_bytes(archive: ZipFile, name: str, content: bytes) -> None:
    info = ZipInfo(name, date_time=(2026, 11, 27, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, content)


def main() -> None:
    payloads = {}
    for name in bundle_file_names():
        path = ROOT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        payloads[name] = path.read_bytes()

    checksums = "".join(
        f"{hashlib.sha256(content).hexdigest()}  {name}\n"
        for name, content in payloads.items()
    ).encode("ascii")
    manifest_name = f"SHA256SUMS-{VERSION}.txt"
    (PAPER / manifest_name).write_bytes(checksums)

    bundle = PAPER / f"zenodo-upload-{VERSION}.zip"
    with ZipFile(bundle, "w") as archive:
        for name, content in payloads.items():
            add_bytes(archive, name, content)
        add_bytes(archive, manifest_name, checksums)
    print(f"Created {bundle} ({len(payloads)} files, {bundle.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
