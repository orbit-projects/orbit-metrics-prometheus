# Copyright 2026-present Orbit Contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Prometheus output preserves Core snapshot data with deterministic escaping."""

import pytest
from orbit import Application, ApplicationConfig
from orbit.asgi import ASGIApplication
from orbit.diagnostics import MetricSnapshot, MetricsRegistry
from orbit_metrics import MetricsExporter
from orbit_security import Identity, Principal, RoleAuthorizer
from orbit_testing import TestClient

from orbit_metrics_prometheus import PrometheusExporter, PrometheusPlugin


def test_exporter_renders_counter_gauge_and_histogram() -> None:
    metrics = MetricsRegistry()
    metrics.counter("requests_total", labels=("method",)).inc(method="GET")
    metrics.gauge("temperature", labels=("zone",)).set(21.5, zone='north"\\wing')
    metrics.histogram("latency_seconds", buckets=(1.0, 2.0)).observe(0.5)
    exporter = PrometheusExporter()

    assert isinstance(exporter, MetricsExporter)
    output = exporter.export(metrics.snapshots())
    assert '# TYPE requests_total counter\nrequests_total{method="GET"} 1.0' in output
    assert 'temperature{zone="north\\"\\\\wing"} 21.5' in output
    assert 'latency_seconds_bucket{le="1.0"} 1' in output
    assert 'latency_seconds_bucket{le="+Inf"} 1' in output
    assert "latency_seconds_count 1" in output


def test_exporter_rejects_prometheus_reserved_histogram_label() -> None:
    snapshot = MetricSnapshot(
        name="latency",
        kind="histogram",
        labels={"le": "custom"},
        value=0,
        count=0,
        sum=0,
        buckets={1.0: 0},
    )
    with pytest.raises(ValueError, match="'le'"):
        PrometheusExporter().export((snapshot,))


def test_exporter_rejects_core_label_names_outside_prometheus_grammar() -> None:
    snapshot = MetricSnapshot("requests_total", "counter", {"bad:name": "value"}, 1)
    with pytest.raises(ValueError, match="label name"):
        PrometheusExporter().export((snapshot,))


@pytest.mark.parametrize("conflicting_name", ("latency_bucket", "latency_sum", "latency_count"))
def test_exporter_rejects_histogram_generated_sample_collisions(
    conflicting_name: str,
) -> None:
    histogram = MetricSnapshot("latency", "histogram", {}, 0, count=0, sum=0, buckets={1.0: 0})
    conflicting = MetricSnapshot(conflicting_name, "gauge", {}, 1)

    with pytest.raises(ValueError, match="collid"):
        PrometheusExporter().export((histogram, conflicting))


def test_exporter_rejects_output_above_eight_mib() -> None:
    labels = {f"label_{index:02}": "v" * 256 for index in range(32)}
    snapshots = tuple(
        MetricSnapshot(f"metric_{index}", "gauge", labels, 1) for index in range(1_100)
    )

    with pytest.raises(ValueError, match="8 MiB"):
        PrometheusExporter().export(snapshots)


async def test_metrics_plugin_requires_role_and_serves_endpoint_when_authorized() -> None:
    class Auth:
        async def authenticate(self, request):
            return Principal(
                identity=Identity(subject="scraper", provider="test"),
                roles=frozenset({"orbit.metrics.read"}),
            )

    app = Application(ApplicationConfig(name="prometheus-plugin"))
    app.register_plugin(PrometheusPlugin())
    async with TestClient(ASGIApplication(app)) as client:
        denied = await client.request("GET", "/metrics")
    assert denied.status == 401

    app = Application(ApplicationConfig(name="prometheus-plugin-authorized"))
    app.register_plugin(PrometheusPlugin())
    async with TestClient(
        ASGIApplication(app, authenticator=Auth(), authorizer=RoleAuthorizer())
    ) as client:
        await client.request("GET", "/missing")
        response = await client.request("GET", "/metrics")
    assert response.status == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert "orbit_http_responses_total" in response.body.decode()
