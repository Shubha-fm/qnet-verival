"""Fetch and verify the exact IrelandQCI v2 files. Original bytes are unchanged."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import datetime,hashlib,json,os,time,urllib.request
root=Path(__file__).resolve().parents[1];dest=root/'measurement/source';dest.mkdir(parents=True,exist_ok=True)
record=dest/'zenodo_record.json'
if not record.exists():
 with urllib.request.urlopen('https://zenodo.org/api/records/21792844',timeout=45) as r:record.write_bytes(r.read())
meta=json.loads(record.read_text())
def fetch(f):
 target=dest/f['key'];expected=f['checksum'].removeprefix('md5:')
 if target.exists() and hashlib.md5(target.read_bytes()).hexdigest()==expected:return (f['key'],'cached')
 for attempt in range(3):
  try:
   req=urllib.request.Request(f['links']['self'],headers={'User-Agent':'VeriQKD-measurement-reproducibility/1.0'})
   with urllib.request.urlopen(req,timeout=45) as r:data=r.read()
   if hashlib.md5(data).hexdigest()!=expected:raise ValueError('checksum mismatch '+f['key'])
   tmp=target.with_suffix(target.suffix+'.writing')
   with tmp.open('wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
   tmp.replace(target)
   return (f['key'],'downloaded')
  except Exception:
   if attempt==2:raise
   time.sleep(2*(attempt+1))
with ThreadPoolExecutor(max_workers=4) as pool:
 for future in as_completed([pool.submit(fetch,f) for f in meta['files']]):print(*future.result(),flush=True)
manifest={'record_id':21792844,'doi':meta['doi'],'version':meta['metadata'].get('version'),'acquired_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[]}
for f in meta['files']:
 data=(dest/f['key']).read_bytes();assert hashlib.md5(data).hexdigest()==f['checksum'].removeprefix('md5:')
 manifest['files'].append({'name':f['key'],'bytes':len(data),'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),'source_url':f['links']['self']})
(dest/'acquisition_manifest.json').write_text(json.dumps(manifest,indent=2))
print('Verified all',len(meta['files']),'source files.',flush=True)
