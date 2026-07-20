import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT_PATH = (
    Path(__file__).parents[2] / "plugins/habit-tracker-control/scripts/habitctl.py"
)
spec = importlib.util.spec_from_file_location("habitctl", SCRIPT_PATH)
habitctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(habitctl)


class FakeClient:
    def __init__(self):
        self.calls = []
        self.goals = [
            {
                "id": 1,
                "title": "Faire le tour du monde",
                "completed": False,
                "substeps": [],
            }
        ]

    def request(self, method, path, payload=None, idempotency_key=None):
        self.calls.append((method, path, payload, idempotency_key))
        if path == "/api/v1/goals":
            return self.goals
        if method == "POST":
            self.goals.append(
                {
                    "id": 2,
                    "title": payload["title"],
                    "completed": False,
                    "substeps": payload.get("substeps", []),
                }
            )
            return {"status": "success"}
        raise AssertionError((method, path))


class ResolutionClient:
    def request(self, method, path, payload=None, idempotency_key=None):
        assert method == "GET"
        if path == "/api/v1/goals":
            return [
                {
                    "id": 1,
                    "title": "Tour du monde",
                    "substeps": [{"id": 2, "title": "Obtenir un passeport"}],
                }
            ]
        if path == "/api/v1/softskills":
            return {
                "branches": {"communication": {}},
                "skills": [{"id": "ecoute", "name": "Écoute active"}],
            }
        raise AssertionError(path)


class TargetResolutionClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, payload=None, idempotency_key=None):
        self.calls.append((method, path, payload, idempotency_key))
        assert method == "GET"
        if path == "/api/v1/habits":
            return [{"id": 24, "name": "test", "archived_at": None}]
        if path == "/api/v1/habits?include_archived=true&include_all_versions=true":
            return [
                {
                    "id": 24,
                    "name": "test",
                    "frequency": "daily",
                    "archived_at": "2026-06-30T00:00:00",
                    "source_type": "manual",
                },
                {
                    "id": 25,
                    "name": "active test",
                    "frequency": "daily",
                    "archived_at": None,
                    "source_type": "manual",
                },
            ]
        if path == "/api/v1/todos":
            return [
                {"id": 12, "title": "Active bounty", "is_completed": False},
                {"id": 13, "title": "Done bounty", "is_completed": True},
            ]
        if path == "/api/v1/notodos":
            return [{"id": 5, "title": "Snoozer", "failed_today": False}]
        if path == "/api/v1/biological-zones":
            return [{"id": 2, "zone_name": "Sommeil", "zone_type": "sleep"}]
        raise AssertionError(path)


class ConfigureClient:
    def __init__(self, capabilities=None, error=None):
        self.capabilities = capabilities
        self.error = error

    def request(self, method, path, payload=None, idempotency_key=None):
        assert method == "GET"
        if path == "/api/v1/auth/users":
            return [{"id": 3, "username": "Gabriel"}]
        if path == "/api/v1/capabilities":
            if self.error:
                raise self.error
            return self.capabilities
        raise AssertionError(path)


def test_normalization_and_ambiguity():
    items = [{"title": "Karaoké"}, {"title": "Karaoké avancé"}]
    assert (
        habitctl.resolve_one(items, "karaoke", "title", "skill")["title"] == "Karaoké"
    )
    with pytest.raises(habitctl.HabitCtlError, match="Ambiguous"):
        habitctl.resolve_one(items, "kara", "title", "skill")


def test_branch_defaults_are_deterministic():
    prepared = habitctl.prepare_plan_data(
        "softskill-branch-with-skills",
        {"name": "Bon vivant", "skills": ["Karaoké", "Danse", "Ukulélé"]},
    )
    assert prepared["key"] == "bon_vivant"
    assert prepared["color"] == habitctl.branch_colors("bon_vivant")[0]
    assert [skill["id"] for skill in prepared["skills"]] == [
        "karaoke",
        "danse",
        "ukulele",
    ]
    assert all(skill["branch"] == "bon_vivant" for skill in prepared["skills"])
    assert all("x" not in skill and "y" not in skill for skill in prepared["skills"])


def test_softskill_defaults_leave_position_to_backend():
    prepared = habitctl.prepare_plan_data(
        "softskill-create",
        {"name": "Écoute profonde", "branch": "communication"},
    )
    assert "x" not in prepared
    assert "y" not in prepared


def test_plan_does_not_write(monkeypatch, tmp_path):
    client = FakeClient()
    monkeypatch.setenv("HABIT_TRACKER_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        habitctl,
        "configured_client",
        lambda: (
            client,
            {"base_url": "http://127.0.0.1:5000"},
            {"id": 1, "username": "Gabriel"},
        ),
    )
    result = habitctl.command_plan(
        SimpleNamespace(
            operation="goal-create",
            data='{"title":"Devenir millionnaire"}',
        )
    )
    assert result["status"] == "confirmation_required"
    assert all(call[0] == "GET" for call in client.calls)
    assert client.goals == [
        {
            "id": 1,
            "title": "Faire le tour du monde",
            "completed": False,
            "substeps": [],
        }
    ]


def test_apply_refuses_changed_state(monkeypatch, tmp_path):
    client = FakeClient()
    monkeypatch.setenv("HABIT_TRACKER_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        habitctl,
        "configured_client",
        lambda: (
            client,
            {"base_url": "http://127.0.0.1:5000"},
            {"id": 1, "username": "Gabriel"},
        ),
    )
    result = habitctl.command_plan(
        SimpleNamespace(
            operation="goal-create",
            data='{"title":"Devenir millionnaire"}',
        )
    )
    client.goals.append(
        {"id": 3, "title": "État modifié", "completed": False, "substeps": []}
    )
    with pytest.raises(habitctl.HabitCtlError, match="state changed"):
        habitctl.command_apply(SimpleNamespace(plan_id=result["plan_id"]))


def test_apply_writes_once_and_replays_local_result(monkeypatch, tmp_path):
    client = FakeClient()
    monkeypatch.setenv("HABIT_TRACKER_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        habitctl,
        "configured_client",
        lambda: (
            client,
            {"base_url": "http://127.0.0.1:5000"},
            {"id": 1, "username": "Gabriel"},
        ),
    )
    planned = habitctl.command_plan(
        SimpleNamespace(
            operation="goal-create",
            data='{"title":"Devenir millionnaire"}',
        )
    )
    applied = habitctl.command_apply(SimpleNamespace(plan_id=planned["plan_id"]))
    replayed = habitctl.command_apply(SimpleNamespace(plan_id=planned["plan_id"]))

    assert applied["status"] == "applied"
    assert replayed["status"] == "already_applied"
    assert len([call for call in client.calls if call[0] == "POST"]) == 1


def test_plain_http_rejects_public_hosts():
    with pytest.raises(habitctl.HabitCtlError, match="private LAN"):
        habitctl.validate_base_url("http://example.com")
    assert (
        habitctl.validate_base_url("http://192.168.0.199:5000")
        == "http://192.168.0.199:5000"
    )


def test_link_and_pin_operations_resolve_names_to_ids():
    client = ResolutionClient()
    method, path, payload, _resource = habitctl.operation_request(
        client,
        "substep-link",
        {"goal": "Tour du monde", "substep": "Passeport"},
    )
    assert (method, path, payload) == (
        "POST",
        "/api/v1/substeps/link",
        {"goal_id": 1, "substep_id": 2},
    )

    _method, _path, pins, _resource = habitctl.operation_request(
        client,
        "pins-update",
        {
            "pinned_substeps": ["Passeport"],
            "pinned_softskills": ["Écoute active"],
        },
    )
    assert pins == {
        "pinned_substeps": [2],
        "pinned_softskills": ["ecoute"],
    }


def test_todo_update_resolves_active_todo_only():
    client = TargetResolutionClient()
    method, path, payload, resource = habitctl.operation_request(
        client, "todo-update", {"target": "Active", "title": "Renamed"}
    )
    assert (method, path, payload, resource) == (
        "PUT",
        "/api/v1/todos/12",
        {"title": "Renamed"},
        "todos",
    )
    with pytest.raises(habitctl.HabitCtlError, match="No todo matches"):
        habitctl.operation_request(client, "todo-delete", {"target": "Done"})


def test_notodo_delete_resolves_by_title():
    client = TargetResolutionClient()
    method, path, payload, resource = habitctl.operation_request(
        client, "notodo-delete", {"target": "Snoozer"}
    )
    assert (method, path, payload, resource) == (
        "DELETE",
        "/api/v1/notodos/5",
        None,
        "notodos",
    )


def test_biological_zone_update_resolves_by_zone_name():
    client = TargetResolutionClient()
    method, path, payload, resource = habitctl.operation_request(
        client,
        "biological-zone-update",
        {"target": "Sommeil", "end_time": "06:30"},
    )
    assert (method, path, payload, resource) == (
        "PUT",
        "/api/v1/biological-zones/2",
        {"end_time": "06:30"},
        "biological-zones",
    )


def test_habit_unarchive_resolves_including_archived_habits():
    client = TargetResolutionClient()
    method, path, payload, resource = habitctl.operation_request(
        client, "habit-unarchive", {"target": "test"}
    )
    assert (method, path, payload, resource) == (
        "POST",
        "/api/v1/habits/24/unarchive",
        {},
        "habits",
    )
    assert (
        "GET",
        "/api/v1/habits?include_archived=true&include_all_versions=true",
        None,
        None,
    ) in client.calls


def test_query_archived_habits_uses_all_versions(monkeypatch):
    client = TargetResolutionClient()
    monkeypatch.setattr(
        habitctl,
        "configured_client",
        lambda: (
            client,
            {"base_url": "http://127.0.0.1:5000"},
            {"id": 1, "username": "Gabriel"},
        ),
    )

    result = habitctl.command_query(
        SimpleNamespace(
            resource="archived-habits",
            name=None,
            year=2026,
            month=7,
            date=None,
        )
    )

    assert result == {
        "count": 1,
        "items": [
            {
                "id": 24,
                "name": "test",
                "frequency": "daily",
                "archived_at": "2026-06-30T00:00:00",
                "source_type": "manual",
            }
        ],
    }
    assert (
        "GET",
        "/api/v1/habits?include_archived=true&include_all_versions=true",
        None,
        None,
    ) in client.calls


def test_agenda_placement_set_resolves_habit_and_defaults_date(monkeypatch):
    client = TargetResolutionClient()
    monkeypatch.setattr(
        habitctl.dt, "date", SimpleNamespace(today=lambda: SimpleNamespace(
            isoformat=lambda: "2026-07-01"
        ))
    )
    method, path, payload, resource = habitctl.operation_request(
        client,
        "agenda-placement-set",
        {"habit": "test", "start_time": "06:00", "duration_minutes": 15},
    )
    assert (method, path, payload, resource) == (
        "PUT",
        "/api/v1/agenda/2026-07-01/quests/24/placement",
        {"start_time": "06:00", "duration_minutes": 15},
        "agenda",
    )


def test_agenda_placement_clear_has_no_payload():
    client = TargetResolutionClient()
    method, path, payload, resource = habitctl.operation_request(
        client,
        "agenda-placement-clear",
        {"habit": "test", "date": "2026-07-04"},
    )
    assert (method, path, payload, resource) == (
        "DELETE",
        "/api/v1/agenda/2026-07-04/quests/24/placement",
        None,
        "agenda",
    )


def test_agenda_save_as_template_does_not_require_a_habit():
    client = TargetResolutionClient()
    method, path, payload, resource = habitctl.operation_request(
        client,
        "agenda-save-as-template",
        {"date": "2026-07-04", "template_name": "hustle"},
    )
    assert (method, path, payload, resource) == (
        "POST",
        "/api/v1/agenda/2026-07-04/save-as-template",
        {"template_name": "hustle"},
        "agenda",
    )


def test_api_error_payload_includes_request_context():
    error = habitctl.ApiError(
        422,
        {"detail": "Invalid payload"},
        method="POST",
        path="/api/v1/todos",
    )

    assert habitctl.api_error_payload(error) == {
        "status": "api_error",
        "http_status": 422,
        "error": {"detail": "Invalid payload"},
        "method": "POST",
        "path": "/api/v1/todos",
    }


def test_missing_capabilities_has_deployment_hint():
    error = habitctl.ApiError(
        404,
        {"detail": "Not Found"},
        method="GET",
        path="/api/v1/capabilities",
    )

    payload = habitctl.api_error_payload(error)

    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/capabilities"
    assert "Deploy a backend version" in payload["hint"]


def test_protocol_mismatch_reports_versions():
    with pytest.raises(
        habitctl.HabitCtlError,
        match=r"Expected 2, received 1",
    ):
        habitctl.validate_protocol({"protocol_version": 1})


def test_configure_does_not_write_when_capabilities_are_missing(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    client = ConfigureClient(
        error=habitctl.ApiError(
            404,
            {"detail": "Not Found"},
            method="GET",
            path="/api/v1/capabilities",
        )
    )
    monkeypatch.setenv("HABIT_TRACKER_CONFIG", str(config_path))
    monkeypatch.setattr(habitctl, "ApiClient", lambda *_args, **_kwargs: client)

    with pytest.raises(habitctl.ApiError):
        habitctl.command_configure(
            SimpleNamespace(
                base_url="http://192.168.0.199:5000",
                username="Gabriel",
                api_token="token",
            )
        )

    assert not config_path.exists()


def test_configure_does_not_write_on_protocol_mismatch(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    client = ConfigureClient(capabilities={"protocol_version": 1})
    monkeypatch.setenv("HABIT_TRACKER_CONFIG", str(config_path))
    monkeypatch.setattr(habitctl, "ApiClient", lambda *_args, **_kwargs: client)

    with pytest.raises(habitctl.HabitCtlError, match="Expected 2, received 1"):
        habitctl.command_configure(
            SimpleNamespace(
                base_url="http://192.168.0.199:5000",
                username="Gabriel",
                api_token="token",
            )
        )

    assert not config_path.exists()
