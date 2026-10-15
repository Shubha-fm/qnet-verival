"""Sequential experiment controller. Each case runs in a fresh process for RSS isolation."""
import argparse,collections,json,os,platform,subprocess,sys,time
from dataclasses import asdict
from pathlib import Path
from design import design
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int);a=ap.parse_args()
for d in ('dataset/configurations','dataset/graphs','dataset/outcomes','results'): (root/d).mkdir(parents=True,exist_ok=True)
cases=design();(root/'dataset/design.json').write_text(json.dumps(cases,indent=2))
subprocess.run(['g++','-O2','-std=c++17',str(root/'src/checker.cpp'),'-o',str(root/'src/graph_checker')],check=True)
log=root/'results/benchmark_progress.jsonl'
for j,case in enumerate(cases[:a.limit]):
 spec=root/'dataset/configurations'/f"{case['case_id']}.json";spec.write_text(json.dumps(case,indent=2))
 out=root/'dataset/outcomes'/f"{case['case_id']}.json"
 if not out.exists():
  subprocess.run([sys.executable,str(root/'src/worker.py'),str(spec),str(out),'--graph-dir',str(root/'dataset/graphs'),'--checker',str(root/'src/graph_checker')],check=True,timeout=180)
 r=json.loads(out.read_text())
 rec={'index':j+1,'total':len(cases),'case_id':case['case_id'],'status':r['status'],'states':r.get('states',r.get('discovered_states')),'seconds':r['seconds']}
 with log.open('a') as f:f.write(json.dumps(rec)+'\n')
 if j%20==0 or j==len(cases)-1: print(rec,flush=True)
(root/'results/environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'cpu':subprocess.check_output(['lscpu'],text=True),'compiler':subprocess.check_output(['g++','--version'],text=True),'execution':'Sequential cases, fresh worker per case; no parallel workers.'},indent=2))
