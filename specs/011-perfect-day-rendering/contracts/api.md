# API Contracts: Perfect Day Rendering

**Feature**: 011-perfect-day-rendering | **Date**: 2026-06-28 | **Base path**: `/api/v1`

## Biological Zones CRUD

### GET /biological-zones

List all biological zones for the authenticated user.

**Headers**: `X-User-ID: <int>`

**Response** (200):
```json
[
  {
    "id": 1,
    "zone_name": "Focus Profond Matin",
    "zone_type": "deep_focus",
    "start_time": "08:00",
    "end_time": "12:00",
    "color": null,
    "display_order": 1
  },
  {
    "id": 2,
    "zone_name": "Pic Physique",
    "zone_type": "physical_peak",
    "start_time": "14:00",
    "end_time": "17:00",
    "color": null,
    "display_order": 2
  }
]
```

**Notes**: Results are ordered by `start_time` ascending. Overnight zones (start > end) sort by their start time.

---

### POST /biological-zones

Create a new biological zone.

**Headers**: `X-User-ID: <int>`

**Request body**:
```json
{
  "zone_name": "Zone Créative",
  "zone_type": "creative",
  "start_time": "20:00",
  "end_time": "22:00",
  "color": "#eab308",
  "display_order": 4
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `zone_name` | string | yes | — | Non-empty |
| `zone_type` | string | yes | — | One of: `deep_focus`, `physical_peak`, `creative`, `rest`, `social`, `sleep` |
| `start_time` | string | yes | — | "HH:MM" (00:00–23:59) |
| `end_time` | string | yes | — | "HH:MM" (00:00–23:59) |
| `color` | string | no | null | Hex color (e.g., "#8b5cf6") |
| `display_order` | int | no | 0 | Non-negative integer |

**Response** (201):
```json
{
  "id": 5,
  "zone_name": "Zone Créative",
  "zone_type": "creative",
  "start_time": "20:00",
  "end_time": "22:00",
  "color": "#eab308",
  "display_order": 4
}
```

**Error** (422 — overlap detected):
```json
{
  "detail": "Ce créneau chevauche la zone \"Focus Profond Matin\" (08:00 – 12:00)."
}
```

**Error** (422 — invalid zone_type):
```json
{
  "detail": "Type de zone invalide. Valeurs acceptées : deep_focus, physical_peak, creative, rest, social, sleep."
}
```

---

### PUT /biological-zones/{zone_id}

Update an existing biological zone.

**Headers**: `X-User-ID: <int>`

**Request body**: Same schema as POST (all fields optional for partial update).

**Response** (200): Updated zone object.

**Error** (404): `{ "detail": "Zone introuvable." }`

**Error** (422): Overlap or validation error (same format as POST).

---

### DELETE /biological-zones/{zone_id}

Delete a biological zone.

**Headers**: `X-User-ID: <int>`

**Response** (200):
```json
{
  "status": "deleted",
  "id": 5
}
```

**Error** (404): `{ "detail": "Zone introuvable." }`

---

## Existing Endpoints (consumed read-only)

### GET /templates

Returns template configurations including `agenda_json` for the left recap panel. No changes needed.

### GET /profile/status

Returns the active template name for determining which template's blocks to display. No changes needed.
