# Operations

Install `orbit-core`, `orbit-metrics`, `orbit-auth`, and this adapter. Register
`PrometheusPlugin` on the application to contribute `GET /metrics`. The plugin refreshes Core's
runtime diagnostics for each scrape and returns UTF-8 Prometheus text with the exposition content
type. No endpoint is installed unless the application registers the plugin.

## Protecting the scrape route

The route requires `orbit.metrics.read` by default. Core stores route roles but does not enforce
them itself. Configure `ASGIApplication` with an authenticator and `RoleAuthorizer` (or another
compatible authorizer), then grant the role only to the scrape identity. Without an ASGI
authorizer, route role metadata alone is not an access-control boundary. Restrict ingress to the
monitoring network as defense in depth.

`PrometheusPlugin(roles=frozenset())` explicitly creates a route with no required roles. Use that
only when an independently enforced network boundary makes the endpoint appropriately private.
Do not expose internal diagnostic counters to the public internet by accident.

## Output bounds and metric shape

The exporter accepts at most 100,000 snapshots and caps encoded output at 8 MiB. It validates
Prometheus family, label, and generated histogram sample names; invalid samples or collisions fail
the scrape rather than being silently omitted. If output reaches the limit, reduce instrumentation
or label cardinality instead of raising the bound without measuring scrape memory and latency.

The exporter sorts metric families and label sets for deterministic output. It emits counter,
gauge, and histogram types. Histogram output includes finite buckets, the `+Inf` bucket, sum, and
count. This capability does not add HELP text or accept arbitrary exporter configuration.

## Operational checks

Use the in-process `orbit-testing` client to verify the route and authorization wiring, then test
scrapes through the same ingress/authentication path used by the monitoring system. Validate
response size, scrape duration under expected series volume, unauthorized requests, auth-provider
outages, and behavior when a metric name or label cannot be represented. Confirm that the chosen
scrape interval and timeout can tolerate diagnostics collection and exposition work.
