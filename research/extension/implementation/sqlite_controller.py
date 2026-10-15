"""Executable SQLite key-lifecycle controller for the integration case study.

This is newly implemented research code, not an existing production QKD KMS.
No secret key material is stored. Key IDs stand for synthetic resource units.
The caller supplies a controlled integer clock for deterministic expiry tests.
"""
import sqlite3

class KeyController:
    def __init__(self,path,capacity,mode,expires):
        if mode not in ('atomic','split','reserved'):raise ValueError(mode)
        self.path=str(path);self.mode=mode;self.capacity=capacity;self.expires=expires
        with self.connect() as db:
            db.executescript('''CREATE TABLE keys(id INTEGER PRIMARY KEY, state TEXT, owner TEXT);
            CREATE TABLE deliveries(request TEXT PRIMARY KEY,key_id INTEGER,at INTEGER);
            CREATE TABLE events(seq INTEGER PRIMARY KEY,request TEXT,operation TEXT,key_id INTEGER,at INTEGER);''')
            db.executemany('INSERT INTO keys VALUES (?, ?, NULL)',[(i,'free') for i in range(capacity)])
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        db.execute('PRAGMA busy_timeout=10000');return db
    def prepare(self,request,now):
        if self.mode=='atomic':raise ValueError('Atomic mode has no prepare operation')
        db=self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT id FROM keys WHERE state='free' ORDER BY id LIMIT 1").fetchone() if now<self.expires else None
            key=row[0] if row else None
            if key is not None and self.mode=='reserved':db.execute("UPDATE keys SET state='held',owner=? WHERE id=?",(request,key))
            db.execute('INSERT INTO events(request,operation,key_id,at) VALUES (?,?,?,?)',(request,'prepare',key,now));db.commit();return key
        finally:db.close()
    def commit(self,request,key,now):
        db=self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            if self.mode=='atomic':
                row=db.execute("SELECT id FROM keys WHERE state='free' ORDER BY id LIMIT 1").fetchone() if now<self.expires else None
                key=row[0] if row else None;allowed=key is not None
            elif self.mode=='reserved':
                allowed=key is not None and now<self.expires and db.execute("SELECT 1 FROM keys WHERE id=? AND state='held' AND owner=?",(key,request)).fetchone() is not None
            else:
                # Intentional TOCTOU control: trust the earlier result without
                # checking current ownership or freshness at actual delivery.
                allowed=key is not None
            if allowed:
                db.execute('INSERT INTO deliveries VALUES (?,?,?)',(request,key,now))
                db.execute("UPDATE keys SET state='used',owner=NULL WHERE id=?",(key,))
            db.execute('INSERT INTO events(request,operation,key_id,at) VALUES (?,?,?,?)',(request,'deliver' if allowed else 'reject',key,now));db.commit();return bool(allowed)
        finally:db.close()
    def abort(self,request,key,now):
        db=self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            if self.mode=='reserved' and key is not None:
                db.execute("UPDATE keys SET state=?,owner=NULL WHERE id=? AND state='held' AND owner=?",('free' if now<self.expires else 'wasted',key,request))
            db.execute('INSERT INTO events(request,operation,key_id,at) VALUES (?,?,?,?)',(request,'abort',key,now));db.commit()
        finally:db.close()
    def snapshot(self):
        with self.connect() as db:
            deliveries=[dict(zip(('request','key_id','at'),row)) for row in db.execute('SELECT * FROM deliveries ORDER BY request')]
            return {'deliveries':deliveries,'held':db.execute("SELECT COUNT(*) FROM keys WHERE state='held'").fetchone()[0],
              'wasted':db.execute("SELECT COUNT(*) FROM keys WHERE state='wasted'").fetchone()[0],
              'events':[dict(zip(('seq','request','operation','key_id','at'),row)) for row in db.execute('SELECT * FROM events ORDER BY seq')]}

def findings(snapshot,capacity,expiry):
    rows=snapshot['deliveries'];ids=[r['key_id'] for r in rows]
    return {'duplicate_key':len(ids)!=len(set(ids)),'over_capacity':len(rows)>capacity,
            'expired_delivery':any(r['at']>=expiry for r in rows)}
