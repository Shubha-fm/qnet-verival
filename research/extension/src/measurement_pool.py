"""Bounded resource refinement driven by measured rates, with assumed controller event budgets.
Identical requests are represented by counts, a symmetry quotient. No measured timeline is invented.
"""
from dataclasses import dataclass,replace,asdict
from collections import deque
from pathlib import Path
import gzip,hashlib,json,subprocess,tempfile,time

@dataclass(frozen=True)
class PoolConfig:
    requests:int
    capacity:int
    mode:str
    expiry_steps:int
    deadline_steps:int

@dataclass(frozen=True)
class PoolState:
    waiting:int
    prepared:int
    delivered:int
    aborted:int
    free:int
    clock:int=0
    stale_delivery:bool=False

NAMES=('I1_capacity','I2_fresh_commit','I3_accounting','I4_termination')

def initial(c):return PoolState(c.requests,0,0,0,c.capacity)
def terminal(s):return s.waiting+s.prepared==0

def successors(s,c):
    if terminal(s):return
    fresh=s.clock<c.expiry_steps;within=s.clock<c.deadline_steps
    def emit(label,**kw):
        return label,replace(s,clock=min(c.deadline_steps,s.clock+1),**kw)
    if within:
        yield emit('Tick')
        if s.waiting and s.free>0 and fresh:
            if c.mode=='atomic':yield emit('AtomicDeliver',waiting=s.waiting-1,delivered=s.delivered+1,free=s.free-1)
            else:yield emit('Prepare',waiting=s.waiting-1,prepared=s.prepared+1,free=s.free-(c.mode=='reserved'))
        if s.prepared and (c.mode=='split' or fresh):
            yield emit('Commit',prepared=s.prepared-1,delivered=s.delivered+1,free=s.free-(c.mode=='split'),stale_delivery=s.stale_delivery or not fresh)
    if s.waiting and (not fresh or not within or s.free<=0):
        yield emit('AbortWaiting',waiting=s.waiting-1,aborted=s.aborted+1)
    if s.prepared and (not fresh or not within or (c.mode=='split' and s.free<=0)):
        yield emit('AbortPrepared',prepared=s.prepared-1,aborted=s.aborted+1,free=s.free+(c.mode=='reserved' and fresh))

def violations(s,c):
    return {name for name,bad in (
      ('I1_capacity',s.free<0 or s.delivered>c.capacity),
      ('I2_fresh_commit',s.stale_delivery),
      ('I3_accounting',s.waiting+s.prepared+s.delivered+s.aborted!=c.requests or min(s.waiting,s.prepared,s.delivered,s.aborted)<0 or (c.mode=='reserved' and s.free+s.prepared+s.delivered>c.capacity))) if bad}

def check(c,export=None):
    start=time.perf_counter();states=[initial(c)];ids={states[0]:0};parent=[None];edges=[]
    for u,s in enumerate(states):
        row=[]
        for label,t in successors(s,c):
            if t not in ids:ids[t]=len(states);states.append(t);parent.append((u,label))
            row.append((ids[t],label))
        edges.append(row or [(u,'TerminalStutter' if terminal(s) else 'DeadlockStutter')])
    bad={}
    for u,s in enumerate(states):
        for p in sorted(violations(s,c)):bad.setdefault(p,u)
    rev=[[] for _ in states];remaining=list(map(len,edges));good={u for u,s in enumerate(states) if terminal(s)};queue=deque(sorted(good))
    for u,row in enumerate(edges):
        for v,_ in row:rev[v].append(u)
    while queue:
        v=queue.popleft()
        for u in rev[v]:
            remaining[u]-=1
            if remaining[u]==0 and u not in good:good.add(u);queue.append(u)
    if 0 not in good:bad['I4_termination']=0
    witnesses={}
    for p,u in bad.items():
        assert p!='I4_termination','Unexpected nontermination; explicit lasso generation required before returning result.'
        final=u;trace=[]
        while parent[u] is not None:
            v,label=parent[u];trace.append({'from':v,'action':label,'to':u});u=v
        witnesses[p]={'steps':list(reversed(trace)),'state':asdict(states[final]),'kind':'shortest_BFS_prefix'}
    if export:
        with Path(export).open('w') as f:
            f.write(f'{len(states)} {sum(map(len,edges))}\n')
            for s in states:f.write(f"{int(terminal(s))} {sum(1<<j for j,p in enumerate(NAMES) if p in violations(s,c))}\n")
            for u,row in enumerate(edges):
                for v,label in row:f.write(f'{u} {v}\n')
    return {'config':asdict(c),'states':len(states),'edges':sum(map(len,edges)),'properties':{p:p not in bad for p in NAMES},'witnesses':witnesses,'seconds':time.perf_counter()-start,'max_delivered':max(s.delivered for s in states),'successful_delivery_reachable':any(s.delivered for s in states)}

if __name__=='__main__':
    for mode in ('atomic','split','reserved'):
        print(mode,check(PoolConfig(2,1,mode,3,12))['properties'])
