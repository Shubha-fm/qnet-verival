"""Produce measured-data evidence figures/tables from original rows and executed pool checks."""
from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal
import csv,json,statistics,io,os
root=Path(__file__).resolve().parents[1];base=root/'measurement';out=base/'results';tex=root/'manuscript'
rows=[r for r in csv.DictReader((base/'normalized/observations.csv').open()) if r['primary']=='True']
audit=json.loads((out/'source_audit.json').read_text());results=json.loads((out/'pool_verification.json').read_text());summary=json.loads((out/'experiment_summary.json').read_text());op=list(csv.DictReader((base/'normalized/operating_points.csv').open()))
short={'IDQ_Clavis3':'Clavis3','IDQ_ClavisXGR':'ClavisXGR','Toshiba_LE_Production':'Toshiba LE prod.','Toshiba_LE_Research':'Toshiba LE research','Toshiba_MU':'Toshiba MU'}
esc=lambda x:str(x).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def table(name,caption,headers,data,spec):
 text=r'\begin{table}[htbp]\centering\small\caption{'+caption+r'}\label{tab:'+name+r'}\begin{tabular}{'+spec+r'}\toprule '+' & '.join(headers)+r' \\\midrule'+'\n'
 for row in data:text+=' & '.join(esc(x) for x in row)+r' \\'+'\n'
 text+=r'\bottomrule\end{tabular}\end{table}'+'\n';(tex/(name+'.tex')).write_text(text)
table('measured_inventory','Primary published observations after excluding the exact 6,024-row auxiliary subset. Rate ranges are descriptive across different operating conditions, not device rankings.',['Platform','Rows','Zero SKR','SKR range (bit/s)'],[(short[r['system']],f"{r['rows']:,}",r['zero_skr'],f"{r['rate_min']:,.0f}--{r['rate_max']:,.0f}") for r in audit['systems']],'lrrr')
# Median perturbation ratios at matched attenuation, not reconstructed time traces.
perturb=defaultdict(list)
for r in rows:
 if 'perturbation' in r['source_file']:perturb[(r['condition'],float(r['voa_db']))].append(float(r['secure_key_rate_bps']))
conditions=('baseline','1s_settling','2s_settling','5s_settling','20s_settling','continuous','continuous_noisy','random')
ratios={condition:{str(voa):statistics.median(perturb[(condition,voa)])/statistics.median(perturb[('baseline',voa)]) for voa in (9.,12.,15.)} for condition in conditions}
table('measured_perturbation','Median measured SKR divided by the baseline median at the same attenuation. Labels are source experimental settings, not reconstructed event times.',['Condition','9 dB','12 dB','15 dB'],[(c,*[f"{ratios[c][str(v)]:.3f}" for v in (9.,12.,15.)]) for c in conditions],'lrrr')
mode_rows=[]
for mode in ('atomic','split','reserved'):
 xs=[r for r in results if r['config']['mode']==mode]
 mode_rows.append((mode,len(xs),sum(any(not v for v in r['properties'].values()) for r in xs),*[sum(not r['properties'][p] for r in xs) for p in ('I1_capacity','I2_fresh_commit','I3_accounting','I4_termination')]))
table('measured_verification','Resource-model verification across observed capacity classes and assumed event budgets. Every case completes and agrees with the C++ graph checker.',['Mode','Cases','Any fail','I1','I2','I3','I4'],mode_rows,'lrrrrrr')
# Primary example supply-class distribution: N=4, W=0.01 seconds, 256-bit units.
capacity=defaultdict(Counter)
for r in rows:
 c=min(int(Decimal(r['secure_key_rate_bps'])*Decimal('.01')/256),4);capacity[r['system']][c]+=1
table('measured_capacity','Measurement-row associations with capacity classes for a 10 ms assumed accumulation window, 256-bit units, and four requests. Counts describe published sampling, not outage probabilities.',['Platform','C=0','C=1','C=2','C=3','C$\\geq$4'],[(short[sy],*[capacity[sy][c] for c in range(5)]) for sy in short],'lrrrrr')
# Sensitivity to sampling-density weighting: equal operating-point mean of within-group sufficiency shares.
weightrows=[]
for sy in short:
 xs=[r for r in rows if r['system']==sy];groups=defaultdict(list)
 for r in xs:groups[(r['source_file'],r['condition'],r['run'],r['fibre_km'],r['noise_dbm'],r['voa_db'])].append(r)
 for window in (Decimal('.01'),Decimal('1')):
  enough=lambda r:int(Decimal(r['secure_key_rate_bps'])*window/256)>=4
  rw=sum(enough(r) for r in xs)/len(xs);pw=statistics.mean(sum(enough(r) for r in group)/len(group) for group in groups.values())
  weightrows.append((short[sy],str(window),f'{rw:.3f}',f'{pw:.3f}',len(groups)))
table('measured_weighting','Fraction of observations meeting four 256-bit units: row weighting versus equal weighting of operating-point groups. These are descriptive sampling summaries.',['Platform','Window s','Row weight','Point weight','Groups'],weightrows,'lrrrr')
(out/'perturbation_ratios.json').write_text(json.dumps(ratios,indent=2));(out/'weighting_sensitivity.json').write_text(json.dumps(weightrows,indent=2))
nums={'SourceFiles':39,'MeasurementRows':f"{audit['source_rows']:,}",'PrimaryRows':f"{audit['primary_rows']:,}",'OperatingPoints':f"{audit['primary_operating_points']:,}",'CrosswalkRows':f"{summary['primary_crosswalk_rows']:,}",'Transformations':f"{summary['sensitivity_transformations']:,}",'PoolCases':summary['verified_cases'],'PoolStates':f"{summary['sum_states']:,}",'PoolEdges':f"{summary['sum_edges']:,}"}
(tex/'measurement_numbers.tex').write_text('\n'.join('\\newcommand{\\M'+k+'}{'+str(v)+'}' for k,v in nums.items())+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
 fig.tight_layout();b=io.BytesIO();fig.savefig(b,format='png',dpi=230);plt.close(fig);data=b.getvalue();Image.open(io.BytesIO(data)).verify();target=root/'figures'/f'{name}.png';tmp=target.with_suffix('.writing')
 with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 tmp.replace(target)
fig,axs=plt.subplots(2,2,figsize=(10,7))
for sy in ('IDQ_Clavis3','IDQ_ClavisXGR','Toshiba_LE_Production','Toshiba_LE_Research'):
 xs=[r for r in rows if r['system']==sy and 'perturbation' not in r['source_file']];groups=defaultdict(list)
 for r in xs:groups[float(r['voa_db'])].append(r)
 x=sorted(groups);y=[statistics.median(float(r['secure_key_rate_bps']) for r in groups[v]) for v in x];q=[100*statistics.median(float(r['qber_fraction']) for r in groups[v]) for v in x]
 axs[0,0].plot(x,[a if a>0 else np.nan for a in y],label=short[sy]);axs[0,1].plot(x,q,label=short[sy])
axs[0,0].set_yscale('log');axs[0,0].set(xlabel='Added attenuation (dB)',ylabel='Median SKR (bit/s, log)');axs[0,0].legend(fontsize=11)
axs[0,1].set(xlabel='Added attenuation (dB)',ylabel='Median QBER (%)');axs[0,1].legend(fontsize=11)
for ax,fibre in zip(axs[1],('0','50')):
 for noise in ('none','3','7','9','12'):
  xs=[r for r in rows if r['campaign']=='coexistence' and r['fibre_km']==fibre and r['noise_dbm']==noise];g=defaultdict(list)
  for r in xs:g[float(r['voa_db'])].append(float(r['secure_key_rate_bps']))
  x=sorted(g);y=[statistics.median(g[v]) for v in x];ax.plot(x,[a if a>0 else np.nan for a in y],'o-',markersize=3,label='No injection' if noise=='none' else noise+' dBm')
 ax.set_yscale('log');ax.set(xlabel='Added attenuation (dB)',ylabel='Median SKR (bit/s, log)',title=f'Toshiba MU: {fibre} km added fibre');ax.legend(fontsize=11)
save(fig,'measured_envelopes')
fig,axs=plt.subplots(1,2,figsize=(10,3.8))
x=np.arange(len(conditions))
for voa in (9.,12.,15.):axs[0].plot(x,[ratios[c][str(voa)] for c in conditions],'o-',label=f'{voa:g} dB')
axs[0].axhline(1,color='grey',linestyle='--');axs[0].set_xticks(x,conditions,rotation=40,ha='right');axs[0].set_ylabel('Median SKR / matched baseline');axs[0].legend(fontsize=11)
for sy in short:
 ys=[]
 for window in (Decimal('.001'),Decimal('.01'),Decimal('.1'),Decimal('1')):
  xs=[r for r in rows if r['system']==sy];ys.append(sum(int(Decimal(r['secure_key_rate_bps'])*window/256)>=4 for r in xs)/len(xs))
 axs[1].plot((.001,.01,.1,1),ys,'o-',label=short[sy])
axs[1].set_xscale('log');axs[1].set(xlabel='Assumed accumulation window (s)',ylabel='Published rows with capacity >= 4',ylim=(0,1.05));axs[1].legend(fontsize=11)
save(fig,'measured_perturbation_supply')
fig,axs=plt.subplots(1,2,figsize=(10,3.5))
for j,mode in enumerate(('atomic','split','reserved')):
 xs=[r for r in results if r['config']['mode']==mode];fails=sum(any(not v for v in r['properties'].values()) for r in xs);axs[0].bar(j,len(xs)-fails,color='#237e69',label='Pass' if j==0 else None);axs[0].bar(j,fails,bottom=len(xs)-fails,color='#c76532',label='Fail' if j==0 else None)
axs[0].set_xticks(range(3),('atomic','split','reserved'));axs[0].set_ylabel('Complete resource-model cases');axs[0].legend(fontsize=11)
matrix=[]
for n in (2,4,8):
 matrix.append([sum(any(not v for v in r['properties'].values()) for r in results if r['config']['mode']=='split' and r['config']['requests']==n and r['config']['capacity']==cap) if cap<=n else np.nan for cap in range(9)])
im=axs[1].imshow(matrix,aspect='auto',cmap='Oranges',vmin=0,vmax=6);axs[1].set_xticks(range(9));axs[1].set_yticks(range(3),(2,4,8));axs[1].set(xlabel='Saturated initial capacity',ylabel='Requests')
for i,row in enumerate(matrix):
 for j,v in enumerate(row):
  if not np.isnan(v):axs[1].text(j,i,str(int(v)),ha='center',va='center',fontsize=9)
fig.colorbar(im,ax=axs[1],label='Failing split-mode budget settings / 6');save(fig,'measured_pool_results')
print('Generated measured-data tables and three figures.')
