"""Independent TLA+ model baseline. Compare aggregate safety, not TLA+ liveness.

No Python state graph or safety labels are supplied to TLC. The constants and
independently authored TLA+ module are its only model inputs. Java process
startup, parsing, exploration and shutdown are included in wall time.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib, json, re, subprocess, time
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'baseline'; OUT=BASE/'results'; OUT.mkdir(exist_ok=True)
JAR=ROOT/'tools/tla2tools.jar'
CASES=json.loads((ROOT/'measurement/results/pool_verification.json').read_text())

def run(case):
    c=case['config']; ident=case['case_id']; folder=OUT/ident;folder.mkdir(exist_ok=True)
    cfg=(f'CONSTANTS N={c["requests"]} C={c["capacity"]} Mode="{c["mode"]}" '
         f'L={c["expiry_steps"]} D={c["deadline_steps"]}\n'
         'INIT Init\nNEXT Next\nINVARIANT Safety\nCHECK_DEADLOCK FALSE\n')
    (folder/'ResourcePool.cfg').write_text(cfg)
    # Avoid shared TLC state directories. Model remains identical for all cases.
    (folder/'ResourcePool.tla').write_bytes((BASE/'ResourcePool.tla').read_bytes())
    start=time.perf_counter()
    scratch=folder/'java_tmp';scratch.mkdir(exist_ok=True)
    command=['java',f'-Djava.io.tmpdir={scratch}','-XX:+UseSerialGC','-Xmx512m','-cp',str(JAR),
             'tlc2.TLC','-workers','1','-seed','1','-config','ResourcePool.cfg','ResourcePool.tla']
    try:
        proc=subprocess.run(command,cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
        log=proc.stdout;code=proc.returncode
    except subprocess.TimeoutExpired as e:
        log=str(e.stdout);code=-1
    seconds=time.perf_counter()-start;(folder/'tlc.log').write_text(log)
    if 'Invariant Safety is violated' in log: verdict='fail'
    elif 'Model checking completed. No error has been found.' in log: verdict='pass'
    else:verdict='unknown'
    expected='pass' if all(v for k,v in case['properties'].items() if k!='I4_termination') else 'fail'
    matches=re.findall(r'([\d,]+) states generated, ([\d,]+) distinct states found',log)
    result={'case_id':ident,'config':c,'verdict':verdict,'expected_safety':expected,
      'agrees':verdict==expected,'returncode':code,'process_wall_seconds':seconds,
      'generated_states':int(matches[-1][0].replace(',','')) if matches else None,
      'distinct_states':int(matches[-1][1].replace(',','')) if matches else None,
      'log_sha256':hashlib.sha256(log.encode()).hexdigest()}
    result['complete_state_count_agrees']=(result['distinct_states']==case['states']) if verdict=='pass' else None
    (folder/'result.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    results=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,c) for c in CASES]
        for f in as_completed(futures):
            r=f.result();results.append(r)
            if len(results)%30==0:print(f'TLC completed {len(results)}/{len(CASES)}',flush=True)
    results.sort(key=lambda r:r['case_id']);(BASE/'tlc_results.json').write_text(json.dumps(results,indent=2))
    summary={'cases':len(results),'agree':sum(r['agrees'] for r in results),
      'pass':sum(r['verdict']=='pass' for r in results),'fail':sum(r['verdict']=='fail' for r in results),
      'unknown':sum(r['verdict']=='unknown' for r in results),'jar_sha256':hashlib.sha256(JAR.read_bytes()).hexdigest(),
      'safe_complete_state_counts_agree':sum(r['complete_state_count_agrees'] is True for r in results),
      'scope':'Aggregate I1-I3 safety only; no liveness equivalence claim; two concurrent single-worker Java runs.'}
    (BASE/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
    assert summary['agree']==len(CASES), 'Inspect unknown or disagreeing logs before reporting agreement.'
