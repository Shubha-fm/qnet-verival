"""Transform rates to explicit supply scenarios; verify a bounded symmetric key-pool refinement."""
from pathlib import Path
from collections import Counter,defaultdict
from dataclasses import asdict
from decimal import Decimal,ROUND_FLOOR
import csv,gzip,hashlib,itertools,json,os,subprocess,tempfile,time
from measurement_pool import *
root=Path(__file__).resolve().parents[1];base=root/'measurement';out=base/'results';out.mkdir(exist_ok=True);(base/'graphs').mkdir(exist_ok=True)
rows=[r for r in csv.DictReader((base/'normalized/observations.csv').open()) if r['primary']=='True']
windows=('0.001','0.01','0.1','1');workloads=(2,4,8);bits=(128,256,512)
counts=Counter();observed=set();crosswalk=base/'normalized/capacity_crosswalk.csv.gz';tmp=crosswalk.with_suffix('.writing')
with gzip.open(tmp,'wt',newline='') as f:
 w=csv.writer(f);w.writerow(['observation_id','window_s','request_count','key_unit_bits','initial_tokens','capacity_class'])
 for r in rows:
  rate=Decimal(r['secure_key_rate_bps'])
  for window,keybits in itertools.product(windows,bits):
   capacity=int((rate*Decimal(window)/keybits).to_integral_value(rounding=ROUND_FLOOR))
   for n in workloads:
    cap=min(capacity,n);counts[(r['system'],r['campaign'],r['condition'],window,keybits,n,cap)]+=1
    if keybits==256:
     w.writerow([r['observation_id'],window,n,keybits,capacity,cap]);observed.add((n,cap))
tmp.replace(crosswalk)
fields=['system','campaign','condition','window_s','key_unit_bits','request_count','capacity_class','observation_count']
with (out/'capacity_counts.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(fields)
 for key,value in sorted(counts.items()):w.writerow([*key,value])
# Independent graph-level checker: same program with progress bit changed from P8 to I4.
cpp=(root/'src/checker.cpp').read_text().replace('1<<7','1<<3')
(root/'src/pool_checker.cpp').write_text(cpp)
subprocess.run(['g++','-O2','-std=c++17',str(root/'src/pool_checker.cpp'),'-o',str(root/'src/pool_graph_checker')],check=True)
results=[]
with tempfile.TemporaryDirectory(prefix='veriqkd_pool_') as td:
 for n,cap in sorted(observed):
  for mode,L,D in itertools.product(('atomic','split','reserved'),(3,6,12),(6,12)):
   c=PoolConfig(n,cap,mode,L,D);cid=hashlib.sha256(json.dumps(asdict(c),sort_keys=True).encode()).hexdigest()[:16]
   path=Path(td)/'graph.txt';r=check(c,path);cpp_result=json.loads(subprocess.check_output([str(root/'src/pool_graph_checker'),str(path)],text=True))
   expected=sum(1<<j for j,p in enumerate(NAMES) if not r['properties'][p]);assert expected==cpp_result['violation_mask'] and r['states']==cpp_result['reachable'] and r['edges']==cpp_result['edges']
   r.update(case_id=cid,crosscheck_agrees=True,crosscheck=cpp_result)
   target=base/'graphs'/f'{cid}.graph.gz'
   data=gzip.compress(path.read_bytes(),mtime=0);temp=target.with_suffix('.writing')
   with temp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
   temp.replace(target);r['graph_sha256']=hashlib.sha256(data).hexdigest();results.append(r)
(out/'pool_verification.json').write_text(json.dumps(results,indent=2))
# Attach static profile verdicts to measured operating-condition counts. These are associations, not probabilities of field faults.
lookup=defaultdict(list)
for r in results:lookup[(r['config']['requests'],r['config']['capacity'])].append(r)
weighted=[]
for system in sorted({r['system'] for r in rows}):
 for window,mode,L,D in itertools.product(windows,('atomic','split','reserved'),(3,6,12),(6,12)):
  for n in workloads:
   total=unsafe=capacity_bad=stale_bad=0
   for key,value in counts.items():
    sy,campaign,condition,win,b,n0,cap=key
    if (sy,win,b,n0)!=(system,window,256,n):continue
    rec=next(r for r in lookup[(n,cap)] if (r['config']['mode'],r['config']['expiry_steps'],r['config']['deadline_steps'])==(mode,L,D))
    total+=value;unsafe+=value*any(not v for v in rec['properties'].values());capacity_bad+=value*(not rec['properties']['I1_capacity']);stale_bad+=value*(not rec['properties']['I2_fresh_commit'])
   weighted.append({'system':system,'window_s':window,'key_unit_bits':256,'requests':n,'mode':mode,'expiry_steps':L,'deadline_steps':D,'measurement_rows':total,'rows_associated_with_unsafe_profile':unsafe,'rows_associated_with_capacity_violation':capacity_bad,'rows_associated_with_stale_commit':stale_bad})
with (out/'measurement_profile_associations.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(weighted[0]));w.writeheader();w.writerows(weighted)
summary={'primary_measurements':len(rows),'primary_crosswalk_rows':len(rows)*len(windows)*len(workloads),'sensitivity_transformations':len(rows)*len(windows)*len(workloads)*len(bits),'key_unit_bits_primary':256,'key_unit_bits_sensitivity':list(bits),'windows_s':list(windows),'request_counts':list(workloads),'observed_capacity_profiles':len(observed),'verified_cases':len(results),'sum_states':sum(r['states'] for r in results),'sum_edges':sum(r['edges'] for r in results),'crosschecks_agree':sum(r['crosscheck_agrees'] for r in results),'modes':{m:{'cases':sum(r['config']['mode']==m for r in results),'failing':sum(r['config']['mode']==m and any(not x for x in r['properties'].values()) for r in results)} for m in ('atomic','split','reserved')}}
(out/'experiment_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
