"""Unit tests for the machine-readable events module (B3.2)."""

from __future__ import annotations

import json
from pathlib import Path

from mathstudio_renderer.events import (
    EVENTS_FILENAME,
    EVENTS_PROTOCOL_VERSION,
    EventEmitter,
    get_final_event,
    parse_events_file,
)


class TestEventEmitter:
    def test_creates_events_file(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        events_path = tmp_path / EVENTS_FILENAME
        assert events_path.exists()

    def test_events_are_valid_json_lines(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        emitter.validating()
        emitter.rendering(30)
        emitter.completed(1234.5)

        lines = (tmp_path / EVENTS_FILENAME).read_text().splitlines()
        assert len(lines) == 4
        for line in lines:
            obj = json.loads(line)
            assert isinstance(obj, dict)

    def test_protocol_version_present(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev["protocol_version"] == EVENTS_PROTOCOL_VERSION

    def test_renderer_request_id_present(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "abc123-a2")
        emitter.validating()
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev["renderer_request_id"] == "abc123-a2"

    def test_required_fields_present(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.rendering(50)
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        for field in ("protocol_version", "renderer_request_id", "phase",
                      "progress_hint", "timestamp", "elapsed_ms",
                      "message_code", "status"):
            assert field in ev, f"missing field: {field}"

    def test_progress_hint_clamped_to_99(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.emit("rendering", progress_hint=200, message_code="X", status="running")
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev["progress_hint"] <= 99

    def test_progress_hint_min_zero(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.emit("rendering", progress_hint=-10, message_code="X", status="running")
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev["progress_hint"] >= 0

    def test_completed_event_has_status_completed(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.completed(500.0)
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev["status"] == "completed"
        assert ev["phase"] == "completed"

    def test_failed_event_has_status_failed(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.failed("RENDER_PROCESS_FAILED", "Manim exited with code 1")
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev["status"] == "failed"
        assert ev["phase"] == "failed"

    def test_cancelled_event_has_status_cancelled(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.cancelled()
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev["status"] == "cancelled"

    def test_events_are_append_only(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        emitter.validating()
        emitter.completed(100.0)
        events = parse_events_file(tmp_path / EVENTS_FILENAME)
        assert len(events) == 3
        phases = [e["phase"] for e in events]
        assert phases == ["received", "validating", "completed"]

    def test_elapsed_ms_is_non_negative(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        emitter.completed(100.0)
        for ev in parse_events_file(tmp_path / EVENTS_FILENAME):
            assert ev["elapsed_ms"] >= 0

    def test_extra_fields_merged(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.emit("completed", progress_hint=99, message_code="DONE", status="completed",
                     extra={"custom_key": "custom_val"})
        ev = parse_events_file(tmp_path / EVENTS_FILENAME)[0]
        assert ev.get("custom_key") == "custom_val"


class TestParseEventsFile:
    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text("")
        assert parse_events_file(path) == []

    def test_nonexistent_file_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.jsonl"
        assert parse_events_file(path) == []

    def test_tolerates_corrupted_line(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text('{"phase":"received"}\n{corrupted\n{"phase":"validating"}\n')
        events = parse_events_file(path)
        # Only 2 valid lines
        assert len(events) == 2
        assert events[0]["phase"] == "received"
        assert events[1]["phase"] == "validating"


class TestGetFinalEvent:
    def test_returns_completed_event(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        emitter.validating()
        emitter.completed(999.9)
        final = get_final_event(tmp_path / EVENTS_FILENAME)
        assert final is not None
        assert final["status"] == "completed"

    def test_returns_failed_event(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        emitter.failed("RENDER_PROCESS_FAILED", "oops")
        final = get_final_event(tmp_path / EVENTS_FILENAME)
        assert final is not None
        assert final["status"] == "failed"

    def test_returns_none_when_no_terminal_event(self, tmp_path: Path) -> None:
        emitter = EventEmitter(tmp_path, "testreq01")
        emitter.received()
        emitter.validating()
        final = get_final_event(tmp_path / EVENTS_FILENAME)
        assert final is None

    def test_returns_none_for_nonexistent_file(self, tmp_path: Path) -> None:
        assert get_final_event(tmp_path / "nofile.jsonl") is None
