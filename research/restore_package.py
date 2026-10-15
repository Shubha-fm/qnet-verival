"""Verify and restore the complete, unchanged experimental ZIP."""
from pathlib import Path
import hashlib
import io
import zipfile

ROOT = Path(__file__).resolve().parent
EXPECTED = "cc5e477a5b8a9c2a6b19f45860398fa45a4848c0d4530baa5b247f11591a2df8"

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
