"""Machine-readable phase events for B3.2 worker integration.

Events are written as newline-delimited JSON (JSON Lines) to a file at
``{output_dir}/events.jsonl``.  The worker reads this file to observe
renderer progress and map phases to Control-Plane progress values.

Protocol invariants
-------------------
* Every event line is a complete, self-describing JSON object.
* ``protocol_version`` is always present and currently ``"1.0.0"``.
* ``renderer_request_id`` is always present and matches the request.
* ``phase`` uses the ``RenderPhase`` vocabulary.
* ``progress_hint`` is 0–99 (the worker maps it; 100 is set by complete RPC).
* ``elapsed_ms`` is wall-clock ms since the renderer started.
* ``message_code`` is a stable machine-readable label (never raw exception text).
* ``status`` is ``"running"`` | ``"completed"`` | ``"failed"`` | ``"cancelled"``.
* Events are append-only; no line is ever modified.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import orjson

EVENTS_PROTOCOL_VERSION = "1.0.0"
EVENTS_FILENAME = "events.jsonl"


class EventEmitter:
    """Emits machine-readable phase events to ``events.jsonl``."""

    def __init__(
        self,
        output_dir: Path,
        renderer_request_id: str,
        started_at_ns: int | None = None,
    ) -> None:
        self._path = output_dir / EVENTS_FILENAME
        self._request_id = renderer_request_id
        self._started_ns = started_at_ns if started_at_ns is not None else time.monotonic_ns()
        # Ensure parent exists before first write
        output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(
        self,
        phase: str,
        *,
        progress_hint: int,
        message_code: str,
        status: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Append one event line to ``events.jsonl``."""
        elapsed_ms = (time.monotonic_ns() - self._started_ns) / 1_000_000
        event: dict[str, Any] = {
            "protocol_version": EVENTS_PROTOCOL_VERSION,
            "renderer_request_id": self._request_id,
            "phase": phase,
            "progress_hint": max(0, min(99, progress_hint)),
            "timestamp": _iso_now(),
            "elapsed_ms": round(elapsed_ms, 1),
            "message_code": message_code,
            "status": status,
        }
        if extra:
            event.update(extra)
        line = orjson.dumps(event).decode() + "\n"
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()

    # ------------------------------------------------------------------
    # Phase convenience helpers
    # ------------------------------------------------------------------

    def received(self) -> None:
        self.emit(
            "received",
            progress_hint=1,
            message_code="RENDER_RECEIVED",
            status="running",
        )

    def validating(self) -> None:
        self.emit(
            "validating",
            progress_hint=5,
            message_code="RENDER_VALIDATING",
            status="running",
        )

    def preparing_workspace(self) -> None:
        self.emit(
            "preparing_workspace",
            progress_hint=10,
            message_code="RENDER_PREPARING",
            status="running",
        )

    def building_scene(self) -> None:
        self.emit(
            "building_scene",
            progress_hint=20,
            message_code="RENDER_BUILDING_SCENE",
            status="running",
        )

    def rendering(self, progress_hint: int = 25) -> None:
        self.emit(
            "rendering",
            progress_hint=progress_hint,
            message_code="RENDER_RENDERING",
            status="running",
        )

    def validating_artifacts(self) -> None:
        self.emit(
            "validating_artifacts",
            progress_hint=90,
            message_code="RENDER_VALIDATING_ARTIFACTS",
            status="running",
        )

    def writing_metadata(self) -> None:
        self.emit(
            "writing_metadata",
            progress_hint=95,
            message_code="RENDER_WRITING_METADATA",
            status="running",
        )

    def completed(self, elapsed_ms: float) -> None:
        self.emit(
            "completed",
            progress_hint=99,
            message_code="RENDER_COMPLETED",
            status="completed",
            extra={"elapsed_ms_total": round(elapsed_ms, 1)},
        )

    def failed(self, error_code: str, message: str) -> None:
        self.emit(
            "failed",
            progress_hint=0,
            message_code=error_code,
            status="failed",
            extra={"error_message": message},
        )

    def cancelled(self) -> None:
        self.emit(
            "cancelled",
            progress_hint=0,
            message_code="RENDER_CANCELLED",
            status="cancelled",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    """Return current UTC timestamp as ISO-8601."""
    import datetime

    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


def parse_events_file(path: Path) -> list[dict[str, Any]]:
    """Parse all events from an events.jsonl file.  Tolerates partial lines."""
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(orjson.loads(line))
        except Exception:  # noqa: BLE001,S110
            pass  # tolerate partial/corrupted lines
    return events


def get_final_event(path: Path) -> dict[str, Any] | None:
    """Return the last terminal event (completed/failed/cancelled), if any."""
    events = parse_events_file(path)
    for ev in reversed(events):
        if ev.get("status") in {"completed", "failed", "cancelled"}:
            return ev
    return None
