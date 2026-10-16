# Security

## Route authorization

Prometheus metrics can disclose internal service names, deployment shape, dependency state, and
traffic patterns. The plugin requires the `orbit.metrics.read` role by default, but Core only stores
route role metadata. Configure an ASGI authenticator and authorizer to enforce it. A route
requirement without an authorizer is not access control. Keep the scrape endpoint on a trusted
network and use the same ingress and identity controls in production as in other operational APIs.

An empty role set removes the role requirement at the route. Use it only when a separate network
boundary restricts access. Verify behavior with both authenticated and unauthenticated requests.

## Metric content and cardinality

Metric labels and values may contain user, tenant, or infrastructure details. Instrument only
bounded, reviewed dimensions; never put credentials, tokens, request bodies, or raw personal data
in labels. High-cardinality labels can increase memory use and expose identifiers. This exporter
does not sanitize labels for sensitivity; it escapes text for syntax and enforces format bounds.

The exporter caps one response at 8 MiB and 100,000 snapshots, but those limits do not replace
safe instrumentation or access control. Avoid logging full scrape bodies and monitor failures
without attaching sensitive metric values to error reports.

## Vulnerability reporting

Use the private vulnerability-reporting guidance in the repository
[security policy](../../SECURITY.md).
