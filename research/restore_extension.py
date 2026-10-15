"""Restore the pinned base archive, then merge the verified research extension."""
from pathlib import Path
import hashlib,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parent
EXPECTED='cd87532e4e5408a08033c2de0c33f1b0c886b988fc1df1fb599de7998d02044d'
def main():
    target=ROOT/'replication/VeriQKD_Net_Measurement_Driven'
    if not target.exists():subprocess.run([sys.executable,str(ROOT/'restore_package.py')],check=True)
    source=ROOT/'extension/VeriQKD_Net_Implementation_Baseline_Extension.zip'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==EXPECTED,'Extension SHA-256 mismatch'
    with zipfile.ZipFile(source) as archive:
        assert archive.testzip() is None,'Extension ZIP integrity failure'
        for member in archive.infolist():
            name={'README.md':'EXTENSION_README.md','MANIFEST.sha256':'EXTENSION_MANIFEST.sha256'}.get(member.filename,member.filename)
            out=(target/name).resolve()
            assert out.is_relative_to(target.resolve()),'Unsafe archive path'
            if member.is_dir():out.mkdir(parents=True,exist_ok=True)
            else:out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(archive.read(member))
    print(f'Extension verified and restored into {target}')
    print('Read EXTENSION_README.md; expected unit-test count is 28.')
if __name__=='__main__':main()
