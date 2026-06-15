from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .models import FaultResult, Finding, MutationResult, Operation, ProtocolModel, ValidationSummary, VerificationResult


@dataclass(frozen=True)
class Property:
    id: str
    category: str
    description: str
    trigger: str
    required: str


SAFETY_PROPERTIES: List[Property] = [
    Property("P1", "Authentication ordering", "Quantum transmission requires authentication", "q12_sent", "authenticated"),
    Property("P2", "Basis reconciliation", "Error estimation requires basis reconciliation", "qber12_checked", "sift12_done"),
    Property("P3", "Privacy amplification", "Privacy amplification requires error estimation", "pa12_done", "qber12_checked"),
    Property("P4", "Relay integrity", "Relay forwarding requires privacy amplification", "relay23_done", "pa12_done"),
    Property("P5", "Key-management ordering", "Key storage requires relay delivery", "key_stored", "relay34_done"),
    Property("P6", "Key confirmation", "Protocol completion requires final key confirmation", "finished", "key_confirmed"),
]

FAULTS = {
    "F1": ("Unauthenticated quantum transmission", "qsend_12", "authenticated"),
    "F2": ("QBER before basis reconciliation", "qber_12", "sift12_done"),
    "F3": ("Privacy amplification before error estimation", "pa_12", "qber12_checked"),
    "F4": ("Premature relay forwarding", "relay_23", "pa12_done"),
    "F5": ("Key storage before relay delivery", "kms_store", "relay34_done"),
    "F6": ("Finish before key confirmation", "finish", "key_confirmed"),
}

MUTATIONS = {
    "M1": ("Guard weakening in quantum transmission", "qsend_12", "authenticated"),
    "M2": ("Guard weakening in error estimation", "qber_12", "sift12_done"),
    "M3": ("Guard weakening in privacy amplification", "pa_12", "qber12_checked"),
    "M4": ("Guard weakening in relay forwarding", "relay_23", "pa12_done"),
    "M5": ("Guard weakening in key storage", "kms_store", "relay34_done"),
    "M6": ("Guard weakening in final completion", "finish", "key_confirmed"),
}


def _initial_state(model: ProtocolModel) -> Dict[str, bool]:
    flags: Dict[str, bool] = {k: bool(v) for k, v in model.initial_flags.items()}
    for op in model.operations:
        for flag in op.requires + op.sets:
            flags.setdefault(flag, False)
    return flags


def _enabled(op: Operation, flags: Dict[str, bool]) -> bool:
    return all(flags.get(req, False) for req in op.requires) and not all(flags.get(s, False) for s in op.sets)


def _apply(op: Operation, flags: Dict[str, bool]) -> Dict[str, bool]:
    nxt = dict(flags)
    for flag in op.sets:
        nxt[flag] = True
    return nxt


def _state_key(flags: Dict[str, bool]) -> Tuple[Tuple[str, bool], ...]:
    return tuple(sorted(flags.items()))


def _explore(model: ProtocolModel) -> Tuple[List[Tuple[Dict[str, bool], List[str]]], int]:
    start = _initial_state(model)
    queue: List[Tuple[Dict[str, bool], List[str]]] = [(start, [])]
    visited: Set[Tuple[Tuple[str, bool], ...]] = set()
    states: List[Tuple[Dict[str, bool], List[str]]] = []
    transitions = 0
    while queue:
        flags, trace = queue.pop(0)
        key = _state_key(flags)
        if key in visited:
            continue
        visited.add(key)
        states.append((flags, trace))
        for op in model.operations:
            if _enabled(op, flags):
                transitions += 1
                queue.append((_apply(op, flags), trace + [op.id]))
    return states, transitions


def verify(model: ProtocolModel) -> VerificationResult:
    states, transition_count = _explore(model)
    findings: List[Finding] = []
    for prop in SAFETY_PROPERTIES:
        bad = next(((s, t) for s, t in states if s.get(prop.trigger, False) and not s.get(prop.required, False)), None)
        if bad:
            findings.append(Finding(
                property_id=prop.id,
                status="violated",
                category=prop.category,
                message=f"{prop.description} violated: {prop.trigger} is true while {prop.required} is false.",
                trace=bad[1],
            ))
        else:
            findings.append(Finding(
                property_id=prop.id,
                status="satisfied",
                category=prop.category,
                message=prop.description,
                trace=[],
            ))

    terminal_ok = any(all(s.get(flag, False) for flag in model.terminal_flags) for s, _ in states)
    deadlocks = []
    for s, t in states:
        terminal = all(s.get(flag, False) for flag in model.terminal_flags)
        if not terminal and not any(_enabled(op, s) for op in model.operations):
            deadlocks.append((s, t))

    findings.append(Finding(
        property_id="L1",
        status="satisfied" if terminal_ok else "violated",
        category="Termination",
        message="A valid execution eventually reaches protocol completion." if terminal_ok else "No reachable completion state was found.",
        trace=[] if terminal_ok else (states[-1][1] if states else []),
    ))
    findings.append(Finding(
        property_id="L2",
        status="satisfied" if not deadlocks else "violated",
        category="Deadlock freedom",
        message="No non-terminal deadlock state was found." if not deadlocks else "A non-terminal deadlock state was found.",
        trace=[] if not deadlocks else deadlocks[0][1],
    ))

    safety_satisfied = sum(1 for f in findings if f.property_id.startswith("P") and f.status == "satisfied")
    liveness_satisfied = sum(1 for f in findings if f.property_id.startswith("L") and f.status == "satisfied")
    verdict = "verified" if all(f.status == "satisfied" for f in findings) else "violated"
    return VerificationResult(
        model_name=model.name,
        states_explored=len(states),
        transitions_explored=transition_count,
        safety_satisfied=safety_satisfied,
        liveness_satisfied=liveness_satisfied,
        findings=findings,
        verdict=verdict,
    )


def _remove_requirement(model: ProtocolModel, operation_id: str, requirement: str) -> ProtocolModel:
    mutant = deepcopy(model)
    for op in mutant.operations:
        if op.id == operation_id and requirement in op.requires:
            op.requires = [r for r in op.requires if r != requirement]
    return mutant


def inject_fault(model: ProtocolModel, fault_id: str) -> FaultResult:
    if fault_id not in FAULTS:
        raise ValueError(f"Unknown fault id: {fault_id}")
    description, op_id, req = FAULTS[fault_id]
    faulty = _remove_requirement(model, op_id, req)
    result = verify(faulty)
    violated = [f.property_id for f in result.findings if f.status == "violated"]
    trace = next((f.trace for f in result.findings if f.status == "violated" and f.trace), [])
    diagnosis = "Detected and localized by property violation." if violated else "Not detected. Property set should be refined."
    return FaultResult(fault_id=fault_id, description=description, detected=bool(violated), violated_properties=violated, diagnosis=diagnosis, trace=trace)


def mutate(model: ProtocolModel, mutation_id: str) -> MutationResult:
    if mutation_id not in MUTATIONS:
        raise ValueError(f"Unknown mutation id: {mutation_id}")
    description, op_id, req = MUTATIONS[mutation_id]
    mutated = _remove_requirement(model, op_id, req)
    result = verify(mutated)
    killed_by = [f.property_id for f in result.findings if f.status == "violated"]
    trace = next((f.trace for f in result.findings if f.status == "violated" and f.trace), [])
    return MutationResult(mutation_id=mutation_id, description=description, killed=bool(killed_by), killed_by=killed_by, trace=trace)


def validate(model: ProtocolModel) -> ValidationSummary:
    fault_results = [inject_fault(model, fid) for fid in FAULTS]
    mutation_results = [mutate(model, mid) for mid in MUTATIONS]
    detected_faults = sum(1 for r in fault_results if r.detected)
    killed_mutants = sum(1 for r in mutation_results if r.killed)
    return ValidationSummary(
        total_faults=len(fault_results),
        detected_faults=detected_faults,
        fault_detection_rate=round(detected_faults / len(fault_results), 4) if fault_results else 0.0,
        total_mutants=len(mutation_results),
        killed_mutants=killed_mutants,
        mutation_score=round(killed_mutants / len(mutation_results), 4) if mutation_results else 0.0,
        fault_results=fault_results,
        mutation_results=mutation_results,
    )
