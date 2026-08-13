"""Authorization for model-proposed tool calls.

The threat model is the whole design, so it goes first:

    Assume the model is fully compromised by content it retrieved. Assume it
    will emit whatever tool call the injected text asked for, with whatever
    arguments, and will describe it convincingly. The control must hold anyway.

That assumption rules out an entire family of popular mitigations. Classifying
the input, stripping suspicious phrases, instructing the model to ignore
instructions in documents, scoring outputs for "injection likelihood" — each of
these tries to keep a compromised model from *asking*. None of them is a control,
because each fails exactly when it matters, and each fails silently.

What holds instead is that the model's output is a **request, not a decision**.
Authorization is computed from session state established by authentication, and
no input to that computation is reachable from the prompt, the retrieved
documents, or the model's output. The gate is deterministic code. It would
produce the same verdict if the tool call were proposed by an attacker directly,
because from the gate's perspective it always is.

Five rules, in order of how often their absence causes an incident:

1. **Deny by default.** An unrecognised tool is denied, not passed through.
2. **Scopes come from the session.** Nothing the model emits can add one.
3. **Subject-bound arguments must match the session.** A tool call that names a
   tenant, user or account is checked against the authenticated one — this is
   the same control as `../tenant-isolation/`, enforced at the tool boundary
   rather than the retrieval boundary. Both are needed; neither substitutes.
4. **Egress destinations are allowlisted.** Exfiltration does not need a
   privileged tool, only a tool that takes a URL.
5. **Irreversible actions need a confirmation token the model cannot mint.**
   Tokens are issued to a human interaction and bound to the exact call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# Tool -> the scope required to invoke it. A tool absent from this table is
# denied; the table is the allowlist, not a hint to a more permissive default.
TOOL_SCOPES: dict[str, str] = {
    "search_documents": "documents:read",
    "summarize": "documents:read",
    "send_email": "email:send",
    "create_ticket": "tickets:write",
    "delete_documents": "documents:admin",
    "rotate_credentials": "secrets:admin",
    "fetch_url": "net:egress",
}

# Actions whose effect cannot be walked back by re-running the agent.
IRREVERSIBLE: frozenset[str] = frozenset(
    {"send_email", "delete_documents", "rotate_credentials"}
)

# Arguments that name a security principal or boundary. If a tool call carries
# one, it must equal the session's own value.
SUBJECT_BOUND_ARGS: frozenset[str] = frozenset(
    {"tenant_id", "org_id", "customer_id", "user_id", "account_id", "workspace_id"}
)

ALLOWED_EGRESS_HOSTS: frozenset[str] = frozenset(
    {"docs.internal.example", "api.internal.example"}
)


class Verdict(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class Session:
    """Established by authentication. Never influenced by model output."""

    subject: str
    tenant_id: str
    granted_scopes: frozenset[str]
    confirmation_tokens: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ToolCall:
    """What the model asked for. Untrusted, in full."""

    tool: str
    arguments: dict = field(default_factory=dict)
    confirmation_token: str | None = None


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    rule: str
    detail: str

    @property
    def allowed(self) -> bool:
        return self.verdict is Verdict.ALLOW


def _host(url: str) -> str:
    from urllib.parse import urlparse

    return (urlparse(url).hostname or "").lower()


def authorize(session: Session, call: ToolCall) -> Decision:
    """Return a decision. Pure function of (session, call) — no I/O, no model."""

    # 1. Deny by default.
    required = TOOL_SCOPES.get(call.tool)
    if required is None:
        return Decision(
            Verdict.DENY,
            "unknown-tool",
            f"{call.tool!r} is not in the tool allowlist",
        )

    # 2. Scopes come from the session.
    if required not in session.granted_scopes:
        return Decision(
            Verdict.DENY,
            "missing-scope",
            f"{call.tool!r} requires {required!r}; session holds "
            f"{sorted(session.granted_scopes)}",
        )

    # 3. Subject-bound arguments must match the session.
    for arg in SUBJECT_BOUND_ARGS & set(call.arguments):
        value = call.arguments[arg]
        expected = session.tenant_id if arg != "user_id" else session.subject
        if str(value) != expected:
            return Decision(
                Verdict.DENY,
                "subject-mismatch",
                f"{arg}={value!r} does not match the authenticated {expected!r}",
            )

    # 4. Egress destinations are allowlisted.
    for arg in ("url", "endpoint", "callback", "webhook"):
        if arg in call.arguments:
            host = _host(str(call.arguments[arg]))
            if host not in ALLOWED_EGRESS_HOSTS:
                return Decision(
                    Verdict.DENY,
                    "egress-not-allowlisted",
                    f"destination {host or '(unparseable)'!r} is not an allowed egress host",
                )

    # 5. Irreversible actions need a token bound to this exact call.
    if call.tool in IRREVERSIBLE:
        expected = confirmation_token_for(session, call)
        if call.confirmation_token != expected:
            return Decision(
                Verdict.DENY,
                "unconfirmed-irreversible-action",
                f"{call.tool!r} is irreversible and requires a human confirmation "
                "token bound to this call",
            )
        if expected not in session.confirmation_tokens:
            return Decision(
                Verdict.DENY,
                "unissued-confirmation-token",
                "token is well-formed but was never issued to this session",
            )

    return Decision(Verdict.ALLOW, "allowed", f"{call.tool!r} permitted by {required!r}")


def confirmation_token_for(session: Session, call: ToolCall) -> str:
    """Derive the token that a human confirmation of *this exact call* would produce.

    Binding the token to the arguments is what stops the confirm-then-swap
    problem: a user approves "email the report to finance@", the model re-emits
    the call with a different recipient, and an unbound token still validates.
    """
    import hashlib
    import json

    material = json.dumps(
        {
            "subject": session.subject,
            "tenant": session.tenant_id,
            "tool": call.tool,
            "arguments": {k: v for k, v in sorted(call.arguments.items())},
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()[:32]
