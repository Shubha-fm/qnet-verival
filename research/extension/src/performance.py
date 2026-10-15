"""Repeated isolated-process timing after the sweep and testing have finished."""
from dataclasses import asdict
from pathlib import Path
import json,subprocess,sys
from model import Config
root=Path(__file__).resolve().parents[1]
configs=[(f'chain_r{r}',Config(relays=r,deadline=4*(r+1)+8,failures=True,max_states=300000)) for r in range(1,8)]
configs += [(f'two_sessions_{m}',Config(relays=1,sessions=2,shared_key=True,delivery_mode=m,deadline=17,failures=True,max_states=100000)) for m in ('atomic','split','reserved')]
(root/'results/performance_raw').mkdir(exist_ok=True)
for label,c in configs:
    for rep in range(8): # 1 warmup, 7 measured
        rec={'case_id':label+f'_rep{rep}','suite':'performance','tag':label,'memberships':['performance'],'config':asdict(c)}
        spec=root/'results/performance_raw'/f'{label}_rep{rep}.spec.json';spec.write_text(json.dumps(rec))
        out=root/'results/performance_raw'/f'{label}_rep{rep}.json'
        subprocess.run([sys.executable,str(root/'src/worker.py'),str(spec),str(out)],check=True,timeout=180)
    print(label,flush=True)
