"""Generate every manuscript number, table, and evidence plot from recorded files."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,gzip,hashlib,json,math,statistics
root=Path(__file__).resolve().parents[1]
rs=[json.loads(p.read_text()) for p in sorted((root/'dataset/outcomes').glob('*.json'))]
complete=[r for r in rs if r['status']=='complete']; capped=[r for r in rs if r['status']=='capped']
props=list(complete[0]['properties']);bad=lambda r:any(v is False for v in r['properties'].values())
summary={'cases':len(rs),'complete':len(complete),'capped':len(capped),'violating':sum(map(bad,complete)),'passing':sum(not bad(r) for r in complete),'crosschecked':sum(r['crosscheck_agrees'] for r in complete),'sum_states':sum(r['states'] for r in complete),'sum_edges':sum(r['transitions'] for r in complete),'max_states':max(r['states'] for r in complete),'unique_graph_serializations':len({r['graph_sha256'] for r in complete})}
# Outcome table explicitly separates unknown from pass/fail.
with (root/'dataset/case_summary.csv').open('w') as f:
 fields=['case_id','suite','tag','status','states','discovered_states','transitions','seconds','peak_rss_kib','states_with_delivery','states_all_delivered','crosscheck_agrees']+props
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for r in rs:
  row={k:r.get(k,'') for k in fields if k not in props};row.update({p:('unknown' if r['properties'][p] is None else 'pass' if r['properties'][p] else 'fail') for p in props});w.writerow(row)
esc=lambda s:str(s).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def table(name,caption,headers,rows,widths=None):
 spec=''.join('l' if i==0 else 'r' for i in range(len(headers))) if widths is None else widths
 text=r'\begin{table}[htbp]\centering\small\caption{'+caption+r'}\label{tab:'+name+r'}\begin{tabular}{'+spec+r'}\toprule '+' & '.join(headers)+r' \\\midrule'+'\n'
 for row in rows:text+=' & '.join(esc(x) for x in row)+r' \\'+'\n'
 text+=r'\bottomrule\end{tabular}\end{table}'+'\n'
 (root/f'manuscript/{name}.tex').write_text(text)
suites=[]
for suite in ('structural','concurrency','faults','localized','combined','routes'):
 xs=[r for r in rs if r['suite']==suite];ys=[r for r in xs if r['status']=='complete']
 suites.append([suite,len(xs),len(ys),len(xs)-len(ys),sum(bad(r) for r in ys),f"{sum(r['states'] for r in ys):,}"])
table('dataset_summary','Synthetic benchmark coverage. A capped case has no verification verdict. State totals count each complete configuration separately, including repeated graph structures.',['Family','Cases','Complete','Capped','Fail','State total'],suites)
# Context masking and ablation.
faults=[r for r in complete if r['suite']=='faults' and r['config']['mutant']!='abort_label']
controls=[r for r in complete if r['suite']=='faults' and r['config']['mutant']=='abort_label']
sets=[('P6 only',['P6_delivery_contract']),('P1--P7',[p for p in props if p.split('_')[0] in ['P'+str(i) for i in range(1,8)]]),('P1--P7 + P9',[p for p in props if not p.startswith('P8')]),('Full suite',props)]
ablation=[(name,sum(any(r['properties'][p] is False for p in subset) for r in faults)) for name,subset in sets]
summary.update(fault_contexts=len(faults),fault_contexts_detected=sum(bad(r) for r in faults),label_controls=len(controls),label_control_failures=sum(bad(r) for r in controls))
table('ablation','Detection over complete first-order fault contexts, excluding the diagnostic-label control. Contexts with no observed violation remain in the denominator.',['Property subset','Detected','Evaluated'],[(n,k,len(faults)) for n,k in ablation])
mutrows=[]
for m in sorted({r['config']['mutant'] for r in faults}):
 xs=[r for r in faults if r['config']['mutant']==m]
 mutrows.append((m,len(xs),sum(bad(r) for r in xs),sum(not bad(r) for r in xs)))
table('faults_summary','Context-dependent first-order results. A surviving context is not automatically an equivalent mutant.',['Operator','Contexts','Detected','No violation'],mutrows)
# Confirm label controls match baseline graph serialization.
def normalized(c):
 c=dict(c);c['mutant']='none';c.pop('max_states');return json.dumps(c,sort_keys=True)
lookup={normalized(r['config']):r for r in complete if r['suite']=='structural'}
label_matches=sum(normalized(r['config']) in lookup and lookup[normalized(r['config'])]['graph_sha256']==r['graph_sha256'] for r in controls)
summary['label_control_graph_matches']=label_matches
# Concurrency modes, excluding deliberately short budgets in primary repair comparison.
conrows=[]
for mode in ('atomic','split','reserved'):
 xs=[r for r in rs if r['suite']=='concurrency' and r['config']['delivery_mode']==mode];ys=[r for r in xs if r['status']=='complete']
 conrows.append((mode,len(xs),len(ys),len(xs)-len(ys),sum(bad(r) for r in ys),sum(r['properties']['P9_single_use'] is False for r in ys),sum(r['properties']['P5_fresh_at_delivery'] is False for r in ys)))
table('concurrency_summary','All concurrency contexts, including short budgets. Failures in split mode are intended negative controls.',['Mode','Cases','Complete','Capped','Any fail','P9 fail','P5 fail'],conrows)
# Preserve one shortest actual race witness from two-session shared split mode.
race=next(r for r in complete if r['suite']=='concurrency' and r['config']['sessions']==2 and r['config']['relays']==0 and r['config']['shared_key'] and r['config']['delivery_mode']=='split' and r['properties']['P9_single_use'] is False)
(root/'results/race_example.json').write_text(json.dumps(race,indent=2));summary['race_case_id']=race['case_id']
w=race['witnesses']['P9_single_use'];table('race_trace','Actual shortest BFS counterexample prefix for shared-key duplicate delivery. Prefix events are retained in the JSON witness.',['Step','Action'],[(i+1,e['action']) for i,e in enumerate(w['steps'])],widths='rl')
summary['race_witness_steps']=len(w['steps'])
# Repeated timing results, discard replication 0.
perf=[]
for p in sorted((root/'results/performance_raw').glob('*.json')):
 if p.name.endswith('.spec.json'):continue
 r=json.loads(p.read_text());rep=int(r['case_id'].rsplit('rep',1)[1]);
 if rep>0:perf.append(r)
perfrows=[]
for tag in sorted({r['tag'] for r in perf}):
 xs=[r for r in perf if r['tag']==tag and r['status']=='complete'];
 if xs:
  ts=sorted(r['seconds'] for r in xs);mem=[r['peak_rss_kib']/1024 for r in xs]
  perfrows.append((tag,len(xs),xs[0]['states'],statistics.median(ts),min(ts),max(ts),statistics.median(mem)))
table('performance_summary','Fresh-process measurements: seven measured replicates after one discarded run per setting. Time excludes graph export and C++ checking. RSS is the peak of the Python worker process.',['Setting','Runs','States','Median s','Min s','Max s','RSS MiB'],[(n,k,f'{st:,}',f'{med:.3f}',f'{lo:.3f}',f'{hi:.3f}',f'{mm:.1f}') for n,k,st,med,lo,hi,mm in perfrows])
summary['performance_measured_runs']=len(perf)
# Random-testing results with per-scenario Wilson intervals over seed trials.
trials=json.loads((root/'results/testing_trials.json').read_text());truth=json.loads((root/'results/testing_truth.json').read_text());meta=json.loads((root/'results/testing_metadata.json').read_text());truthmap={r['scenario_id']:bad(r) for r in truth}
summary.update(random_traces=meta['traces'],random_scenarios=meta['scenarios'],random_failing_scenarios=sum(truthmap.values()))
def wilson(k,n):
 z=1.95996398454;den=1+z*z/n;center=(k/n+z*z/(2*n))/den;half=z*math.sqrt((k/n*(1-k/n)+z*z/(4*n))/n)/den;return max(0,center-half),min(1,center+half)
randrows=[]
for scheduler in ('uniform','progress_biased'):
 for budget in (10,50,100):
  xs=[r for r in trials if r['scheduler']==scheduler and r['budget_traces']==budget and truthmap[r['scenario_id']]]
  hits=sum(r['any_failure'] for r in xs)
  scenario_hits=sum(any(r['any_failure'] for r in xs if r['scenario_id']==sid) for sid,ok in truthmap.items() if ok)
  randrows.append((scheduler,budget,hits,len(xs),scenario_hits))
table('testing_summary','Enabled-action testing on exhaustively failing scenarios. A hit is at least one valid witness in a seed trial. Scenario coverage pools the twenty seeds.',['Scheduler','Trace budget','Seed hits','Seed trials','Scenarios hit'],randrows)
cirows=[]
for sid in ('skip_auth_r2','skip_ec_r2','wrong_session_ack_r2','expired_delivery_r2','missing_timeout_r2','retry_loop_r2','split_shared1'):
 for scheduler in ('uniform','progress_biased'):
  xs=[r for r in trials if r['scenario_id']==sid and r['scheduler']==scheduler and r['budget_traces']==100]
  k=sum(r['any_failure'] for r in xs);lo,hi=wilson(k,len(xs))
  cirows.append((sid,scheduler,f'{k}/{len(xs)}',f'[{lo:.3f}, {hi:.3f}]'))
table('testing_intervals','Selected seed-trial hit rates at 100 traces, with descriptive 95 percent Wilson intervals. Intervals concern the configured synthetic scheduler, not deployed QKD reliability.',['Scenario','Scheduler','Hits','Wilson interval'],cirows,widths='llrl')
# Trace record validation counts are added by audit.py later.
(root/'results/analysis.json').write_text(json.dumps(summary,indent=2))
(root/'results/derived.json').write_text(json.dumps({'suites':suites,'ablation':ablation,'mutants':mutrows,'concurrency':conrows,'performance':perfrows,'random':randrows},indent=2))
macros={'Cases':summary['cases'],'Complete':summary['complete'],'Capped':summary['capped'],'Failing':summary['violating'],'Passing':summary['passing'],'Crosschecked':summary['crosschecked'],'TotalStates':f"{summary['sum_states']:,}",'TotalEdges':f"{summary['sum_edges']:,}",'MaxStates':f"{summary['max_states']:,}",'UniqueGraphs':summary['unique_graph_serializations'],'RandomTraces':f"{meta['traces']:,}",'RandomFailing':summary['random_failing_scenarios'],'PerfRuns':len(perf),'FaultContexts':len(faults),'FaultDetected':summary['fault_contexts_detected'],'LabelControls':len(controls),'LabelMatches':label_matches}
(root/'manuscript/numbers.tex').write_text('\n'.join('\\newcommand{\\N'+k+'}{'+str(v)+'}' for k,v in macros.items())+'\n')
# Static publication figures; all are derived from dataset records.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
 import io,os
 from PIL import Image
 fig.tight_layout();buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=220);plt.close(fig)
 data=buffer.getvalue();Image.open(io.BytesIO(data)).verify()
 target=root/f'figures/{name}.png';tmp=target.with_suffix('.writing')
 with tmp.open('wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
 tmp.replace(target)
 Image.open(target).verify()
fig,axs=plt.subplots(1,2,figsize=(10,3.5))
for j,label in enumerate(('Complete pass','Complete fail','Capped')):
 vals=[row[2]-row[4] if j==0 else row[4] if j==1 else row[3] for row in suites]
 bottom=[0]*len(suites) if j==0 else [row[2]-row[4] for row in suites] if j==1 else [row[2] for row in suites]
 axs[0].bar([r[0] for r in suites],vals,bottom=bottom,label=label)
axs[0].tick_params(axis='x',rotation=35);axs[0].set_ylabel('Configurations');axs[0].legend(fontsize=10)
axs[1].barh([n for n,k in ablation],[k for n,k in ablation],color='#247b6c');axs[1].invert_yaxis();axs[1].set_xlabel(f'Detected contexts (of {len(faults)})')
save(fig,'coverage_ablation')
# Detection matrix fractions by operator/property, retaining context masking.
ms=[r[0] for r in mutrows];matrix=np.array([[sum(r['properties'][p] is False for r in faults if r['config']['mutant']==m)/sum(r['config']['mutant']==m for r in faults) for p in props] for m in ms])
fig,ax=plt.subplots(figsize=(9,5));im=ax.imshow(matrix,aspect='auto',cmap='Blues',vmin=0,vmax=1);ax.set_xticks(range(9),[p.split('_')[0] for p in props]);ax.set_yticks(range(len(ms)),ms)
for i in range(len(ms)):
 for j in range(9):
  if matrix[i,j]:ax.text(j,i,f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=10,color='white' if matrix[i,j]>.6 else 'black')
fig.colorbar(im,ax=ax,label='Fraction of contexts violating property');save(fig,'mutation_matrix')
fig,axs=plt.subplots(1,2,figsize=(9.5,3.5))
pr=[r for r in perfrows if r[0].startswith('chain_r')];pr.sort(key=lambda r:int(r[0].split('r')[-1]));x=[int(r[0].split('r')[-1]) for r in pr]
axs[0].errorbar(x,[r[3] for r in pr],yerr=[[r[3]-r[4] for r in pr],[r[5]-r[3] for r in pr]],fmt='o-',capsize=3);axs[0].set_yscale('log');axs[0].set(xlabel='Relays',ylabel='Core verification seconds (log)',xticks=x)
axs[1].plot(x,[r[6] for r in pr],'s-',color='#b36335');axs[1].set(xlabel='Relays',ylabel='Median peak worker RSS (MiB)',xticks=x);save(fig,'performance')
fig,axs=plt.subplots(1,2,figsize=(10,3.5))
for scheduler,color in [('uniform','#196185'),('progress_biased','#b5652c')]:
 ys=[]
 for b in (10,50,100):
  row=next(r for r in randrows if r[0]==scheduler and r[1]==b);ys.append(row[2]/row[3])
 axs[0].plot((10,50,100),ys,'o-',label=scheduler,color=color)
 axs[0].set(xlabel='Trace budget per seed trial',ylabel='Fraction of failing seed trials detected',ylim=(0,1.03));axs[0].legend(fontsize=10)
# CDF of first witness over all failing seed trials, nondetections remain in denominator.
 xs=[r for r in trials if r['scheduler']==scheduler and r['budget_traces']==100 and truthmap[r['scenario_id']]]
 curve=[sum(r['first_failure_episode'] is not None and r['first_failure_episode']<=b for r in xs)/len(xs) for b in range(1,101)]
 axs[1].plot(range(1,101),curve,label=scheduler,color=color)
axs[1].set(xlabel='Episode of first witness',ylabel='Cumulative detected trial fraction',ylim=(0,1.03));axs[1].legend(fontsize=10);save(fig,'random_testing')
fig,axs=plt.subplots(1,2,figsize=(10,3.5))
for d in (False,True):
 xs=[r for r in complete if r['suite']=='structural' and r['config']['failures'] and r['config']['delay']==d and '_slack_' in r['tag']]
 xs.sort(key=lambda r:r['config']['relays']);axs[0].plot([r['config']['relays'] for r in xs],[r['states'] for r in xs],'o-',label='Delay enabled' if d else 'No delay')
axs[0].set_yscale('log');axs[0].set(xlabel='Relays',ylabel='Complete-instance states (log)');axs[0].legend(fontsize=10)
for j,mode in enumerate(('atomic','split','reserved')):
 xs=[r for r in complete if r['suite']=='concurrency' and r['config']['delivery_mode']==mode]
 axs[1].bar(j,sum(bad(r) for r in xs),label=mode)
axs[1].set_xticks(range(3),('atomic','split','reserved'));axs[1].set_ylabel('Failing complete concurrency contexts');save(fig,'sensitivity_repair')
print(json.dumps(summary,indent=2))
