# KubeMind

**Kubernetes Intelligence for Humans.**

KubeMind is an AI operations intelligence platform that turns Kubernetes from a specialized engineering system into an accessible platform anyone in an organization can query in plain language. Instead of reading dashboards or running `kubectl`, a CEO, manager, or developer asks a question and gets an evidence-backed answer with recommended actions.

> 🚧 **Status — under active development (pre-alpha).** The core loop works end-to-end against a real cluster — executive dashboard, AI incident investigation, deployment & architecture discovery — but APIs, data models, and UX are still evolving. **Not production-ready.** Expect breaking changes; see the [Roadmap](#roadmap) below.

---

## Goals

Make Kubernetes **legible to the whole organization**, not just platform engineers — so the people who depend on production (executives, product, support, on-call developers) can understand what's happening and act on it without paging a specialist for every question.

Concretely, KubeMind aims to:

- **Translate Kubernetes into plain language.** Ask "Is production healthy?" or "Why is the API slow?" and get an evidence-backed answer in business terms.
- **Compress incident investigation.** An AI agent investigates across Prometheus, Kubernetes, deployments, and logs, then proposes a root cause with **cited evidence** and a **confidence score** — minutes instead of hours.
- **Surface risk before it breaks.** Health scores, change tracking, and blast-radius analysis reveal what's risky *before* an incident.
- **Keep humans in control.** The agent proposes; a human reviews and confirms. Nothing destructive runs automatically, and every action is audited.

---


## Features (MVP)

| Module | What it does |
|---|---|
| **Executive Dashboard** | Production health score, active incidents, warnings, recent deployments, top-risk services — aggregated from Prometheus + Kubernetes. |
| **AI Incident Investigator** | Ask "Why is the API slow?" in natural language. A LangGraph agent decomposes the question, calls k8s/Prometheus tools, evaluates evidence, and returns a root cause + proposed action with confidence. |
| **Deployment Intelligence** | Sync and track deployments and ConfigMap/Secret changes from Kubernetes. Answer "what changed today?" |
| **Architecture Discovery** | Discover services and dependencies from Kubernetes env vars. Compute blast radius — "if `payment-api` goes down, what fails?" |

**Safety:** read-only by default. Every mutating action requires explicit confirmation, shows blast radius + rollback plan, and is recorded in an append-only audit log.

---

## Roadmap

### ✅ Working (MVP)
- [x] **Auth & multi-tenant cluster CRUD** — register/login, org-scoped clusters
- [x] **Executive dashboard** — health score, active warnings, recent changes, top-risk services, with graceful degradation when an integration is down
- [x] **AI incident investigator** — LangGraph agent (plan → tools → evaluate → respond) returning root cause + action + confidence
- [x] **Deployment intelligence** — sync deployments + ConfigMap/Secret changes from Kubernetes
- [x] **Architecture discovery & blast radius** — derive services & dependencies from k8s env vars

### 🚧 In progress
- [ ] **ArgoCD & Grafana integrations** — REST clients scaffolded, full implementation pending
- [ ] **Mutating actions** — currently read-only; confirmation, dry-run, and rollback flows are designed ([`docs/safety.md`](docs/safety.md)) but not yet wired to live mutations
- [ ] **Cluster connection UI** — today clusters are connected via the `/docs` Swagger UI or `curl`

### 📋 Planned
- **Phase 2:** Elasticsearch, Loki, GitHub/GitLab integrations
- **Phase 3:** Slack, Teams, Jira, Sentry notifications & workflows
- Hardening: full test coverage, rate limiting, RBAC, production Helm deployment

---

## License

MIT. See [`LICENSE`](LICENSE).
