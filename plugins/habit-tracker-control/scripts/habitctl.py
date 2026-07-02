#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import socket
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


PROTOCOL_VERSION = 2
PLAN_TTL_SECONDS = 600
DEFAULT_BASE_URL = "http://192.168.0.199:5000"
BRANCH_PALETTE = [
    ("#8b5cf6", "#ddd6fe"),
    ("#0ea5e9", "#bae6fd"),
    ("#10b981", "#a7f3d0"),
    ("#f59e0b", "#fde68a"),
    ("#ef4444", "#fecaca"),
    ("#ec4899", "#fbcfe8"),
]

QUERY_PATHS = {
    "status": "/api/v1/status",
    "profile": "/api/v1/profile",
    "goals": "/api/v1/goals",
    "habits": "/api/v1/habits",
    "todos": "/api/v1/todos",
    "notodos": "/api/v1/notodos",
    "softskills": "/api/v1/softskills",
    "rewards": "/api/v1/rewards",
    "history": "/api/v1/history",
    "templates": "/api/v1/templates",
    "potentials": "/api/v1/quests/daily-stats-potentials",
    "agenda": "/api/v1/agenda",
    "biological-zones": "/api/v1/biological-zones",
}

PLAN_OPERATIONS = {
    "goal-create": ("POST", "/api/v1/goals", "goals"),
    "goal-with-substeps": ("POST", "/api/v1/goals/with-substeps", "goals"),
    "goal-update": ("PUT", "/api/v1/goals/{id}", "goals"),
    "goal-delete": ("DELETE", "/api/v1/goals/{id}", "goals"),
    "substep-create": ("POST", "/api/v1/goals/{goal_id}/substeps", "goals"),
    "substep-update": ("PUT", "/api/v1/substeps/{id}", "goals"),
    "substep-delete": ("DELETE", "/api/v1/substeps/{id}", "goals"),
    "substep-link": ("POST", "/api/v1/substeps/link", "goals"),
    "habit-create": ("POST", "/api/v1/habits", "habits"),
    "habit-update": ("PUT", "/api/v1/habits/{id}", "habits"),
    "habit-delete": ("DELETE", "/api/v1/habits/{id}", "habits"),
    "habit-archive": ("POST", "/api/v1/habits/{id}/archive", "habits"),
    "habit-unarchive": ("POST", "/api/v1/habits/{id}/unarchive", "habits"),
    "habit-levelup": ("POST", "/api/v1/habits/{id}/versions", "habits"),
    "todo-create": ("POST", "/api/v1/todos", "todos"),
    "todo-update": ("PUT", "/api/v1/todos/{id}", "todos"),
    "todo-delete": ("DELETE", "/api/v1/todos/{id}", "todos"),
    "notodo-create": ("POST", "/api/v1/notodos", "notodos"),
    "notodo-delete": ("DELETE", "/api/v1/notodos/{id}", "notodos"),
    "biological-zone-create": (
        "POST",
        "/api/v1/biological-zones",
        "biological-zones",
    ),
    "biological-zone-update": (
        "PUT",
        "/api/v1/biological-zones/{id}",
        "biological-zones",
    ),
    "biological-zone-delete": (
        "DELETE",
        "/api/v1/biological-zones/{id}",
        "biological-zones",
    ),
    "agenda-placement-set": (
        "PUT",
        "/api/v1/agenda/{date}/quests/{habit_id}/placement",
        "agenda",
    ),
    "agenda-placement-clear": (
        "DELETE",
        "/api/v1/agenda/{date}/quests/{habit_id}/placement",
        "agenda",
    ),
    "agenda-save-as-template": (
        "POST",
        "/api/v1/agenda/{date}/save-as-template",
        "agenda",
    ),
    "template-save": ("POST", "/api/v1/templates", "templates"),
    "pins-update": ("PUT", "/api/v1/profile/pins", "profile"),
    "reward-create": ("POST", "/api/v1/rewards", "rewards"),
    "reward-update": ("PUT", "/api/v1/rewards/{id}", "rewards"),
    "reward-delete": ("DELETE", "/api/v1/rewards/{id}", "rewards"),
    "softskill-branch-create": (
        "POST",
        "/api/v1/softskills/branches",
        "softskills",
    ),
    "softskill-branch-with-skills": (
        "POST",
        "/api/v1/softskills/branches-with-skills",
        "softskills",
    ),
    "softskill-branch-update": (
        "PUT",
        "/api/v1/softskills/branches/{key}",
        "softskills",
    ),
    "softskill-branch-delete": (
        "DELETE",
        "/api/v1/softskills/branches/{key}",
        "softskills",
    ),
    "softskill-create": ("POST", "/api/v1/softskills/skills", "softskills"),
    "softskill-update": (
        "PUT",
        "/api/v1/softskills/skills/{skill_id}",
        "softskills",
    ),
    "softskill-delete": (
        "DELETE",
        "/api/v1/softskills/skills/{skill_id}",
        "softskills",
    ),
    "softskill-test": (
        "POST",
        "/api/v1/softskills/{skill_id}/test",
        "softskills",
    ),
}


class HabitCtlError(Exception):
    pass


class ApiError(HabitCtlError):
    def __init__(self, status, payload, method=None, path=None):
        super().__init__(str(payload))
        self.status = status
        self.payload = payload
        self.method = method
        self.path = path


class AmbiguousWrite(HabitCtlError):
    def __init__(self, key):
        super().__init__("The write timed out and its outcome is unknown.")
        self.key = key


def config_path():
    override = os.getenv("HABIT_TRACKER_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config/habit-tracker-control/config.json"


def state_dir():
    override = os.getenv("HABIT_TRACKER_STATE_DIR")
    if override:
        return Path(override).expanduser()
    root = os.getenv("XDG_STATE_HOME")
    if root:
        return Path(root) / "habit-tracker-control"
    return Path.home() / ".local/state/habit-tracker-control"


def emit(payload, exit_code=0):
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    raise SystemExit(exit_code)


def normalize(value):
    decomposed = unicodedata.normalize("NFKD", str(value))
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(plain.casefold().split())


def slugify(value):
    chars = [ch if ch.isalnum() else "_" for ch in normalize(value)]
    return "_".join(part for part in "".join(chars).split("_") if part)


def branch_colors(key):
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return BRANCH_PALETTE[digest[0] % len(BRANCH_PALETTE)]


def stable_hash(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json_argument(raw):
    if raw == "-":
        raw = sys.stdin.read()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HabitCtlError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise HabitCtlError("The JSON payload must be an object.")
    return value


def validate_base_url(base_url):
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HabitCtlError("The base URL must use http:// or https://.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise HabitCtlError("The base URL must not include a path, query, or fragment.")
    if parsed.scheme == "http":
        hostname = parsed.hostname
        is_private = hostname in {"localhost", "127.0.0.1", "::1"}
        if not is_private:
            try:
                is_private = ipaddress.ip_address(hostname).is_private
            except ValueError:
                is_private = hostname.endswith(".local")
        if not is_private:
            raise HabitCtlError("Plain HTTP is allowed only for private LAN hosts.")
    return base_url.rstrip("/")


def write_config(config):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, path)


def read_config():
    path = config_path()
    if not path.exists():
        raise HabitCtlError(
            "Not configured. Run: habitctl.py configure --username NAME"
        )
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HabitCtlError(f"Cannot read configuration: {exc}") from exc
    config["base_url"] = validate_base_url(config["base_url"])
    return config


class ApiClient:
    def __init__(self, base_url, user_id=None, api_token=None, timeout=8.0):
        self.base_url = validate_base_url(base_url)
        self.user_id = user_id
        self.api_token = api_token
        self.timeout = timeout

    def request(self, method, path, payload=None, idempotency_key=None):
        body = None
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        if self.user_id is not None:
            headers["X-User-ID"] = str(self.user_id)
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                error_payload = json.loads(raw)
            except json.JSONDecodeError:
                error_payload = {"detail": raw or exc.reason}
            raise ApiError(
                exc.code,
                error_payload,
                method=method,
                path=path,
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            if method != "GET" and idempotency_key:
                raise AmbiguousWrite(idempotency_key) from exc
            raise HabitCtlError(f"Request timed out: {path}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                if method != "GET" and idempotency_key:
                    raise AmbiguousWrite(idempotency_key) from exc
                raise HabitCtlError(f"Request timed out: {path}") from exc
            raise HabitCtlError(f"Cannot reach {self.base_url}: {exc.reason}") from exc


def resolve_one(items, target, label_key, kind):
    wanted = normalize(target)
    exact = [item for item in items if normalize(item[label_key]) == wanted]
    candidates = exact or [
        item for item in items if wanted in normalize(item[label_key])
    ]
    if not candidates:
        raise HabitCtlError(f"No {kind} matches '{target}'.")
    if len(candidates) > 1:
        names = [item[label_key] for item in candidates]
        raise HabitCtlError(
            f"Ambiguous {kind} '{target}': {', '.join(names)}."
        )
    return candidates[0]


def resolve_user(base_url, username, api_token):
    users = ApiClient(base_url, api_token=api_token).request(
        "GET", "/api/v1/auth/users"
    )
    return resolve_one(users, username, "username", "user")


def validate_protocol(capabilities):
    received_version = capabilities.get("protocol_version")
    if received_version != PROTOCOL_VERSION:
        raise HabitCtlError(
            "The server protocol version is not supported. "
            f"Expected {PROTOCOL_VERSION}, received {received_version!r}."
        )


def api_error_payload(exc):
    payload = {
        "status": "api_error",
        "http_status": exc.status,
        "error": exc.payload,
    }
    if exc.method is not None:
        payload["method"] = exc.method
    if exc.path is not None:
        payload["path"] = exc.path
    if exc.status == 404 and exc.path == "/api/v1/capabilities":
        payload["hint"] = (
            "The Habit Tracker server does not expose protocol version 2. "
            "Deploy a backend version that provides "
            "GET /api/v1/capabilities before configuring this plugin."
        )
    return payload


def configured_client():
    config = read_config()
    api_token = config.get("api_token")
    if not api_token:
        raise HabitCtlError(
            "Missing api_token in configuration. Run configure with --api-token."
        )
    user = resolve_user(config["base_url"], config["username"], api_token)
    if config.get("user_id") != user["id"]:
        config["user_id"] = user["id"]
        write_config(config)
    return ApiClient(config["base_url"], user["id"], api_token), config, user


def compact_query(resource, payload, name=None):
    if resource == "goals":
        if name:
            return resolve_one(payload, name, "title", "goal")
        return {
            "count": len(payload),
            "items": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "completed": item["completed"],
                }
                for item in payload
            ],
        }
    if resource == "habits":
        if name:
            return resolve_one(payload, name, "name", "habit")
        return {
            "count": len(payload),
            "items": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "type": item["type"],
                    "frequency": item["frequency"],
                }
                for item in payload
            ],
        }
    if resource in {"todos", "notodos", "rewards"}:
        if name:
            return resolve_one(payload, name, "title", resource[:-1])
        fields = {
            "todos": ("id", "title", "is_completed"),
            "notodos": ("id", "title", "failed_today"),
            "rewards": (
                "id",
                "title",
                "gold_cost",
                "category",
                "unlocked",
                "is_available",
            ),
        }[resource]
        return {
            "count": len(payload),
            "items": [
                {field: item.get(field) for field in fields} for item in payload
            ],
        }
    if resource == "biological-zones":
        if name:
            return resolve_one(payload, name, "zone_name", "biological zone")
        return {
            "count": len(payload),
            "items": [
                {
                    "id": item["id"],
                    "zone_name": item["zone_name"],
                    "zone_type": item["zone_type"],
                    "start_time": item["start_time"],
                    "end_time": item["end_time"],
                }
                for item in payload
            ],
        }
    if resource == "softskills":
        skills = payload.get("skills", [])
        if name:
            return resolve_one(skills, name, "name", "softskill")
        return {
            "branches": list(payload.get("branches", {}).keys()),
            "items": [
                {
                    "id": skill["id"],
                    "name": skill["name"],
                    "branch": skill["branch"],
                    "completed": skill.get("progress", {}).get(
                        "completed", False
                    ),
                }
                for skill in skills
            ],
        }
    return payload


def command_configure(args):
    base_url = validate_base_url(args.base_url)
    user = resolve_user(base_url, args.username, args.api_token)
    capabilities = ApiClient(base_url, user["id"], args.api_token).request(
        "GET", "/api/v1/capabilities"
    )
    validate_protocol(capabilities)
    config = {
        "base_url": base_url,
        "username": user["username"],
        "user_id": user["id"],
        "api_token": args.api_token,
        "protocol_version": PROTOCOL_VERSION,
    }
    write_config(config)
    return {
        "status": "configured",
        "base_url": config["base_url"],
        "username": config["username"],
        "user_id": config["user_id"],
        "protocol_version": config["protocol_version"],
        "api_token_configured": True,
    }


def command_doctor(_args):
    client, config, user = configured_client()
    health = ApiClient(config["base_url"]).request("GET", "/health")
    capabilities = client.request("GET", "/api/v1/capabilities")
    validate_protocol(capabilities)
    return {
        "status": "ok",
        "server": health,
        "user": user,
        "capabilities": capabilities,
    }


def command_query(args):
    client, _config, _user = configured_client()
    if args.resource == "habit-calendar":
        if not args.name:
            raise HabitCtlError("--name is required for habit-calendar.")
        habits = client.request("GET", QUERY_PATHS["habits"])
        habit = resolve_one(habits, args.name, "name", "habit")
        query = urllib.parse.urlencode(
            {"year": args.year, "month": args.month}
        )
        return client.request(
            "GET",
            f"/api/v1/habits/{habit['id']}/calendar?{query}",
        )
    if args.resource == "agenda" and args.date:
        query = urllib.parse.urlencode({"date": args.date})
        return client.request("GET", f"{QUERY_PATHS['agenda']}?{query}")
    payload = client.request("GET", QUERY_PATHS[args.resource])
    return compact_query(args.resource, payload, args.name)


def flatten_substeps(goals):
    items = []
    for goal in goals:
        for substep in goal.get("substeps", []):
            items.append({**substep, "goal_title": goal["title"]})
    return items


def action_request(client, action, target, amount=None, reason=None):
    if action.startswith("habit-"):
        habits = client.request("GET", QUERY_PATHS["habits"])
        item = resolve_one(habits, target, "name", "habit")
        if action == "habit-done":
            payload = {"habit_id": item["id"], "log_type": "done"}
        elif action == "habit-log":
            if amount is None:
                raise HabitCtlError("--amount is required for habit-log.")
            payload = {
                "habit_id": item["id"],
                "log_type": "log",
                "amount": amount,
            }
        else:
            if not reason:
                raise HabitCtlError("--reason is required for habit-skip.")
            payload = {
                "habit_id": item["id"],
                "log_type": "skip",
                "reason": reason,
            }
        return "POST", "/api/v1/logs", payload
    if action == "todo-complete":
        todos = [
            item
            for item in client.request("GET", QUERY_PATHS["todos"])
            if not item["is_completed"]
        ]
        item = resolve_one(todos, target, "title", "todo")
        return "POST", f"/api/v1/todos/{item['id']}/complete", None
    if action == "notodo-fail":
        item = resolve_one(
            client.request("GET", QUERY_PATHS["notodos"]),
            target,
            "title",
            "no-todo",
        )
        return "POST", f"/api/v1/notodos/{item['id']}/fail", None
    if action == "substep-complete":
        item = resolve_one(
            flatten_substeps(client.request("GET", QUERY_PATHS["goals"])),
            target,
            "title",
            "substep",
        )
        return "POST", f"/api/v1/substeps/{item['id']}/complete", None
    if action in {"softskill-complete", "softskill-reset"}:
        tree = client.request("GET", QUERY_PATHS["softskills"])
        item = resolve_one(tree["skills"], target, "name", "softskill")
        return (
            "POST",
            f"/api/v1/softskills/{item['id']}/complete",
            {"completed": action == "softskill-complete"},
        )
    if action == "reward-purchase":
        rewards = client.request("GET", QUERY_PATHS["rewards"])
        item = resolve_one(rewards, target, "title", "reward")
        return "POST", f"/api/v1/rewards/{item['id']}/purchase", None
    if action == "template-set":
        return "POST", "/api/v1/profile/template", {"template_name": target}
    raise HabitCtlError(f"Unsupported action: {action}")


def command_act(args):
    client, _config, _user = configured_client()
    method, path, payload = action_request(
        client, args.action, args.target, args.amount, args.reason
    )
    key = f"habitctl-{uuid.uuid4()}"
    try:
        result = client.request(
            method, path, payload=payload, idempotency_key=key
        )
    except AmbiguousWrite:
        return {
            "status": "ambiguous",
            "idempotency_key": key,
            "recovery": f"recover {key}",
        }
    return {"status": "success", "idempotency_key": key, "result": result}


def operation_request(client, operation, data):
    method, path_template, inspect_resource = PLAN_OPERATIONS[operation]
    payload = dict(data)

    if "{id}" in path_template:
        target = payload.pop("target", None)
        if not target:
            raise HabitCtlError("This operation requires a 'target' field.")
        if operation.startswith("goal-"):
            items, label, kind = (
                client.request("GET", QUERY_PATHS["goals"]),
                "title",
                "goal",
            )
        elif operation.startswith("substep-"):
            items, label, kind = (
                flatten_substeps(client.request("GET", QUERY_PATHS["goals"])),
                "title",
                "substep",
            )
        elif operation == "habit-unarchive":
            items, label, kind = (
                client.request(
                    "GET", f"{QUERY_PATHS['habits']}?include_archived=true"
                ),
                "name",
                "habit",
            )
        elif operation.startswith("habit-"):
            items, label, kind = (
                client.request("GET", QUERY_PATHS["habits"]),
                "name",
                "habit",
            )
        elif operation.startswith("reward-"):
            items, label, kind = (
                client.request("GET", QUERY_PATHS["rewards"]),
                "title",
                "reward",
            )
        elif operation.startswith("todo-"):
            items, label, kind = (
                [
                    item
                    for item in client.request("GET", QUERY_PATHS["todos"])
                    if not item["is_completed"]
                ],
                "title",
                "todo",
            )
        elif operation.startswith("notodo-"):
            items, label, kind = (
                client.request("GET", QUERY_PATHS["notodos"]),
                "title",
                "no-todo",
            )
        elif operation.startswith("biological-zone-"):
            items, label, kind = (
                client.request("GET", QUERY_PATHS["biological-zones"]),
                "zone_name",
                "biological zone",
            )
        else:
            raise HabitCtlError("Cannot resolve the operation target.")
        item = resolve_one(items, target, label, kind)
        path_template = path_template.format(id=item["id"])

    if "{goal_id}" in path_template:
        goal_target = payload.pop("goal", None)
        if not goal_target:
            raise HabitCtlError("This operation requires a 'goal' field.")
        goal = resolve_one(
            client.request("GET", QUERY_PATHS["goals"]),
            goal_target,
            "title",
            "goal",
        )
        path_template = path_template.format(goal_id=goal["id"])

    if "{key}" in path_template:
        key = payload.pop("target", None)
        if not key:
            raise HabitCtlError("This operation requires a 'target' field.")
        branches = client.request("GET", QUERY_PATHS["softskills"])[
            "branches"
        ]
        branch = resolve_one(
            [{"key": branch_key} for branch_key in branches],
            key,
            "key",
            "branch",
        )
        path_template = path_template.format(key=branch["key"])

    if "{skill_id}" in path_template:
        target = payload.pop("target", None)
        if not target:
            raise HabitCtlError("This operation requires a 'target' field.")
        skills = client.request("GET", QUERY_PATHS["softskills"])["skills"]
        skill = resolve_one(skills, target, "name", "softskill")
        path_template = path_template.format(skill_id=skill["id"])

    if "{date}" in path_template:
        date_value = payload.pop("date", None) or dt.date.today().isoformat()
        if "{habit_id}" in path_template:
            habit_target = payload.pop("habit", None)
            if not habit_target:
                raise HabitCtlError(
                    "This operation requires a 'habit' field."
                )
            habit = resolve_one(
                client.request("GET", QUERY_PATHS["habits"]),
                habit_target,
                "name",
                "habit",
            )
            path_template = path_template.format(
                date=date_value, habit_id=habit["id"]
            )
        else:
            path_template = path_template.format(date=date_value)
        if operation == "agenda-placement-clear":
            payload = None

    if operation == "substep-link":
        goal_target = payload.pop("goal", None)
        substep_target = payload.pop("substep", None)
        if not goal_target or not substep_target:
            raise HabitCtlError(
                "substep-link requires 'goal' and 'substep' fields."
            )
        goals = client.request("GET", QUERY_PATHS["goals"])
        goal = resolve_one(goals, goal_target, "title", "goal")
        substep = resolve_one(
            flatten_substeps(goals), substep_target, "title", "substep"
        )
        payload = {"goal_id": goal["id"], "substep_id": substep["id"]}

    if operation == "pins-update":
        goals = client.request("GET", QUERY_PATHS["goals"])
        skills = client.request("GET", QUERY_PATHS["softskills"])["skills"]
        payload["pinned_substeps"] = [
            (
                item
                if isinstance(item, int)
                else resolve_one(
                    flatten_substeps(goals), item, "title", "substep"
                )["id"]
            )
            for item in payload.get("pinned_substeps", [])
        ]
        payload["pinned_softskills"] = [
            (
                item
                if any(skill["id"] == item for skill in skills)
                else resolve_one(skills, item, "name", "softskill")["id"]
            )
            for item in payload.get("pinned_softskills", [])
        ]

    if operation in {"reward-create", "reward-update"}:
        goal_target = payload.pop("required_goal", None)
        if goal_target:
            goal = resolve_one(
                client.request("GET", QUERY_PATHS["goals"]),
                goal_target,
                "title",
                "goal",
            )
            payload["required_goal_id"] = goal["id"]
        softskill_target = payload.pop("required_softskill", None)
        if softskill_target:
            skills = client.request("GET", QUERY_PATHS["softskills"])[
                "skills"
            ]
            skill = resolve_one(
                skills, softskill_target, "name", "softskill"
            )
            payload["required_softskill_id"] = skill["id"]

    if operation.endswith("-delete"):
        payload = None
    return method, path_template, payload, inspect_resource


def inspect_state(client, resource):
    return client.request("GET", QUERY_PATHS[resource])


def prepare_plan_data(operation, data):
    prepared = dict(data)
    if operation in {
        "softskill-branch-create",
        "softskill-branch-with-skills",
    }:
        branch_name = prepared.pop("name", None)
        key = prepared.get("key") or slugify(branch_name or "")
        if not key:
            raise HabitCtlError("A branch key or name is required.")
        prepared["key"] = key
        color, pale_color = branch_colors(key)
        prepared.setdefault("color", color)
        prepared.setdefault("pale_color", pale_color)

        if operation == "softskill-branch-with-skills":
            raw_skills = prepared.get("skills")
            if not isinstance(raw_skills, list) or not raw_skills:
                raise HabitCtlError("A non-empty 'skills' list is required.")
            normalized_skills = []
            for raw_skill in raw_skills:
                if isinstance(raw_skill, str):
                    skill = {"name": raw_skill}
                elif isinstance(raw_skill, dict):
                    skill = dict(raw_skill)
                else:
                    raise HabitCtlError(
                        "Each skill must be a name or an object."
                    )
                name = skill.get("name")
                if not name:
                    raise HabitCtlError("Each skill requires a name.")
                skill.setdefault("id", slugify(name))
                skill["branch"] = key
                skill.setdefault("description", "")
                skill.setdefault("prerequisites", [])
                skill.setdefault("related", [])
                skill.setdefault("execution_order", 1)
                normalized_skills.append(skill)
            prepared["skills"] = normalized_skills

    if operation == "softskill-create":
        name = prepared.get("name")
        if not name:
            raise HabitCtlError("A softskill name is required.")
        prepared.setdefault("id", slugify(name))
        prepared.setdefault("description", "")
        prepared.setdefault("prerequisites", [])
        prepared.setdefault("related", [])
        prepared.setdefault("execution_order", 1)
    return prepared


def plan_path(plan_id):
    return state_dir() / "plans" / f"{plan_id}.json"


def write_plan(plan):
    path = plan_path(plan["plan_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def read_plan(plan_id):
    path = plan_path(plan_id)
    if not path.exists():
        raise HabitCtlError(f"Unknown plan: {plan_id}")
    plan = json.loads(path.read_text(encoding="utf-8"))
    created_at = dt.datetime.fromisoformat(plan["created_at"])
    if dt.datetime.now(dt.timezone.utc) - created_at > dt.timedelta(
        seconds=PLAN_TTL_SECONDS
    ):
        raise HabitCtlError("The plan expired. Create a new plan.")
    return plan


def command_plan(args):
    client, config, user = configured_client()
    data = prepare_plan_data(
        args.operation, load_json_argument(args.data)
    )
    method, path, payload, inspect_resource = operation_request(
        client, args.operation, data
    )
    state = inspect_state(client, inspect_resource)
    plan_id = str(uuid.uuid4())
    now = dt.datetime.now(dt.timezone.utc)
    plan = {
        "plan_id": plan_id,
        "operation": args.operation,
        "method": method,
        "path": path,
        "payload": payload,
        "inspect_resource": inspect_resource,
        "state_hash": stable_hash(state),
        "idempotency_key": f"habitctl-{uuid.uuid4()}",
        "created_at": now.isoformat(),
        "expires_at": (
            now + dt.timedelta(seconds=PLAN_TTL_SECONDS)
        ).isoformat(),
        "base_url": config["base_url"],
        "user_id": user["id"],
        "username": user["username"],
        "status": "planned",
    }
    write_plan(plan)
    return {
        "status": "confirmation_required",
        "plan_id": plan_id,
        "expires_at": plan["expires_at"],
        "operation": args.operation,
        "request": {"method": method, "path": path, "payload": payload},
    }


def command_apply(args):
    plan = read_plan(args.plan_id)
    if plan["status"] == "applied":
        return {
            "status": "already_applied",
            "plan_id": plan["plan_id"],
            "idempotency_key": plan["idempotency_key"],
            "result": plan.get("result"),
        }
    if plan["status"] == "ambiguous":
        raise HabitCtlError(
            "This plan has an ambiguous outcome. Use recover with its "
            "idempotency key."
        )
    client, config, user = configured_client()
    if config["base_url"] != plan["base_url"] or user["id"] != plan["user_id"]:
        raise HabitCtlError("The configured target changed since planning.")
    current_state = inspect_state(client, plan["inspect_resource"])
    if stable_hash(current_state) != plan["state_hash"]:
        raise HabitCtlError(
            "The remote state changed since planning. Create a new plan."
        )
    try:
        result = client.request(
            plan["method"],
            plan["path"],
            payload=plan["payload"],
            idempotency_key=plan["idempotency_key"],
        )
    except AmbiguousWrite:
        plan["status"] = "ambiguous"
        write_plan(plan)
        return {
            "status": "ambiguous",
            "plan_id": plan["plan_id"],
            "idempotency_key": plan["idempotency_key"],
            "recovery": f"recover {plan['idempotency_key']}",
        }
    verified_state = inspect_state(client, plan["inspect_resource"])
    plan["status"] = "applied"
    plan["result"] = result
    plan["verified_state_hash"] = stable_hash(verified_state)
    write_plan(plan)
    return {
        "status": "applied",
        "plan_id": plan["plan_id"],
        "idempotency_key": plan["idempotency_key"],
        "result": result,
    }


def command_recover(args):
    client, _config, _user = configured_client()
    return client.request(
        "GET", f"/api/v1/remote-operations/{args.idempotency_key}"
    )


def build_parser():
    parser = argparse.ArgumentParser(prog="habitctl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser("configure")
    configure.add_argument("--base-url", default=DEFAULT_BASE_URL)
    configure.add_argument("--username", required=True)
    configure.add_argument("--api-token", required=True)
    configure.set_defaults(handler=command_configure)

    doctor = subparsers.add_parser("doctor")
    doctor.set_defaults(handler=command_doctor)

    query = subparsers.add_parser("query")
    query.add_argument(
        "resource", choices=sorted([*QUERY_PATHS, "habit-calendar"])
    )
    query.add_argument("--name")
    query.add_argument("--year", type=int, default=dt.date.today().year)
    query.add_argument("--month", type=int, default=dt.date.today().month)
    query.add_argument("--date", help="YYYY-MM-DD, for the agenda resource")
    query.set_defaults(handler=command_query)

    action = subparsers.add_parser("act")
    action.add_argument(
        "action",
        choices=[
            "habit-done",
            "habit-log",
            "habit-skip",
            "todo-complete",
            "notodo-fail",
            "substep-complete",
            "softskill-complete",
            "softskill-reset",
            "reward-purchase",
            "template-set",
        ],
    )
    action.add_argument("--target", required=True)
    action.add_argument("--amount", type=int)
    action.add_argument("--reason")
    action.set_defaults(handler=command_act)

    plan = subparsers.add_parser("plan")
    plan.add_argument("operation", choices=sorted(PLAN_OPERATIONS))
    plan.add_argument("--data", required=True)
    plan.set_defaults(handler=command_plan)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("plan_id")
    apply_parser.set_defaults(handler=command_apply)

    recover = subparsers.add_parser("recover")
    recover.add_argument("idempotency_key")
    recover.set_defaults(handler=command_recover)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        emit(args.handler(args))
    except ApiError as exc:
        emit(api_error_payload(exc), 2)
    except HabitCtlError as exc:
        emit({"status": "error", "error": str(exc)}, 2)


if __name__ == "__main__":
    main()
