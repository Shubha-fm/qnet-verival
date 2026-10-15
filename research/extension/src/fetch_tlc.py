"""Acquire the exact official TLC release used by the independent baseline."""
from pathlib import Path
import hashlib,urllib.request
ROOT=Path(__file__).resolve().parents[1]
SHA='936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88'
URL='https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar'
if __name__=='__main__':
    p=ROOT/'tools/tla2tools.jar';p.parent.mkdir(exist_ok=True)
    data=p.read_bytes() if p.exists() else urllib.request.urlopen(URL,timeout=60).read()
    assert hashlib.sha256(data).hexdigest()==SHA,'TLC release checksum mismatch'
    if not p.exists():p.write_bytes(data)
    print(f'Verified TLC release v1.7.4, embedded TLC 2.19: {SHA}')
