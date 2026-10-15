"""Seeded enabled-action testing of the same model. No physical probability claims."""
from dataclasses import asdict
from pathlib import Path
import csv,gzip,hashlib,json,random,sys,time
from model import *
root=Path(__file__).resolve().parents[1]

def scenarios():
    out=[]
    for r in (1,2):
        for m in MUTANTS:
            out.append({'scenario_id':f'{m}_r{r}','config':asdict(Config(relays=r,mutant=m,deadline=5 if m=='missing_timeout' else 4*(r+1)+8,failures=True,max_states=100000))})
    for mode in ('atomic','split','reserved'):
        for shared in (False,True):
            out.append({'scenario_id':f'{mode}_shared{int(shared)}','config':asdict(Config(relays=0,sessions=2,shared_key=shared,delivery_mode=mode,deadline=13,failures=True))})
    return out

def cfg(obj):
    x=dict(obj);x['route_lengths']=tuple(x['route_lengths']);x['mutations']=tuple(x['mutations']);return Config(**x)

def episode(c,rng,scheduler):
    s=initial(c);seen={s:0};actions=[];bad=set();loop_start=None
    outcome='cutoff'
    for _ in range(200):
        choices=list(successors(s,c))
        if not choices:
            if terminal(s):outcome='terminal'
            else:bad.add('P8_termination');outcome='deadlock';loop_start=len(actions);actions.append('DeadlockStutter')
            break
        if scheduler=='uniform':a,t=choices[rng.randrange(len(choices))]
        else:
            weights=[0.02 if 'LinkFailure' in a else 0.05 if 'Expire' in a else 0.10 if 'Delay' in a else 1.0 for a,t in choices]
            a,t=rng.choices(choices,weights=weights,k=1)[0]
        actions.append(a);s=t;bad.update(violations(s,c))
        if terminal(s):outcome='terminal';break
        if s in seen:
            bad.add('P8_termination');loop_start=seen[s];outcome='cycle';break
        seen[s]=len(actions)
    return {'actions':actions,'steps':len(actions),'violations':sorted(bad),'outcome':outcome,'loop_start':loop_start}

def main():
    cases=scenarios();(root/'dataset/testing_scenarios.json').write_text(json.dumps(cases,indent=2))
    truth=[]
    for case in cases:
        r=explore(cfg(case['config']));r['scenario_id']=case['scenario_id'];truth.append(r)
    (root/'results/testing_truth.json').write_text(json.dumps(truth,indent=2))
    trial=[];total=0;start=time.perf_counter()
    with gzip.open(root/'dataset/random_traces.writing.gz','wt') as f:
        for case in cases:
            c=cfg(case['config'])
            for scheduler in ('uniform','progress_biased'):
                for seed in range(20):
                    # Stable independent stream for this scenario, scheduler, and seed.
                    key=f"20261015:{case['scenario_id']}:{scheduler}:{seed}"
                    rng=random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16],16))
                    found=set();first=None
                    for ep in range(1,101):
                        rec=episode(c,rng,scheduler)
                        if rec['violations'] and first is None:first=ep
                        found.update(rec['violations'])
                        rec.update(scenario_id=case['scenario_id'],scheduler=scheduler,seed=seed,episode=ep)
                        f.write(json.dumps(rec,separators=(',',':'))+'\n');total+=1
                        if ep in (10,50,100):
                            trial.append({'scenario_id':case['scenario_id'],'scheduler':scheduler,'seed':seed,'budget_traces':ep,'any_failure':bool(found),'found_properties':sorted(found),'first_failure_episode':first})
            print(case['scenario_id'],total,flush=True)
    import os
    staged=root/'dataset/random_traces.writing.gz'
    with staged.open('rb') as checked: os.fsync(checked.fileno())
    staged.replace(root/'dataset/random_traces.jsonl.gz')
    (root/'results/testing_trials.json').write_text(json.dumps(trial,indent=2))
    (root/'results/testing_metadata.json').write_text(json.dumps({'traces':total,'scenarios':len(cases),'seeds':20,'traces_per_seed':100,'schedulers':['uniform','progress_biased'],'seed_prefix':'20261015','max_steps':200,'seconds':time.perf_counter()-start},indent=2))

if __name__=='__main__':main()
