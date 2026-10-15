"""Finite-state QKD coordination reference model. Python standard library only.
Synthetic benchmark reference model; no claim of implementation conformance.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, replace, asdict
import argparse, hashlib, json, platform, time
from pathlib import Path

@dataclass(frozen=True)
class Session:
    route: int = -1
    auth: bool = False
    links: tuple[int, ...] = ()  # bit 0 raw, bit 1 EC, bit 2 PA
    ack: int = 0
    bad_ack: bool = False
    confirm: bool = False
    stored: bool = False
    expired: bool = False
    error: bool = False
    steps: int = 0
    status: int = 0  # 0 active, 1 delivered, 2 aborted
    receipt: tuple[bool, ...] = ()
    abort_valid: bool = False
    pending: bool = False
    staged_receipt: tuple[bool, ...] = ()

@dataclass(frozen=True)
class State:
    sessions: tuple[Session, ...]
    consumed: tuple[bool, ...]
    owners: tuple[int, ...] = ()  # reservation owner; -1 means unreserved

@dataclass(frozen=True)
class Config:
    relays: int = 1
    sessions: int = 1
    route_lengths: tuple[int, ...] = ()
    deadline: int = 24  # local event budget, not wall-clock time
    failures: bool = True
    delay: bool = False
    shared_key: bool = False
    mutant: str = 'none'
    max_states: int = 100000
    delivery_mode: str = 'atomic'  # atomic, split, reserved
    mutations: tuple[str, ...] = ()
    target_session: int = -1
    target_hop: int = -1
    target_relay: int = -1

MUTANTS = ('skip_auth', 'skip_ec', 'skip_ack', 'wrong_session_ack',
           'skip_confirm', 'skip_store', 'expired_delivery', 'omit_consume',
           'invalid_abort', 'missing_timeout', 'retry_loop', 'abort_label')
PROPERTIES = ('P1_auth', 'P2_postprocess', 'P3_agreement', 'P4_confirm',
              'P5_fresh_at_delivery', 'P6_delivery_contract', 'P7_valid_abort',
              'P8_termination', 'P9_single_use')

def has(c, name, i=None):
    return (name == c.mutant or name in c.mutations) and (i is None or c.target_session < 0 or c.target_session == i)

class StateLimit(RuntimeError):
    def __init__(self, states, expanded, seconds):
        self.states, self.expanded, self.seconds = states, expanded, seconds
        super().__init__(f'state cap reached at {states} states; no verdict')

def initial(c):
    keys = 1 if c.shared_key else c.sessions
    return State(tuple(Session() for _ in range(c.sessions)), (False,) * keys, (-1,) * keys)

def lengths(c):
    return c.route_lengths or (c.relays + 1,)

def successors(s, c):
    for i, q in enumerate(s.sessions):
        if q.status:
            continue
        k = 0 if c.shared_key else i
        def emit(label, changes=None, consumed=None, advance=True, owners=None):
            changes = dict(changes or {})
            if advance:
                changes['steps'] = min(c.deadline, q.steps + 1)
            arr = list(s.sessions)
            arr[i] = replace(q, **changes)
            return f's{i}:{label}', State(tuple(arr), s.consumed if consumed is None else consumed, s.owners if owners is None else owners)
        timed_out = q.steps >= c.deadline
        valid_abort = q.error or q.expired or timed_out or s.consumed[k]
        if valid_abort:
            if not (has(c, 'missing_timeout', i) and timed_out and not (q.error or q.expired or s.consumed[k])):
                yield emit('AbortWithDiagnosticLabel' if has(c, 'abort_label', i) else 'Abort', {'status': 2, 'abort_valid': True}, owners=tuple(-1 if j == k and owner == i else owner for j, owner in enumerate(s.owners)))
        if has(c, 'invalid_abort', i) and not valid_abort:
            yield emit('AbortWithoutCause', {'status': 2})
        if q.error or timed_out:
            continue
        if q.pending:
            # Split delivery commits the earlier snapshot, exposing a TOCTOU race.
            # Reserved mode validates ownership and candidate freshness at commit.
            allowed = c.delivery_mode == 'split' or (s.owners[k] == i and not s.consumed[k] and not q.expired)
            if allowed:
                used = list(s.consumed)
                if not has(c, 'omit_consume', i): used[k] = True
                owners = list(s.owners); owners[k] = -1
                fresh_now = not q.expired and not s.consumed[k]
                receipt_now = q.staged_receipt[:4] + (fresh_now, q.staged_receipt[5] and fresh_now)
                yield emit('CommitDelivery', {'status': 1, 'pending': False, 'receipt': receipt_now}, tuple(used), owners=tuple(owners))
            # A staged request may fail/expire before commit. No unrelated service actions run here.
            if not q.expired:
                yield emit('ExpireAfterPrepare', {'expired': True})
            continue
        if c.failures:
            yield emit('LinkFailure', {'error': True})
        if c.delay:
            yield emit('Delay')
        if q.route < 0:
            for rid, hops in enumerate(lengths(c)):
                yield emit(f'SelectRoute({rid})', {'route': rid, 'links': (0,) * hops})
            continue
        if not q.auth:
            yield emit('Authenticate', {'auth': True})
        if q.auth or has(c, 'skip_auth', i):
            for h, bits in enumerate(q.links):
                upd = None
                if not bits & 1:
                    upd = bits | 1
                    label = 'Raw'
                elif not bits & 2:
                    upd = bits | 2
                    label = 'EC'
                elif not bits & 4:
                    upd = bits | 4
                    label = 'PA'
                if upd is not None:
                    links = list(q.links); links[h] = upd
                    yield emit(f'{label}({h})', {'links': tuple(links)})
                if has(c, 'skip_ec', i) and bits == 1 and c.target_hop in (-1, h):
                    links = list(q.links); links[h] = 5
                    yield emit(f'PAWithoutEC({h})', {'links': tuple(links)})
        ready = bool(q.links) and all(v == 7 for v in q.links)
        relay_count = len(q.links) - 1
        full_ack = (1 << relay_count) - 1
        if ready:
            for r in range(relay_count):
                if not q.ack & (1 << r):
                    yield emit(f'Ack({r})', {'ack': q.ack | (1 << r)})
                    if has(c, 'wrong_session_ack', i) and c.target_relay in (-1, r):
                        yield emit(f'ForeignAck({r})', {'ack': q.ack | (1 << r), 'bad_ack': True})
        agree = ready and q.ack == full_ack and not q.bad_ack
        # The mutant accepts acknowledged bits without session identity validation.
        accepted = ready and q.ack == full_ack
        if (accepted or (has(c, 'skip_ack', i) and ready)) and not q.confirm:
            yield emit('Confirm', {'confirm': True})
        if (q.confirm or (has(c, 'skip_confirm', i) and accepted)) and not q.stored:
            yield emit('Store', {'stored': True})
        if q.stored and not q.expired:
            yield emit('Expire', {'expired': True})
        if has(c, 'retry_loop', i) and q.stored:
            yield emit('RetryWithoutBudget', advance=False)
        can_deliver = (q.stored or (has(c, 'skip_store', i) and q.confirm))
        if q.expired and not has(c, 'expired_delivery', i):
            can_deliver = False
        if s.consumed[k]:
            can_deliver = False
        if c.delivery_mode == 'reserved' and s.owners[k] not in (-1, i):
            can_deliver = False
        if can_deliver:
            fresh = not q.expired and not s.consumed[k]
            receipt = (q.auth, all((v & 4 == 0) or (v & 2 != 0) for v in q.links),
                       agree, q.confirm, fresh,
                       q.auth and ready and agree and q.confirm and q.stored and fresh)
            if c.delivery_mode == 'atomic':
                used = list(s.consumed)
                if not has(c, 'omit_consume', i): used[k] = True
                yield emit('Deliver', {'status': 1, 'receipt': receipt}, tuple(used))
            else:
                owners = list(s.owners)
                if c.delivery_mode == 'reserved': owners[k] = i
                yield emit('PrepareDelivery', {'pending': True, 'staged_receipt': receipt}, owners=tuple(owners))
    # Totalization is explicit and does not count as an operational action.

def violations(s, c):
    out = set()
    delivered_per_key = [0] * len(s.consumed)
    for i, q in enumerate(s.sessions):
        if any(v & 4 and not v & 2 for v in q.links):
            out.add('P2_postprocess')
        if q.status == 1:
            for prop, flag in zip(PROPERTIES[:6], q.receipt):
                if not flag:
                    out.add(prop)
            k = 0 if c.shared_key else i
            delivered_per_key[k] += 1
            if not s.consumed[k]:
                out.add('P9_single_use')
        if q.status == 2:
            k = 0 if c.shared_key else i
            if not q.abort_valid:
                out.add('P7_valid_abort')
    if any(n > 1 for n in delivered_per_key):
        out.add('P9_single_use')
    return out

def terminal(s):
    return all(q.status != 0 for q in s.sessions)

def explore(c, graph_path=None):
    start = time.perf_counter()
    states = [initial(c)]; ids = {states[0]: 0}; parent = [None]; graph = []
    for index, s in enumerate(states):
        edges = []
        for label, t in successors(s, c):
            if t not in ids:
                if len(states) >= c.max_states:
                    raise StateLimit(len(states), index, time.perf_counter()-start)
                ids[t] = len(states); states.append(t); parent.append((index, label))
            edges.append((ids[t], label))
        if not edges:
            edges = [(index, 'TerminalStutter' if terminal(s) else 'DeadlockStutter')]
        graph.append(edges)
    n = len(states)
    reverse = [[] for _ in states]
    remaining = [len(g) for g in graph]
    for u, edges in enumerate(graph):
        for v, _ in edges:
            reverse[v].append(u)
    # Least fixed point AF terminal: no fairness restriction on paths.
    good = {i for i, s in enumerate(states) if terminal(s)}
    queue = deque(sorted(good))
    while queue:
        v = queue.popleft()
        for u in reverse[v]:
            remaining[u] -= 1
            if remaining[u] == 0 and u not in good:
                good.add(u); queue.append(u)
    bad = {}
    for i, s in enumerate(states):
        for p in sorted(violations(s, c)):
            bad.setdefault(p, i)
    if 0 not in good:
        bad['P8_termination'] = 0
    def trace_to(v):
        path = []
        while parent[v] is not None:
            u, label = parent[v]; path.append({'from': u, 'action': label, 'to': v}); v = u
        return list(reversed(path))
    witnesses = {}
    for p, v in sorted(bad.items()):
        if p != 'P8_termination':
            witnesses[p] = {'kind': 'shortest_BFS_prefix', 'steps': trace_to(v), 'state': asdict(states[v])}
    if 'P8_termination' in bad:
        walk = []; seen = {}; u = 0
        while u not in seen:
            seen[u] = len(walk)
            v, label = next((v, a) for v, a in graph[u] if v not in good)
            walk.append({'from': u, 'action': label, 'to': v}); u = v
        witnesses['P8_termination'] = {'kind': 'lasso_not_necessarily_shortest',
                                     'loop_start': seen[u], 'steps': walk}
    core_seconds = time.perf_counter() - start
    if graph_path is not None:
        export_graph(states, graph, c, graph_path)
    return {'config': asdict(c), 'states': n, 'transitions': sum(map(len, graph)),
            'operational_deadlocks': sum(not terminal(s) and graph[i][0][1] == 'DeadlockStutter' for i, s in enumerate(states)),
            'states_with_delivery': sum(any(q.status == 1 for q in s.sessions) for s in states),
            'states_all_delivered': sum(all(q.status == 1 for q in s.sessions) for s in states),
            'seconds': round(core_seconds, 6),
            'properties': {p: p not in bad for p in PROPERTIES}, 'witnesses': witnesses}

def export_graph(states, graph, c, path):
    """Portable labelled graph for independent C++ checking, not an independent model."""
    with open(path, 'w') as f:
        f.write(f'{len(states)} {sum(map(len,graph))}\n')
        for s in states:
            mask = sum(1 << j for j,p in enumerate(PROPERTIES) if p in violations(s,c))
            f.write(f'{int(terminal(s))} {mask}\n')
        for u, edges in enumerate(graph):
            for v, _ in edges: f.write(f'{u} {v}\n')

if __name__ == '__main__':
    print(explore(Config()))
