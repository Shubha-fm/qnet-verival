import sys,unittest,csv,json,hashlib
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import measurement_pool as mp
root=Path(__file__).resolve().parents[1]

class MeasurementChecks(unittest.TestCase):
 def test_all_original_checksums(self):
  meta=json.loads((root/'measurement/source/zenodo_record.json').read_text())
  self.assertEqual(len(meta['files']),39)
  for f in meta['files']:
   data=(root/'measurement/source'/f['key']).read_bytes();self.assertEqual(hashlib.md5(data).hexdigest(),f['checksum'].removeprefix('md5:'))
 def test_primary_observations_do_not_pool_auxiliary_subset(self):
  audit=json.loads((root/'measurement/results/source_audit.json').read_text())
  self.assertEqual(audit['source_rows']-audit['auxiliary_multiset_overlap'],audit['primary_rows'])
  self.assertEqual(audit['primary_rows'],48507)
 def test_exact_capacity_boundary(self):
  self.assertEqual(int(Decimal('255999')*Decimal('.001')/256),0)
  self.assertEqual(int(Decimal('256000')*Decimal('.001')/256),1)
 def test_capacity_saturation_preserves_selected_verdicts(self):
  for mode in ('atomic','split','reserved'):
   for L in (3,12):
    self.assertEqual(mp.check(mp.PoolConfig(2,2,mode,L,6))['properties'],mp.check(mp.PoolConfig(2,5,mode,L,6))['properties'])
 def test_freshness_at_commit(self):
  s=mp.PoolState(waiting=0,prepared=1,delivered=0,aborted=0,free=1,clock=3)
  split=mp.PoolConfig(1,1,'split',3,12)
  t=next(t for a,t in mp.successors(s,split) if a=='Commit')
  self.assertIn('I2_fresh_commit',mp.violations(t,split))
  reserve=mp.PoolConfig(1,1,'reserved',3,12)
  self.assertFalse(any(a=='Commit' for a,t in mp.successors(s,reserve)))
 def test_abort_releases_only_unexpired_reservation(self):
  c=mp.PoolConfig(2,1,'reserved',12,6)
  s=mp.PoolState(1,1,0,0,0,clock=6)
  t=next(t for a,t in mp.successors(s,c) if a=='AbortPrepared');self.assertEqual(t.free,1)
  expired=mp.PoolConfig(2,1,'reserved',3,6)
  t=next(t for a,t in mp.successors(s,expired) if a=='AbortPrepared');self.assertEqual(t.free,0)
 def test_all_executed_resource_checks_have_agreeing_graph_oracle(self):
  rs=json.loads((root/'measurement/results/pool_verification.json').read_text());self.assertEqual(len(rs),306)
  self.assertTrue(all(r['crosscheck_agrees'] for r in rs))
  for r in rs:
   if r['config']['mode']!='split':self.assertTrue(all(r['properties'].values()))

if __name__=='__main__':unittest.main(verbosity=2)
