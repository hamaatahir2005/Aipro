"""Real-execution boundary. No authorized broker implementation is installed."""
from dataclasses import dataclass
from typing import Protocol
from .trading import Rejected
@dataclass(frozen=True)
class ExecutionAuthorization:
    authenticated:bool=False
    explicit_consent:bool=False
    official_integration_verified:bool=False
    region_approved:bool=False
    financial_limits_configured:bool=False
    audit_ready:bool=False
    emergency_stopped:bool=True
class Broker(Protocol):
    name:str
    async def execute(self,order:dict)->dict: ...
class RealExecutionGate:
    def __init__(self,broker:Broker):self.broker=broker
    async def execute(self,order,authorization:ExecutionAuthorization):
        checks=(authorization.authenticated,authorization.explicit_consent,authorization.official_integration_verified,authorization.region_approved,authorization.financial_limits_configured,authorization.audit_ready)
        if not all(checks) or authorization.emergency_stopped:raise Rejected('Real execution prerequisites not satisfied')
        # A verified adapter must independently validate authorization and deterministic risk.
        return await self.broker.execute(order)
