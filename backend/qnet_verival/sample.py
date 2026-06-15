from __future__ import annotations

from .models import Channel, Node, Operation, OperationType, ProtocolModel


def metropolitan_qkd_model() -> ProtocolModel:
    nodes = [
        Node(id="alice", label="Alice", role="end_user"),
        Node(id="relay_1", label="Trusted Relay 1", role="trusted_relay"),
        Node(id="relay_2", label="Trusted Relay 2", role="trusted_relay"),
        Node(id="bob", label="Bob", role="end_user"),
        Node(id="auth", label="Authentication Service", role="service"),
        Node(id="kms", label="Key Management Server", role="service"),
    ]
    channels = [
        Channel(source="alice", target="relay_1", kind="quantum"),
        Channel(source="relay_1", target="relay_2", kind="quantum"),
        Channel(source="relay_2", target="bob", kind="quantum"),
        Channel(source="alice", target="auth", kind="classical"),
        Channel(source="bob", target="auth", kind="classical"),
        Channel(source="relay_1", target="auth", kind="classical"),
        Channel(source="relay_2", target="auth", kind="classical"),
        Channel(source="auth", target="kms", kind="classical"),
        Channel(source="kms", target="bob", kind="classical"),
    ]
    operations = [
        Operation(id="auth_init", label="Authenticate session", kind=OperationType.authentication, actor="auth", sets=["authenticated"]),
        Operation(id="qsend_12", label="Transmit quantum states A-R1", kind=OperationType.quantum, actor="alice", requires=["authenticated"], sets=["q12_sent"]),
        Operation(id="sift_12", label="Basis reconciliation A-R1", kind=OperationType.classical, actor="relay_1", requires=["q12_sent", "authenticated"], sets=["sift12_done"]),
        Operation(id="qber_12", label="Estimate error rate A-R1", kind=OperationType.post_processing, actor="relay_1", requires=["sift12_done"], sets=["qber12_checked"]),
        Operation(id="pa_12", label="Privacy amplification A-R1", kind=OperationType.post_processing, actor="relay_1", requires=["qber12_checked"], sets=["pa12_done"]),
        Operation(id="relay_23", label="Forward key R1-R2", kind=OperationType.relay, actor="relay_1", requires=["pa12_done", "authenticated"], sets=["relay23_done"]),
        Operation(id="relay_34", label="Forward key R2-B", kind=OperationType.relay, actor="relay_2", requires=["relay23_done", "authenticated"], sets=["relay34_done"]),
        Operation(id="kms_store", label="Store confirmed key material", kind=OperationType.key_management, actor="kms", requires=["relay34_done"], sets=["key_stored"]),
        Operation(id="confirm", label="Confirm final key", kind=OperationType.confirmation, actor="bob", requires=["key_stored", "relay34_done"], sets=["key_confirmed"]),
        Operation(id="finish", label="Finish protocol", kind=OperationType.terminal, actor="bob", requires=["key_confirmed"], sets=["finished"]),
    ]
    return ProtocolModel(
        nodes=nodes,
        channels=channels,
        operations=operations,
        initial_flags={"authenticated": False},
        terminal_flags=["finished"],
    )
