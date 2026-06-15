from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OperationType(str, Enum):
    authentication = "authentication"
    quantum = "quantum"
    classical = "classical"
    relay = "relay"
    post_processing = "post_processing"
    key_management = "key_management"
    confirmation = "confirmation"
    terminal = "terminal"


class Node(BaseModel):
    id: str
    label: str
    role: str


class Channel(BaseModel):
    source: str
    target: str
    kind: str = Field(pattern="^(quantum|classical)$")


class Operation(BaseModel):
    id: str
    label: str
    kind: OperationType
    actor: str
    requires: List[str] = Field(default_factory=list)
    sets: List[str] = Field(default_factory=list)


class ProtocolModel(BaseModel):
    name: str = "Metropolitan Multi-Hop QKD"
    nodes: List[Node]
    channels: List[Channel]
    operations: List[Operation]
    initial_flags: Dict[str, bool] = Field(default_factory=dict)
    terminal_flags: List[str] = Field(default_factory=list)


class FaultRequest(BaseModel):
    fault_id: str


class MutationRequest(BaseModel):
    mutation_id: str


class Finding(BaseModel):
    property_id: str
    status: str
    category: str
    message: str
    trace: List[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    model_name: str
    states_explored: int
    transitions_explored: int
    safety_satisfied: int
    liveness_satisfied: int
    findings: List[Finding]
    verdict: str


class FaultResult(BaseModel):
    fault_id: str
    description: str
    detected: bool
    violated_properties: List[str]
    diagnosis: str
    trace: List[str]


class MutationResult(BaseModel):
    mutation_id: str
    description: str
    killed: bool
    killed_by: List[str]
    trace: List[str]


class ValidationSummary(BaseModel):
    total_faults: int
    detected_faults: int
    fault_detection_rate: float
    total_mutants: int
    killed_mutants: int
    mutation_score: float
    fault_results: List[FaultResult]
    mutation_results: List[MutationResult]
