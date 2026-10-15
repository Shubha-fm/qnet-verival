"""Verify independent-baseline logs, SQL histories and recorded denominators."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'implementation'))
from sqlite_controller import findings
from run_implementation import replay

if __name__=='__main__':
    cases={r['case_id']:r for r in json.loads((ROOT/'measurement/results/pool_verification.json').read_text())}
    results=json.loads((ROOT/'baseline/tlc_results.json').read_text());assert len(results)==len(cases)==306
    module=(ROOT/'baseline/ResourcePool.tla').read_bytes()
    for r in results:
        folder=ROOT/'baseline/results'/r['case_id'];log=(folder/'tlc.log').read_bytes()
        assert hashlib.sha256(log).hexdigest()==r['log_sha256']
        assert (folder/'ResourcePool.tla').read_bytes()==module
        assert r['agrees'] and r['verdict'] in ('pass','fail')
        assert ('Invariant Safety is violated' in log.decode())==(r['verdict']=='fail')
        if r['verdict']=='pass':assert r['complete_state_count_agrees'] and r['distinct_states']==cases[r['case_id']]['states']
    runs=json.loads((ROOT/'implementation/threaded_batches.json').read_text());assert len(runs)==2040
    for r in runs:
        snap=r['database_snapshot'];assert r['findings']==findings(snap,r['capacity'],3)
        assert r['delivered']==len(snap['deliveries'])
        assert len(r['requests_log'])==r['requests']
        prepares=[e['seq'] for e in snap['events'] if e['operation']=='prepare']
        commits=[e['seq'] for e in snap['events'] if e['operation'] in ('deliver','reject')]
        if prepares and commits:assert max(prepares)<min(commits)
        assert all(x['at']==(3 if r['schedule']=='expiry_boundary' else 0) for x in snap['deliveries'])
        if r['mode']!='split':assert not any(r['findings'].values())
    replays=json.loads((ROOT/'implementation/witness_replays.json').read_text());assert len(replays)==80
    for r in replays:
        case=cases[r['case_id']];fresh=replay(case,r['property'],case['witnesses'][r['property']]);assert fresh==r
    trials=json.loads((ROOT/'baseline/random_trials.json').read_text());assert len(trials)==3060
    assert len({(r['case_id'],r['seed']) for r in trials})==3060
    assert all(r['first_hit_episode'] is None or (r['reference_safety_failure'] and 1<=r['first_hit_episode']<=100) for r in trials)
    report={'tlc_logs_verified':len(results),'sql_batches_verified':len(runs),'request_executions':sum(x['requests'] for x in runs),
      'witness_replays_reexecuted':len(replays),'projection_steps':sum(r['steps_checked'] for r in replays),
      'random_seed_trials_checked':len(trials),'unit_tests_expected':28}
    (ROOT/'implementation/audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
