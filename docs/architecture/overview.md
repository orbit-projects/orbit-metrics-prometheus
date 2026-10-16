# Architecture

`orbit-metrics-prometheus` is an optional exporter and Core plugin. It implements the
`orbit_metrics.MetricsExporter` capability and can register a `GET /metrics` route. Core itself
does not reserve the path or serve Prometheus exposition.

```text
Core MetricsRegistry
  └── detached MetricSnapshot tuple
      └── PrometheusExporter
          ├── validates family and generated sample names
          ├── emits deterministic TYPE and sample lines
          └── returns UTF-8 text, capped at 8 MiB

PrometheusPlugin
  └── optional GET /metrics route
      ├── refreshes Core runtime diagnostics per scrape
      ├── exports the current metric snapshot
      └── declares orbit.metrics.read by default
```

The exporter emits counters, gauges, and histogram bucket/sum/count samples using Prometheus text
format conventions. Label names are validated, label values are escaped, and families are sorted
to make output deterministic. Metric-family and histogram-generated sample-name collisions are
rejected rather than silently merged. Exposition omits HELP metadata because Core snapshots do
not currently define help text.

The route's role requirement is stored by Core, but Core does not evaluate it. `ASGIApplication`
must be configured with an authenticator and authorizer capable of enforcing route roles. The
default role is `orbit.metrics.read`. Passing an empty role set makes the route public at the
application authorization layer and is appropriate only when an independently trusted network
boundary protects access.

This package does not install global metrics state, choose the registry's data policy, or provide
remote write. It has no vendor exporter dependency; its output is scraped by Prometheus-compatible
systems.
