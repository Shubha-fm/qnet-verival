from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[1]
ids=json.loads((root/'results/graph_repairs_needed.json').read_text());log=[]
for cid in ids:
 out=root/'dataset/outcomes'/f'{cid}.json';before=json.loads(out.read_text())
 repaired=root/'results'/f'{cid}.reexport.json'
 subprocess.run([sys.executable,str(root/'src/worker.py'),str(root/'dataset/configurations'/f'{cid}.json'),str(repaired),'--graph-dir',str(root/'dataset/graphs'),'--checker',str(root/'src/graph_checker')],check=True)
 after=json.loads(repaired.read_text())
 for field in ('states','transitions','properties','witnesses','states_with_delivery','states_all_delivered'):
  assert after[field]==before[field],(cid,field)
 assert after['graph_sha256']==before['graph_sha256'],cid
 log.append({'case_id':cid,'structural_outcomes_match':True,'compressed_digest_matches_original':True})
print(json.dumps(log,indent=2));(root/'results/export_repair_audit.json').write_text(json.dumps(log,indent=2))
