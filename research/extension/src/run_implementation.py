"""Controlled threaded implementation experiments and model-witness replay.

The SQL controller does not import the abstract model. Only this harness imports
it to compute projections and replay the previously exported witness actions.
"""
from pathlib import Path
import sys,json,tempfile,sqlite3,hashlib,time
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'implementation'))
from sqlite_controller import KeyController,findings
from measurement_pool import PoolConfig,initial,successors
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'implementation';OUT.mkdir(exist_ok=True)
CASES=json.loads((ROOT/'measurement/results/pool_verification.json').read_text())

def batch(n,c,mode,schedule,repetition):
    expiry=3;barrier=Barrier(n);results=[]
    with tempfile.TemporaryDirectory() as td:
        ctl=KeyController(Path(td)/'pool.sqlite',c,mode,expiry)
        def worker(i):
            req=str(i)
            key=ctl.prepare(req,0) if mode!='atomic' else None
            barrier.wait(timeout=15)  # All prepare operations precede every commit.
            now=expiry if schedule=='expiry_boundary' else 0
            ok=ctl.commit(req,key,now)
            if not ok:ctl.abort(req,key,now)
            return {'request':req,'prepared_key':key,'delivered':ok}
        with ThreadPoolExecutor(max_workers=n) as pool:results=list(pool.map(worker,range(n)))
        snap=ctl.snapshot();bad=findings(snap,c,expiry)
    return {'requests':n,'capacity':c,'mode':mode,'schedule':schedule,'repetition':repetition,
       'delivered':len(snap['deliveries']),'findings':bad,'requests_log':results,'database_snapshot':snap}

def replay(case,prop,witness):
    c=PoolConfig(**case['config']);phases=['waiting']*c.requests;keys={};s=initial(c);history=[]
    with tempfile.TemporaryDirectory() as td:
        ctl=KeyController(Path(td)/'pool.sqlite',c.capacity,c.mode,c.expiry_steps)
        for edge in witness['steps']:
            action=edge['action'];expected=[t for a,t in successors(s,c) if a==action];assert len(expected)==1
            req=None
            if action in ('Prepare','AtomicDeliver','AbortWaiting'):req=next(i for i,x in enumerate(phases) if x=='waiting')
            if action in ('Commit','AbortPrepared'):req=next(i for i,x in enumerate(phases) if x=='prepared')
            if action=='Prepare':
                keys[req]=ctl.prepare(str(req),s.clock);assert keys[req] is not None;phases[req]='prepared'
            elif action in ('Commit','AtomicDeliver'):
                assert ctl.commit(str(req),keys.get(req),s.clock);phases[req]='delivered'
            elif action.startswith('Abort'):
                ctl.abort(str(req),keys.get(req),s.clock);phases[req]='aborted'
            elif action!='Tick':raise AssertionError(action)
            snap=ctl.snapshot();rows=snap['deliveries']
            projection={'waiting':phases.count('waiting'),'prepared':phases.count('prepared'),'delivered':len(rows),
              'aborted':phases.count('aborted'),'free':c.capacity-len(rows)-snap['held']-snap['wasted'],
              'clock':expected[0].clock,'stale_delivery':any(r['at']>=c.expiry_steps for r in rows)}
            assert projection==asdict(expected[0]),(case['case_id'],action,projection,asdict(expected[0]))
            history.append({'action':action,'at':s.clock,'projection':projection});s=expected[0]
        snap=ctl.snapshot()
    return {'case_id':case['case_id'],'property':prop,'steps_checked':len(history),'projection_agrees':True,
       'history':history,'findings':findings(snap,c.capacity,c.expiry_steps),'snapshot':snap}

if __name__=='__main__':
    start=time.perf_counter();profiles=sorted({(r['config']['requests'],r['config']['capacity']) for r in CASES})
    runs=[]
    for n,c in profiles:
        for mode in ('atomic','split','reserved'):
            for schedule in ('prepare_barrier','expiry_boundary'):
                for repeat in range(20):runs.append(batch(n,c,mode,schedule,repeat))
        print(f'Implementation profile N={n} C={c}: {len(runs)} batches',flush=True)
    replays=[replay(r,p,w) for r in CASES for p,w in r['witnesses'].items()]
    (OUT/'threaded_batches.json').write_text(json.dumps(runs,separators=(',',':')))
    (OUT/'witness_replays.json').write_text(json.dumps(replays,indent=2))
    summary={'profiles':len(profiles),'batches':len(runs),'request_executions':sum(r['requests'] for r in runs),
      'repetitions_per_cell':20,'witness_replays':len(replays),'witness_steps':sum(r['steps_checked'] for r in replays),
      'projection_mismatches':0,'seconds':time.perf_counter()-start,'python_sqlite_version':sqlite3.sqlite_version,
      'modes':{mode:{sched:{'batches':sum(r['mode']==mode and r['schedule']==sched for r in runs),
        **{k:sum(r['mode']==mode and r['schedule']==sched and r['findings'][k] for r in runs) for k in ('duplicate_key','over_capacity','expired_delivery')}}
        for sched in ('prepare_barrier','expiry_boundary')} for mode in ('atomic','split','reserved')}}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
