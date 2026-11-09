"""Refund policy: who may refund how much. Enforced in code, never by the model."""
import os

# Maximum single refund per role, in minor units (simplified: same for all currencies).
ROLE_LIMITS = {
    "viewer": 0,
    "support_agent": 50_000,
    "team_lead": 200_000,
    "finance_manager": 1_000_000,
}
DEFAULT_ROLE = "viewer"


def current_role() -> str:
    """The caller's role is fixed by whoever launches the server, never by tool arguments.

    Unknown or missing roles fall back to the least-privileged role (deny by default).
    """
    role = os.environ.get("PAYMENTS_OPS_ROLE", DEFAULT_ROLE)
    return role if role in ROLE_LIMITS else DEFAULT_ROLE


def refund_limit(role: str | None = None) -> int:
    return ROLE_LIMITS[role or current_role()]