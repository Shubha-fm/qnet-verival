"""Audit case IDs, graph hashes, cross-check verdicts, and every sampled trace by replay."""
from pathlib import Path
import gzip,hashlib,json,sys
from model import *
from random_testing import cfg
root=Path(__file__).resolve().parents[1]
records=[json.loads(p.read_text()) for p in (root/'dataset/outcomes').glob('*.json')]
assert len(records)==522
complete=0;checked_witnesses=0
for r in records:
 canonical=json.dumps(r['config'],sort_keys=True,separators=(',',':'))
 assert hashlib.sha256(canonical.encode()).hexdigest()[:16]==r['case_id']
 if r['status']=='capped':
  assert all(v is None for v in r['properties'].values());continue
 complete+=1;assert r['crosscheck_agrees']
 g=root/'dataset/graphs'/f"{r['case_id']}.graph.gz"
 assert hashlib.sha256(g.read_bytes()).hexdigest()==r['graph_sha256']
 c=cfg(r['config'])
 for prop,w in r['witnesses'].items():
  s=initial(c);state_by_id={0:s}
  for edge in w['steps']:
   candidates=[t for a,t in successors(s,c) if a==edge['action']]
   if edge['action'] in ('TerminalStutter','DeadlockStutter'):
    assert not list(successors(s,c));candidates=[s]
   assert len(candidates)==1,(r['case_id'],prop,edge)
   s=candidates[0]
   if edge['to'] in state_by_id:assert state_by_id[edge['to']]==s
   state_by_id[edge['to']]=s
  if prop=='P8_termination':
   loop=w['steps'][w['loop_start']:];assert loop[0]['from']==loop[-1]['to']
   assert all(not terminal(state_by_id[e['from']]) for e in loop)
  else:assert prop in violations(s,c)
  checked_witnesses+=1
scenarios={r['scenario_id']:cfg(r['config']) for r in json.loads((root/'dataset/testing_scenarios.json').read_text())}
truth={r['scenario_id']:{p for p,v in r['properties'].items() if not v} for r in json.loads((root/'results/testing_truth.json').read_text())}
traces=0;steps=0;false_witnesses=0;cutoffs=0
with gzip.open(root/'dataset/random_traces.jsonl.gz','rt') as f:
 for line in f:
  rec=json.loads(line);c=scenarios[rec['scenario_id']];s=initial(c);bad=set();states=[s]
  for a in rec['actions']:
   if a=='DeadlockStutter':
    assert not terminal(s) and not list(successors(s,c));bad.add('P8_termination')
   else:
    candidates=[t for label,t in successors(s,c) if label==a]
    assert len(candidates)==1,(rec['scenario_id'],a)
    s=candidates[0];bad.update(violations(s,c))
   states.append(s)
  if rec['outcome']=='cycle':
   assert states[-1]==states[rec['loop_start']]
   assert all(not terminal(s) for s in states[rec['loop_start']:]);bad.add('P8_termination')
  if rec['outcome']=='terminal':assert terminal(s)
  if rec['outcome']=='cutoff':cutoffs+=1
  assert bad==set(rec['violations'])
  assert bad<=truth[rec['scenario_id']]
  traces+=1;steps+=len(rec['actions'])
assert traces==120000
report={'case_records':len(records),'complete_graphs_hash_checked':complete,'exhaustive_witnesses_replayed':checked_witnesses,'random_traces_replayed':traces,'random_actions_replayed':steps,'false_witnesses':false_witnesses,'random_cutoffs':cutoffs}
(root/'results/audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
