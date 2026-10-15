"""Seeded random execution baseline matched to all 306 resource cases.

Uniform choice over enabled labeled successors; no probabilistic deployment
interpretation. Ten independent seed trials, each with 100 executions, per case.
"""
from pathlib import Path
import json,random,time
from measurement_pool import PoolConfig,initial,successors,violations,terminal
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    cases=json.loads((ROOT/'measurement/results/pool_verification.json').read_text());records=[];start=time.perf_counter()
    for case in cases:
        c=PoolConfig(**case['config'])
        for seed in range(10):
            rng=random.Random(int(case['case_id'],16)+seed);first=None;actions=0
            for episode in range(1,101):
                s=initial(c)
                for step in range(c.deadline_steps+c.requests+2):
                    if violations(s,c) and first is None:first=episode
                    if terminal(s):break
                    options=list(successors(s,c));assert options
                    _,s=rng.choice(options);actions+=1
                else:raise AssertionError('Unexpected cutoff')
            records.append({'case_id':case['case_id'],'seed':seed,'first_hit_episode':first,
              'reference_safety_failure':not all(v for k,v in case['properties'].items() if k!='I4_termination'),
              'actions':actions})
    out=ROOT/'baseline';(out/'random_trials.json').write_text(json.dumps(records,indent=2))
    summary={'seed_trials':len(records),'executions':len(records)*100,'actions':sum(r['actions'] for r in records),
      'reference_failing_cases':sum(not all(v for k,v in x['properties'].items() if k!='I4_termination') for x in cases),
      'false_positive_trials':sum(r['first_hit_episode'] is not None and not r['reference_safety_failure'] for r in records),
      'seconds':time.perf_counter()-start,'budgets':{str(b):{
      'failing_case_trials':sum(r['reference_safety_failure'] for r in records),
      'hits':sum(r['reference_safety_failure'] and r['first_hit_episode'] is not None and r['first_hit_episode']<=b for r in records),
      'cases_hit_in_at_least_one_seed':len({r['case_id'] for r in records if r['reference_safety_failure'] and r['first_hit_episode'] is not None and r['first_hit_episode']<=b})}
      for b in (1,10,100)}}
    (out/'random_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
