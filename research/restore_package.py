"""Verify and restore the code-and-data experimental ZIP (manuscript excluded)."""
from pathlib import Path
import hashlib
import io
import zipfile

ROOT = Path(__file__).resolve().parent
EXPECTED = "655c7dc71b59410acff273e093ad39175062c4384c5990068c93f3d89cb015d0"

def main():
    parts = [ROOT / "package" / f"replication.zip.part{i:02d}" for i in range(1, 4)]
    data = b"".join(p.read_bytes() for p in parts)
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise SystemExit("Package SHA-256 mismatch; download all three parts again.")
    target = ROOT / "replication"
    if target.exists():
        raise SystemExit(f"Refusing to overwrite {target}; choose a fresh checkout.")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.testzip() is not None:
            raise SystemExit("ZIP integrity check failed.")
        for member in archive.infolist():
            resolved = (target / member.filename).resolve()
            if not resolved.is_relative_to(target.resolve()):
                raise SystemExit("Unsafe archive path.")
        target.mkdir()
        archive.extractall(target)
    print(f"Verified SHA-256 and extracted complete package to {target}")

if __name__ == "__main__":
    main()

