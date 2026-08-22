# The OWASP Agentic Skills Top 10, mapped to this repo

AI agents do real work through **skills** — the packaged instructions and tool
bindings that sit between the model and the actions it takes. That layer is now
its own attack surface, and OWASP has named it: the
[**Agentic Skills Top 10**](https://owasp.org/www-project-agentic-skills-top-10/)
(AST10, v1.0 2026 Edition, CC-BY-SA, in public review). Its framing is worth
keeping: *MCP is how the model talks to tools; AST10 is what those tools actually
do.* It sits below the [OWASP LLM Top 10](https://genai.owasp.org/) (model-level
risks) and covers the skill deployment and execution layer.

This repo's AI-security work predates the list but lines up with it, because both
start from the same assumption — treat the model as already compromised and
constrain what its skills can reach. The map below is honest about where the repo
demonstrates a control and where the risk is a principle to hold, not a solved
problem.

---

## The ten, and where the repo meets them

| ID | Risk | How this repo addresses it |
|---|---|---|
| **AST01** | Malicious Skills | Partly — a skill is code, so the repo's stance is that skills get read and reviewed like code, not trusted by name. Runtime malice is not statically solvable. |
| **AST02** | Supply Chain Compromise | The repo's [dependency discipline](without-a-commercial-platform.md) — SHA-pinned actions, Dependabot, an SBOM step — is the same defence a skill's dependencies need. |
| **AST03** | Over-Privileged Skills | The [`ai-security/`](../ai-security/) **tool-authorization gate**: a skill is allowed only the actions it declares, and a tool call outside that set is refused. |
| **AST04** | Insecure Metadata | Governance-as-code — a control the repo already applies to itself in [control mapping](control-mapping.md): declared, named, and checked, not implicit. |
| **AST05** | Untrusted External Instructions | The **[prompt-injection regression corpus](../ai-security/prompt-injection/)** — the repo tests exactly this: injected instructions attempting to redirect the agent, asserted against on every change. |
| **AST06** | Weak Isolation | The **[tenant-isolation](../ai-security/tenant-isolation/)** work — an embedding store proven to keep one tenant's data out of another's reach is the same isolation a skill needs from its neighbours. |
| **AST07** | Update Drift | Pinning — the reason the repo pins action SHAs rather than tags is exactly AST07: an unpinned reference silently changes what runs. |
| **AST08** | Poor Scanning | The repo's whole thesis — evidence is *scanned and gated, not asserted*. A skill set is one more thing to scan; auditing skills as code is the answer AST08 asks for. |
| **AST09** | No Governance | Declared controls with owners and versions, diffed in CI — the [control-mapping](control-mapping.md) pattern applied to skills. |
| **AST10** | Cross-Platform Reuse | A principle to watch: the same skill copied across Claude Code, Cursor, and VS Code multiplies one weakness. Dedupe and review by identity, not by copy. |

## What to take from it

The through-line is the one the rest of this repo keeps making: **a skill is code
with permissions, so it earns the same treatment as any other code** — reviewed,
its dependencies pinned, its privileges scoped to what it declares, its metadata
and owner explicit, and its behaviour tested against injected instructions. AST10
is useful because it gives that instinct a checklist and a shared vocabulary.

Three of these are statically checkable from a skill's manifest — AST03
(privilege), AST04 (metadata), and AST07 (pinning) — which means they belong in a
scanner, not a review meeting. That is the point of AST08: the risks you can
check by reading the manifest should be checked automatically, every time.

---

*AST10 is a draft in public review; treat the IDs and severities as current-as-of
v1.0 2026 and verify against the [project page](https://owasp.org/www-project-agentic-skills-top-10/)
before quoting them. See [`staying-current.md`](staying-current.md) for why
tracking this kind of moving standard is itself a control.*
