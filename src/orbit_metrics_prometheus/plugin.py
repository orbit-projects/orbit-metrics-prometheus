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
"""Optional protected ASGI endpoint for Prometheus scrapes."""

from collections.abc import Sequence

from orbit import Application
from orbit.asgi import Request, Response
from orbit.plugins import Plugin, PluginMetadata
from orbit_metrics import MetricsExporter

from orbit_metrics_prometheus.exporter import PrometheusExporter


class PrometheusPlugin(Plugin):
    """Register `/metrics` using the Core plugin and route contracts.

    The default route requires the ``orbit.metrics.read`` role. Set ``roles`` to an empty frozen
    set only when a trusted network boundary independently protects the endpoint.
    """

    metadata = PluginMetadata(
        name="orbit-metrics-prometheus",
        version="0.1.0a1",
        capabilities=frozenset({"metrics.export"}),
    )

    def __init__(self, *, roles: Sequence[str] = ("orbit.metrics.read",)) -> None:
        """Configure route-level authorization for the optional scrape endpoint."""
        if isinstance(roles, (str, bytes)):
            raise TypeError("Prometheus route roles must be a sequence of role strings.")
        role_set: set[str] = set()
        for index, role in enumerate(roles, start=1):
            if index > 1_024:
                raise ValueError("Prometheus route roles cannot exceed 1,024 entries.")
            if not isinstance(role, str):
                raise TypeError("Prometheus route roles must contain strings.")
            role_set.add(role)
        self._roles = frozenset(role_set)
        self._exporter: MetricsExporter = PrometheusExporter()

    def setup(self, application: Application) -> None:
        """Contribute a `/metrics` handler that exports a fresh Core snapshot on each scrape."""
        if not isinstance(application, Application):
            raise TypeError("PrometheusPlugin requires an Orbit Application.")

        @application.router.route(
            "/metrics", method="GET", name="orbit-metrics-prometheus-metrics", roles=self._roles
        )
        async def metrics(request: Request) -> Response:
            """Refresh runtime diagnostics and return their Prometheus text exposition."""
            application.diagnostics.update_runtime(application)
            exposition = self._exporter.export(application.diagnostics.metrics.snapshots())
            return Response(
                body=exposition.encode("utf-8"),
                headers={"content-type": "text/plain; version=0.0.4; charset=utf-8"},
            )


__all__ = ["PrometheusPlugin"]
