import sys, unittest
from collections import deque
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import *

class ReferenceChecks(unittest.TestCase):
    def test_baseline_has_success_and_passes(self):
        r = explore(Config())
        self.assertTrue(all(r['properties'].values()))
        self.assertGreater(r['states_all_delivered'], 0)

    def test_consumed_after_delivery_uses_snapshot(self):
        c = Config()
        s = State((Session(route=0, auth=True, links=(7,7), ack=1, confirm=True, stored=True),), (False,))
        t = next(t for a,t in successors(s,c) if a.endswith(':Deliver'))
        self.assertTrue(t.consumed[0])
        self.assertFalse(violations(t,c))
        self.assertTrue(t.sessions[0].receipt[4])

    def test_invalid_abort_at_budget_boundary(self):
        c = Config(deadline=5, mutant='invalid_abort')
        s = State((Session(steps=4),), (False,))
        t = next(t for a,t in successors(s,c) if 'AbortWithoutCause' in a)
        self.assertIn('P7_valid_abort', violations(t,c))

    def test_shared_key_reuse_fault(self):
        c = Config(relays=0, sessions=2, shared_key=True, mutant='omit_consume', deadline=12)
        r = explore(c)
        self.assertFalse(r['properties']['P9_single_use'])
        self.assertGreater(r['states_all_delivered'], 0)

    def test_all_witness_edges_replay(self):
        for m in MUTANTS:
            c = Config(deadline=5 if m == 'missing_timeout' else 16, mutant=m)
            r = explore(c)
            for prop, w in r['witnesses'].items():
                s = initial(c); reached = {0:s}
                for edge in w['steps']:
                    choices = list(successors(s,c))
                    if not choices:
                        choices = [('TerminalStutter' if terminal(s) else 'DeadlockStutter', s)]
                    candidates = [t for a,t in choices if a == edge['action']]
                    self.assertEqual(len(candidates), 1)
                    s = candidates[0]
                    if edge['to'] in reached:
                        self.assertEqual(reached[edge['to']],s)
                    reached[edge['to']] = s
                if prop != 'P8_termination':
                    self.assertIn(prop, violations(s,c))
                else:
                    loop = w['steps'][w['loop_start']:]
                    self.assertEqual(loop[0]['from'], loop[-1]['to'])
                    self.assertTrue(all(not terminal(reached[e['from']]) for e in loop))

    def test_progress_against_independent_cycle_detection(self):
        for m in ('none', 'retry_loop', 'missing_timeout'):
            c = Config(deadline=5 if m == 'missing_timeout' else 16, mutant=m)
            states = [initial(c)]; ids = {states[0]:0}; adj=[]
            for s in states:
                edges=[]
                for _,t in successors(s,c):
                    if t not in ids:
                        ids[t]=len(states); states.append(t)
                    edges.append(ids[t])
                adj.append(edges or [ids[s]])
            active={i for i,s in enumerate(states) if not terminal(s)}
            degree={i:0 for i in active}
            for u in active:
                for v in adj[u]:
                    if v in active: degree[v]+=1
            queue=deque(i for i,d in degree.items() if d==0); removed=0
            while queue:
                u=queue.popleft(); removed+=1
                for v in adj[u]:
                    if v in degree:
                        degree[v]-=1
                        if degree[v]==0: queue.append(v)
            acyclic=removed==len(active)
            self.assertEqual(acyclic, explore(c)['properties']['P8_termination'])

    def test_abort_label_variant_is_state_graph_equivalent(self):
        def edges(c):
            states=[initial(c)]; seen={states[0]}; result=set()
            for s in states:
                for _,t in successors(s,c):
                    result.add((s,t))
                    if t not in seen: seen.add(t); states.append(t)
            return result
        self.assertEqual(edges(Config()), edges(Config(mutant='abort_label')))

    def test_cap_does_not_report_pass(self):
        with self.assertRaises(RuntimeError): explore(Config(max_states=5))

    def test_split_expiry_is_measured_at_commit(self):
        c = Config(relays=0, delivery_mode='split', failures=False)
        receipt=(True,True,True,True,True,True)
        q=Session(route=0,auth=True,links=(7,),confirm=True,stored=True,pending=True,staged_receipt=receipt,expired=True)
        s=State((q,),(False,),(-1,))
        t=next(t for a,t in successors(s,c) if a.endswith(':CommitDelivery'))
        self.assertIn('P5_fresh_at_delivery',violations(t,c))
        self.assertIn('P6_delivery_contract',violations(t,c))

    def test_reserved_rejects_expired_commit_and_releases(self):
        c=Config(relays=0,delivery_mode='reserved',failures=False)
        q=Session(route=0,auth=True,links=(7,),confirm=True,stored=True,pending=True,staged_receipt=(True,)*6,expired=True)
        s=State((q,),(False,),(0,))
        choices=list(successors(s,c))
        self.assertFalse(any('CommitDelivery' in a for a,t in choices))
        t=next(t for a,t in choices if a.endswith(':Abort'))
        self.assertEqual(t.owners,(-1,))

    def test_split_race_and_reservation_repair(self):
        for mode,expected in [('atomic',True),('split',False),('reserved',True)]:
            c=Config(relays=0,sessions=2,shared_key=True,failures=False,deadline=12,delivery_mode=mode)
            r=explore(c)
            self.assertEqual(r['properties']['P9_single_use'],expected)
            if expected:self.assertTrue(all(r['properties'].values()))

    def test_localized_hop_fault_trace(self):
        c=Config(relays=2,deadline=20,mutant='skip_ec',target_hop=2)
        r=explore(c);self.assertFalse(r['properties']['P2_postprocess'])
        w=r['witnesses']['P2_postprocess']['steps']
        self.assertTrue(any(e['action'].endswith('PAWithoutEC(2)') for e in w))
        self.assertFalse(any('PAWithoutEC(0)' in e['action'] for e in w))

    def test_combined_faults_are_applied(self):
        r=explore(Config(deadline=16,mutations=('skip_ec','invalid_abort')))
        self.assertFalse(r['properties']['P2_postprocess'])
        self.assertFalse(r['properties']['P7_valid_abort'])

if __name__ == '__main__': unittest.main(verbosity=2)
