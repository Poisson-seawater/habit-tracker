# Quickstart: Perfect Day Rendering

**Feature**: 011-perfect-day-rendering | **Date**: 2026-06-28

## Prerequisites

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install dependencies (if needed)
uv pip install -r backend/requirements.txt
```

## Run the Application

```bash
# Start the API server
PYTHONPATH=backend python3 backend/src/main.py
# → http://localhost:5000

# The biological_zones table is auto-created on startup via _run_migrations()
# Default biological zones are seeded for existing users
```

## Test the Feature

### Automated Tests

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_biological_zones.py -v
```

### Manual API Testing

```bash
# List biological zones
curl -H "X-User-ID: 1" http://localhost:5000/api/v1/biological-zones

# Create a new zone
curl -X POST -H "X-User-ID: 1" -H "Content-Type: application/json" \
  -d '{"zone_name":"Test Zone","zone_type":"deep_focus","start_time":"08:00","end_time":"10:00"}' \
  http://localhost:5000/api/v1/biological-zones

# Update a zone
curl -X PUT -H "X-User-ID: 1" -H "Content-Type: application/json" \
  -d '{"zone_name":"Updated Zone","end_time":"11:00"}' \
  http://localhost:5000/api/v1/biological-zones/1

# Delete a zone
curl -X DELETE -H "X-User-ID: 1" http://localhost:5000/api/v1/biological-zones/1

# Test overlap detection (should return 422)
curl -X POST -H "X-User-ID: 1" -H "Content-Type: application/json" \
  -d '{"zone_name":"Overlap","zone_type":"rest","start_time":"09:00","end_time":"11:00"}' \
  http://localhost:5000/api/v1/biological-zones
```

### Dashboard Testing

1. Navigate to http://localhost:5000
2. Go to the **Perfect Day** tab → rendering view
3. Verify the biological timeline renders at the top with default zones
4. Verify the left panel shows activity blocks for the active template
5. Switch templates → left panel updates, bio timeline stays unchanged
6. Go to **Settings** → "Journée Biologique" section
7. Add/edit/delete zones and verify changes reflect on the rendering view

## Key Files

| File | Purpose |
|------|---------|
| `backend/src/database/models.py` | BiologicalZone model |
| `backend/src/database/seed.py` | Migration v18 + default zone seeding |
| `backend/src/api/routes.py` | CRUD endpoints |
| `backend/tests/test_biological_zones.py` | Unit tests |
| `frontend/js/app.js` | Rendering view + Settings UI |
| `frontend/css/style.css` | Timeline + layout styles |
