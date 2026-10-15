"""Deterministic synthetic design; IDs bind canonical configurations, not outcome labels."""
from dataclasses import asdict
from itertools import combinations, product
import hashlib,json
from model import Config,MUTANTS

def design():
    cases={}
    def add(suite,tag,c):
        obj=asdict(c); canonical=json.dumps(obj,sort_keys=True,separators=(',',':'))
        cid=hashlib.sha256(canonical.encode()).hexdigest()[:16]
        if cid in cases:
            cases[cid]['memberships'].append(suite+':'+tag)
        else: cases[cid]={'case_id':cid,'suite':suite,'tag':tag,'memberships':[suite+':'+tag],'config':obj}
    for r,f,d,regime in product(range(1,7),(False,True),(False,True),('short','exact','slack')):
        minimum=4*(r+1)+4 # select,auth,3H,r acks,confirm,store,deliver
        budget={'short':max(3,minimum-3),'exact':minimum,'slack':minimum+4}[regime]
        add('structural',f'r{r}_{regime}_f{int(f)}_d{int(d)}',Config(relays=r,failures=f,delay=d,deadline=budget,max_states=100000))
    for n,r,f,shared,mode,regime in product((2,3),(0,1),(False,True),(False,True),('atomic','split','reserved'),('short','slack')):
        if n==3 and r==1:continue
        minimum=4*(r+1)+4+(mode!='atomic')
        budget=max(3,minimum-3) if regime=='short' else minimum+3
        add('concurrency',f'n{n}_r{r}_{mode}_{regime}_shared{int(shared)}_f{int(f)}',Config(relays=r,sessions=n,failures=f,shared_key=shared,delivery_mode=mode,deadline=budget,max_states=60000))
    for r,f,d,regime,m in product((1,2,3),(False,True),(False,True),('short','slack'),MUTANTS):
        minimum=4*(r+1)+4
        budget=minimum-3 if regime=='short' else minimum+4
        add('faults',f'{m}_r{r}_{regime}_f{int(f)}_d{int(d)}',Config(relays=r,failures=f,delay=d,deadline=budget,mutant=m,max_states=60000))
    # Location-specific instances, distinct from different fault classes.
    for n,r in ((1,2),(2,0),(2,1)):
        for session in range(n):
            for m in ('skip_auth','skip_confirm','omit_consume'):
                add('localized',f'{m}_n{n}_r{r}_s{session}',Config(relays=r,sessions=n,shared_key=n>1,deadline=4*(r+1)+7,mutant=m,target_session=session,max_states=60000))
    for h in range(4):
        add('localized',f'skip_ec_h{h}',Config(relays=3,deadline=23,mutant='skip_ec',target_hop=h))
    for relay in range(3):
        add('localized',f'foreign_ack_r{relay}',Config(relays=3,deadline=23,mutant='wrong_session_ack',target_relay=relay))
    # A selected higher-order set, not all combinations of all mutations.
    ops=('skip_auth','skip_ec','skip_ack','skip_confirm','expired_delivery','omit_consume','invalid_abort','retry_loop')
    for pair in combinations(ops,2):
        for r in (1,2):
            add('combined','+'.join(pair)+f'_r{r}',Config(relays=r,deadline=4*(r+1)+7,mutations=pair,max_states=60000))
    # Route alternatives are hop-count alternatives, not measured physical topologies.
    for routes,d,f in product(((1,2),(2,3),(1,3,4)),(False,True),(False,True)):
        add('routes',str(routes)+f'_d{int(d)}_f{int(f)}',Config(route_lengths=routes,deadline=4*max(routes)+7,delay=d,failures=f,max_states=100000))
    return list(cases.values())

if __name__=='__main__':
 from collections import Counter
 cases=design();print(len(cases),Counter(c['suite'] for c in cases))
