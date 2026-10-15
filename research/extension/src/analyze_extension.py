from pathlib import Path
import json,statistics,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'manuscript'
if __name__=='__main__':
    impl=json.loads((ROOT/'implementation/summary.json').read_text());tlc=json.loads((ROOT/'baseline/summary.json').read_text());rand=json.loads((ROOT/'baseline/random_summary.json').read_text())
    rows=[]
    for mode in ('atomic','split','reserved'):
        for sched in ('prepare_barrier','expiry_boundary'):
            x=impl['modes'][mode][sched];rows.append((mode,sched.replace('_',' '),x['batches'],x['duplicate_key'],x['over_capacity'],x['expired_delivery']))
    tex='\\begin{table}[htbp]\\centering\\small\n\\caption{SQLite implementation batches. Counts are batches exhibiting each finding; columns overlap. Each cell repeats seventeen profiles twenty times.}\\label{tab:sqlresults}\n\\begin{tabular}{llrrrr}\\toprule\nMode & Schedule & Batches & Duplicate & Excess & Expired \\\\\\midrule\n'
    tex+='\n'.join(f'{a} & {b} & {c} & {d} & {e} & {f} \\\\' for a,b,c,d,e,f in rows)
    tex+='\n\\bottomrule\\end{tabular}\\end{table}\n';(M/'sql_results.tex').write_text(tex)
    tex='\\begin{table}[htbp]\\centering\\small\n\\caption{Matched resource-model safety checks and seeded execution testing. Random-testing hits count failing-case seed trials, not independent defects.}\\label{tab:baseline_results}\n\\begin{tabular}{p{.38\\linewidth}p{.19\\linewidth}p{.31\\linewidth}}\\toprule\nMethod & Scope & Observed result \\\\\\midrule\nPython exhaustive & 306 cases & 245 safe; 61 unsafe. \\\\\nTLC, separate TLA+ encoding & Same 306 cases & 245 safe; 61 unsafe; no disagreement. \\\\\nTLC complete passing cases & 245 cases & Equal reachable-state counts in all 245. \\\\\n'
    for b in (1,10,100):tex+=f'Random testing, {b} executions & 610 failing-case trials & {rand["budgets"][str(b)]["hits"]}/610 hits. \\\\\n'
    tex+='\\bottomrule\\end{tabular}\\end{table}\n';(M/'baseline_results.tex').write_text(tex)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(1,2,figsize=(10.5,3.7),layout='constrained')
    xs=range(3);labels=['Duplicate ID','Over capacity','Expired']
    for offset,sched,color,label in [(-.18,'prepare_barrier','#2878a0','Prepare barrier'),(.18,'expiry_boundary','#d27927','Expiry boundary')]:
        x=impl['modes']['split'][sched];ax[0].bar([v+offset for v in xs],[x[k] for k in ['duplicate_key','over_capacity','expired_delivery']],width=.36,color=color,label=label)
    ax[0].set_xticks(list(xs),labels);ax[0].set_ylim(0,350);ax[0].set_ylabel('Failing batches out of 340');ax[0].set_title('(a) Split implementation findings');ax[0].legend(frameon=False,fontsize=8)
    budgets=[1,10,100];hits=[rand['budgets'][str(b)]['hits']/610 for b in budgets]
    ax[1].plot(budgets,hits,'o-',color='#2878a0');ax[1].axhline(1,color='#596666',ls='--',label='Exhaustive reference: 61/61 cases')
    ax[1].set_xscale('log');ax[1].set_xticks(budgets,[str(x) for x in budgets]);ax[1].set_ylim(0,1.06);ax[1].set_xlabel('Executions per seed trial');ax[1].set_ylabel('Fraction of 610 failing-case trials hit');ax[1].set_title('(b) Uniform enabled-action testing');ax[1].legend(frameon=False,fontsize=8,loc='lower right')
    fig.savefig(ROOT/'figures/implementation_baseline.png',dpi=230);plt.close(fig)
    batches=json.loads((ROOT/'implementation/threaded_batches.json').read_text())
    report={'tlc_cases':tlc['cases'],'tlc_agreements':tlc['agree'],'state_count_agreements':tlc['safe_complete_state_counts_agree'],
      'threaded_batches':len(batches),'request_executions':sum(x['requests'] for x in batches),
      'duplicate_without_capacity_excess':{sched:sum(r['mode']=='split' and r['schedule']==sched and r['findings']['duplicate_key'] and not r['findings']['over_capacity'] for r in batches) for sched in ('prepare_barrier','expiry_boundary')},
      'random_executions':rand['executions'],'random_false_positives':rand['false_positive_trials']}
    (ROOT/'implementation/analysis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
