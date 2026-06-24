"""Integration clients for external systems (k8s, Prometheus, ArgoCD, Grafana).

Each client: async, typed methods, caching, rate limiting, circuit breaker,
retry with exponential backoff. See docs/architecture.md §2.4 and
docs/safety.md §10.
"""
