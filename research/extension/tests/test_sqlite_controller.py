import tempfile,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'implementation'))
from sqlite_controller import KeyController,findings

class SQLiteControllerTests(unittest.TestCase):
    def make(self,mode,capacity=1):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        return KeyController(Path(folder.name)/'keys.sqlite',capacity,mode,3)
    def test_split_reuses_key_even_without_capacity_excess(self):
        c=self.make('split',2);a=c.prepare('a',0);b=c.prepare('b',0)
        self.assertTrue(c.commit('a',a,0));self.assertTrue(c.commit('b',b,0))
        f=findings(c.snapshot(),2,3);self.assertTrue(f['duplicate_key']);self.assertFalse(f['over_capacity'])
    def test_reservation_prevents_competing_prepare(self):
        c=self.make('reserved');self.assertIsNotNone(c.prepare('a',0));self.assertIsNone(c.prepare('b',0))
    def test_reservation_checks_owner(self):
        c=self.make('reserved');k=c.prepare('a',0);self.assertFalse(c.commit('b',k,0));self.assertTrue(c.commit('a',k,0))
    def test_reserved_expiry_boundary(self):
        c=self.make('reserved');k=c.prepare('a',0);self.assertFalse(c.commit('a',k,3));c.abort('a',k,3)
        self.assertEqual(c.snapshot()['wasted'],1);self.assertFalse(c.snapshot()['deliveries'])
    def test_abort_releases_only_owned_fresh_reservation(self):
        c=self.make('reserved');k=c.prepare('a',0);c.abort('b',k,1);self.assertIsNone(c.prepare('b',1));c.abort('a',k,1);self.assertEqual(c.prepare('b',1),k)
    def test_atomic_expiry_boundary(self):
        c=self.make('atomic');self.assertFalse(c.commit('a',None,3));self.assertTrue(c.commit('a',None,2));self.assertFalse(c.commit('b',None,2))
    def test_split_stale_commit_control(self):
        c=self.make('split');k=c.prepare('a',0);self.assertTrue(c.commit('a',k,3));self.assertTrue(findings(c.snapshot(),1,3)['expired_delivery'])
    def test_zero_capacity(self):
        for mode in ('atomic','split','reserved'):
            c=self.make(mode,0);k=c.prepare('a',0) if mode!='atomic' else None
            self.assertFalse(c.commit('a',k,0))
