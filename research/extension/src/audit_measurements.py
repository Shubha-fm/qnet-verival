"""Audit raw checksums, published counts, every capacity mapping, and every pool witness."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import csv,gzip,hashlib,json
from measurement_pool import *
root=Path(__file__).resolve().parents[1];base=root/'measurement';src=base/'source'
meta=json.loads((src/'zenodo_record.json').read_text())
for f in meta['files']:assert hashlib.md5((src/f['key']).read_bytes()).hexdigest()==f['checksum'].removeprefix('md5:')
# Recompute and compare exact row counts and ranges supplied in source summary records.
char=json.loads((src/'characterisation_summary_stats.json').read_text());co=json.loads((src/'csv_summary_stats.json').read_text());summary_checks=0;summary_minimum_conventions=[]
fixed={'characterisation_toshiba_production_full_sweep.csv':'production','characterisation_toshiba_production_25samples.csv':'production_25','characterisation_toshiba_research_3runs.csv':'research','characterisation_clavis3_full_sweep.csv':'clavis3','characterisation_clavisxgr_full_sweep.csv':'clavisxgr'}
for p in src.glob('*.csv'):
 data=list(csv.DictReader(p.open()));rates=[float(r['SecureKeyRate_bps']) for r in data]
 if p.name.startswith('characterisation_'):
  key=fixed.get(p.name,'perturb_'+p.stem.removeprefix('characterisation_perturbation_'))
  ss=char[key];assert len(data)==ss['total_records'];assert max(rates)==ss['max_SKR_bps']
  if min(rates)!=ss['min_SKR_bps']:
   assert min(x for x in rates if x>0)==ss['min_SKR_bps']
   summary_minimum_conventions.append({'file':p.name,'csv_minimum_including_zeros':min(rates),'published_summary_minimum':ss['min_SKR_bps'],'published_minimum_matches_positive_rows_only':True})
 else:assert len(data)==co[p.name]['row_count']
 summary_checks+=1
rows={r['observation_id']:r for r in csv.DictReader((base/'normalized/observations.csv').open()) if r['primary']=='True'}
assert len(rows)==48507
count=0;profiles=Counter()
with gzip.open(base/'normalized/capacity_crosswalk.csv.gz','rt') as f:
 for r in csv.DictReader(f):
  srcrow=rows[r['observation_id']];rate=Decimal(srcrow['secure_key_rate_bps']);window=Decimal(r['window_s']);bits=int(r['key_unit_bits']);n=int(r['request_count'])
  expected=int(rate*window/bits);assert expected==int(r['initial_tokens']);assert min(expected,n)==int(r['capacity_class'])
  profiles[(n,min(expected,n))]+=1;count+=1
assert count==582084 and len(profiles)==17
rs=json.loads((base/'results/pool_verification.json').read_text());assert len(rs)==306;witness_count=0;states=edges=0
for r in rs:
 c=PoolConfig(**r['config']);p=base/'graphs'/f"{r['case_id']}.graph.gz";data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==r['graph_sha256']
 with gzip.open(p,'rt') as f:
  n,m=map(int,f.readline().split());assert (n,m)==(r['states'],r['edges'])
  for _ in range(n):assert len(f.readline().split())==2
  assert sum(1 for line in f)==m
 assert r['crosscheck_agrees'];states+=n;edges+=m
 for prop,w in r['witnesses'].items():
  s=initial(c)
  for e in w['steps']:
   ts=[t for a,t in successors(s,c) if a==e['action']];assert len(ts)==1;s=ts[0]
  assert prop in violations(s,c);assert asdict(s)==w['state'];witness_count+=1
report={'raw_files_checksum_verified':len(meta['files']),'csv_summary_records_crosschecked':summary_checks,'primary_observations':len(rows),'capacity_crosswalk_rows_verified':count,'observed_capacity_profiles':len(profiles),'pool_graphs_checked':len(rs),'pool_states':states,'pool_edges':edges,'pool_witnesses_replayed':witness_count,'all_graph_crosschecks_agree':True,'summary_minimum_conventions':summary_minimum_conventions}
(base/'results/measurement_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
