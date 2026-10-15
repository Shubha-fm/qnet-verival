"""One isolated case; core checking time and process peak RSS are separate measures."""
import argparse,gzip,hashlib,json,resource,subprocess,time
from dataclasses import asdict
from pathlib import Path
from model import Config,PROPERTIES,StateLimit,explore
ap=argparse.ArgumentParser();ap.add_argument('spec');ap.add_argument('out');ap.add_argument('--graph-dir');ap.add_argument('--checker');a=ap.parse_args()
case=json.loads(Path(a.spec).read_text());out=Path(a.out)
cfg=case['config'];cfg['route_lengths']=tuple(cfg['route_lengths']);cfg['mutations']=tuple(cfg.get('mutations',()))
c=Config(**cfg);start=time.perf_counter();tmp=out.with_suffix('.graph.tmp')
try:
 result=explore(c,str(tmp) if a.graph_dir else None);result['status']='complete'
 # Core peak includes Python graph export and labels; graph export runs before explore returns.
 result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 if a.graph_dir:
  cpp=json.loads(subprocess.check_output([a.checker,str(tmp)],text=True))
  mask=sum(1<<j for j,p in enumerate(PROPERTIES) if not result['properties'][p])
  result['crosscheck']=cpp;result['crosscheck_agrees']=(mask==cpp['violation_mask'] and result['states']==cpp['reachable'] and result['transitions']==cpp['edges'])
  if not result['crosscheck_agrees']:raise RuntimeError('independent graph checker disagreement')
  target=Path(a.graph_dir)/(case['case_id']+'.graph.gz')
  compressed_tmp=target.with_suffix('.writing')
  with tmp.open('rb') as src, compressed_tmp.open('wb') as raw:
   with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as dst:
    while chunk:=src.read(1024*1024):dst.write(chunk)
   raw.flush()
   import os
   os.fsync(raw.fileno())
  compressed_tmp.replace(target)
  with gzip.open(target,'rt') as verified:
   header=verified.readline().split()
   assert tuple(map(int,header))==(result['states'],result['transitions'])
   for line in verified: pass
  result['graph_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
except StateLimit as e:
 result={'config':asdict(c),'status':'capped','discovered_states':e.states,'expanded_states':e.expanded,'seconds':round(e.seconds,6),'properties':{p:None for p in PROPERTIES},'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
finally:
 tmp.unlink(missing_ok=True)
result.update({k:case[k] for k in ('case_id','suite','tag','memberships')});result['worker_wall_seconds']=round(time.perf_counter()-start,6)
out.write_text(json.dumps(result,indent=2))
