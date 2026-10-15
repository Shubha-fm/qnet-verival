"""Normalize public observations without inventing timestamps or correcting values."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import csv,hashlib,json,math,statistics
root=Path(__file__).resolve().parents[1];src=root/'measurement/source';out=root/'measurement/normalized';out.mkdir(exist_ok=True)
rows=[];file_summary=[];reject=[]
for p in sorted(src.glob('*.csv')):
 data=list(csv.DictReader(p.open(newline='')));file_hash=hashlib.sha256(p.read_bytes()).hexdigest()
 auxiliary=p.name=='characterisation_toshiba_production_25samples.csv'
 for number,r in enumerate(data,2):
  try:
   rate=Decimal(r['SecureKeyRate_bps']);q=Decimal(r['QBER']);voa=Decimal(r['VOA_dB'])
   assert rate.is_finite() and q.is_finite() and voa.is_finite() and rate>=0 and 0<=q<=1
  except Exception as e:
   reject.append({'file':p.name,'source_line':number,'raw':r,'reason':'invalid or out-of-domain numeric field'});continue
  campaign='characterisation' if p.name.startswith('characterisation_') else 'coexistence'
  rec={'observation_id':hashlib.sha256((file_hash+':'+str(number)).encode()).hexdigest()[:16],
       'source_file':p.name,'source_line':number,'primary':not auxiliary,'campaign':campaign,
       'system':r.get('System','Toshiba_MU'),'condition':r.get('Condition','sweep'),
       'run':r.get('Run',''),'fibre_km':r.get('Fibre_km',r.get('Sweep_km','')),
       'noise_dbm':r.get('Noise_dBm','none'),'voa_db':str(voa),'qber_fraction':str(q),'secure_key_rate_bps':str(rate)}
  rows.append(rec)
 file_summary.append({'file':p.name,'rows':len(data),'primary':not auxiliary,'sha256':file_hash,'columns':list(data[0])})
# Published 25-sample file is a multiset subset, not independent added observations.
key=lambda r:tuple(sorted(r.items()))
a=Counter(map(key,csv.DictReader((src/'characterisation_toshiba_production_25samples.csv').open())))
b=Counter(map(key,csv.DictReader((src/'characterisation_toshiba_production_full_sweep.csv').open())))
overlap=sum((a&b).values());assert overlap==sum(a.values())==6024
fields=list(rows[0])
with (out/'observations.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
primary=[r for r in rows if r['primary']]
by_system=[]
for system in sorted({r['system'] for r in primary}):
 xs=[r for r in primary if r['system']==system];rates=[float(r['secure_key_rate_bps']) for r in xs];qs=[float(r['qber_fraction']) for r in xs]
 by_system.append({'system':system,'rows':len(xs),'zero_skr':sum(x==0 for x in rates),'rate_min':min(rates),'rate_median':statistics.median(rates),'rate_max':max(rates),'qber_min':min(qs),'qber_max':max(qs)})
# Group by source file and operating condition to avoid pretending pooled platform medians are fair rankings.
groups=defaultdict(list)
for r in primary:
 groups[(r['source_file'],r['system'],r['condition'],r['run'],r['fibre_km'],r['noise_dbm'],r['voa_db'])].append(r)
operating=[]
for k,xs in sorted(groups.items()):
 rates=sorted(float(r['secure_key_rate_bps']) for r in xs);qs=sorted(float(r['qber_fraction']) for r in xs)
 operating.append(dict(zip(('source_file','system','condition','run','fibre_km','noise_dbm','voa_db'),k))|{'rows':len(xs),'rate_median':statistics.median(rates),'rate_q25':rates[(len(rates)-1)//4],'rate_q75':rates[3*(len(rates)-1)//4],'qber_median':statistics.median(qs),'qber_max':max(qs),'zero_skr':sum(v==0 for v in rates)})
with (out/'operating_points.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(operating[0]));w.writeheader();w.writerows(operating)
report={'source_csv_files':len(file_summary),'source_rows':sum(f['rows'] for f in file_summary),'normalized_rows':len(rows),'primary_csv_files':sum(f['primary'] for f in file_summary),'primary_rows':len(primary),'excluded_auxiliary_rows':6024,'auxiliary_multiset_overlap':overlap,'rejected_rows':len(reject),'primary_zero_skr':sum(Decimal(r['secure_key_rate_bps'])==0 for r in primary),'primary_operating_points':len(operating),'primary_qber_over_0_1':sum(Decimal(r['qber_fraction'])>Decimal('.1') for r in primary),'timestamp_columns_present':False,'file_summary':file_summary,'systems':by_system,'rejected':reject,'high_qber_records':[r for r in primary if Decimal(r['qber_fraction'])>Decimal('.1')]}
(root/'measurement/results/source_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('file_summary','rejected','high_qber_records')},indent=2))
