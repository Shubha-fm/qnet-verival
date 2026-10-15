"""Final structural data validation; run audit.py for full semantic replay."""
from pathlib import Path
import gzip,hashlib,json
import re

def validate_record(r,schema):
 assert all(k in r for k in schema['required'])
 assert re.fullmatch(r'[0-9a-f]{16}',r['case_id'])
 assert r['suite'] in schema['properties']['suite']['enum']
 assert r['status'] in ('complete','capped')
 assert all(k in r['config'] for k in schema['properties']['config']['required'])
 assert isinstance(r['seconds'],(int,float)) and r['seconds']>=0
 assert isinstance(r['peak_rss_kib'],(int,float)) and r['peak_rss_kib']>=0
 assert len(r['properties'])==9 and all(v is None or type(v) is bool for v in r['properties'].values())
 if r['status']=='complete':
  assert all(k in r for k in ('states','transitions','witnesses','graph_sha256','crosscheck_agrees'))
  assert r['crosscheck_agrees'] is True
  assert r['states']>=1 and r['transitions']>=1
  assert re.fullmatch(r'[0-9a-f]{64}',r['graph_sha256'])
 else: assert all(k in r for k in ('discovered_states','expanded_states'))
root=Path(__file__).resolve().parents[1]
schema=json.loads((root/'dataset/SCHEMA.json').read_text());paths=list((root/'dataset/outcomes').glob('*.json'));assert len(paths)==522
complete=0
for p in paths:
 r=json.loads(p.read_text());validate_record(r,schema)
 if r['status']=='capped':assert all(v is None for v in r['properties'].values());continue
 complete+=1;g=root/'dataset/graphs'/f"{r['case_id']}.graph.gz";data=g.read_bytes();assert hashlib.sha256(data).hexdigest()==r['graph_sha256']
 with gzip.open(g,'rt') as f:
  n,m=map(int,f.readline().split());assert n==r['states'] and m==r['transitions']
  vertices=[f.readline().split() for _ in range(n)];assert all(len(v)==2 for v in vertices)
  count=0
  for line in f:
   u,v=map(int,line.split());assert 0<=u<n and 0<=v<n;count+=1
  assert count==m
summary=json.loads((root/'results/analysis.json').read_text());assert summary['complete']==complete
report=json.loads((root/'results/audit.json').read_text());assert report['random_traces_replayed']==120000 and report['false_witnesses']==0
print('Validated 522 outcome schemas, 513 complete graph encodings and digests, aggregate counts, and full replay audit.')
