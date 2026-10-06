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
"""Deterministically serialize validated Core snapshots in Prometheus text format."""

import re
from collections.abc import Mapping

from orbit.diagnostics import MetricSnapshot

_METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]{0,254}$")
_LABEL_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,254}$")
_MAX_SNAPSHOTS = 100_000
_MAX_OUTPUT_BYTES = 8 * 1024 * 1024


class PrometheusExporter:
    """Render Core snapshots using Prometheus's text exposition conventions."""

    def export(self, snapshots: tuple[MetricSnapshot, ...]) -> str:
        """Return deterministic TYPE and sample lines for a detached snapshot collection."""
        if not isinstance(snapshots, tuple):
            raise TypeError("Prometheus export requires a tuple of Core MetricSnapshot values.")
        if len(snapshots) > _MAX_SNAPSHOTS:
            raise ValueError("Prometheus export exceeds the 100,000-series output limit.")
        if any(not isinstance(snapshot, MetricSnapshot) for snapshot in snapshots):
            raise TypeError("Prometheus export requires a tuple of Core MetricSnapshot values.")
        grouped: dict[str, list[MetricSnapshot]] = {}
        kinds: dict[str, str] = {}
        for snapshot in snapshots:
            if _METRIC_NAME.fullmatch(snapshot.name) is None:
                raise ValueError("Metric snapshot name is not valid in Prometheus exposition.")
            if any(_LABEL_NAME.fullmatch(name) is None for name in snapshot.labels):
                raise ValueError(
                    "Metric snapshot label name is not valid in Prometheus exposition."
                )
            if snapshot.kind == "histogram" and "le" in snapshot.labels:
                raise ValueError("Histogram snapshots cannot define the Prometheus 'le' label.")
            previous = kinds.setdefault(snapshot.name, snapshot.kind)
            if previous != snapshot.kind:
                raise ValueError("A metric name cannot have multiple Prometheus types.")
            grouped.setdefault(snapshot.name, []).append(snapshot)

        self._validate_sample_names(grouped, kinds)
        lines: list[str] = []
        output_bytes = 0
        for name in sorted(grouped):
            output_bytes = _append_line(lines, f"# TYPE {name} {kinds[name]}", output_bytes)
            for snapshot in sorted(
                grouped[name], key=lambda item: tuple(sorted(item.labels.items()))
            ):
                labels = _format_labels(snapshot.labels)
                if snapshot.kind == "histogram":
                    buckets = snapshot.buckets
                    if buckets is None:
                        raise ValueError("Histogram snapshots must include bucket values.")
                    for bound, count in sorted(buckets.items()):
                        bucket_labels = _format_labels({**snapshot.labels, "le": str(bound)})
                        output_bytes = _append_line(
                            lines, f"{name}_bucket{bucket_labels} {count}", output_bytes
                        )
                    infinite_labels = _format_labels({**snapshot.labels, "le": "+Inf"})
                    output_bytes = _append_line(
                        lines, f"{name}_bucket{infinite_labels} {snapshot.count}", output_bytes
                    )
                    output_bytes = _append_line(
                        lines, f"{name}_sum{labels} {snapshot.sum}", output_bytes
                    )
                    output_bytes = _append_line(
                        lines, f"{name}_count{labels} {snapshot.count}", output_bytes
                    )
                else:
                    output_bytes = _append_line(
                        lines, f"{name}{labels} {snapshot.value}", output_bytes
                    )
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _validate_sample_names(
        grouped: Mapping[str, list[MetricSnapshot]], kinds: Mapping[str, str]
    ) -> None:
        """Reject histogram-generated samples that overlap another metric family."""
        owners: dict[str, str] = {}
        for family, kind in kinds.items():
            samples = {family}
            if kind == "histogram":
                samples.update((f"{family}_bucket", f"{family}_sum", f"{family}_count"))
            for sample in samples:
                owner = owners.setdefault(sample, family)
                if owner != family:
                    raise ValueError("Metric families produce colliding Prometheus sample names.")
        for family in grouped:
            family_owner = owners.get(family)
            if family_owner is not None and family_owner != family:
                raise ValueError("Metric family name collides with a generated Prometheus sample.")


def _format_labels(labels: Mapping[str, str]) -> str:
    """Escape validated label text and sort it for reproducible output."""
    if not labels:
        return ""
    escaped = {
        key: value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        for key, value in sorted(labels.items())
    }
    return "{" + ",".join(f'{key}="{value}"' for key, value in escaped.items()) + "}"


def _append_line(lines: list[str], line: str, current_bytes: int) -> int:
    """Append one exposition line without exceeding the bounded encoded response size."""
    updated_bytes = current_bytes + len(line.encode("utf-8")) + 1
    if updated_bytes > _MAX_OUTPUT_BYTES:
        raise ValueError("Prometheus exposition exceeds the 8 MiB output limit.")
    lines.append(line)
    return updated_bytes


__all__ = ["PrometheusExporter"]
