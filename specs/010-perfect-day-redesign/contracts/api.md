# API Contracts: Perfect Day Redesign

This document outlines the API request and response contracts for the Perfect Day redesign.

---

## 1. Templates Endpoints

### `GET /api/v1/templates`
Retrieves the user's custom template configurations.

**Response (200 OK)**:
```json
{
  "rest": {
    "focus_hours": 2.0,
    "min_rest_hours": 10.0,
    "ceilings": {
      "musculaire": 1.0,
      "cerveau": 1.0,
      "emotionnel_social": 1.0,
      "creatif_divergent": 1.0,
      "total": 4.0
    }
  },
  "regular": {
    "focus_hours": 6.0,
    "min_rest_hours": 8.0,
    "ceilings": {
      "musculaire": 2.0,
      "cerveau": 2.0,
      "emotionnel_social": 2.0,
      "creatif_divergent": 2.0,
      "total": 8.0
    }
  },
  "hustle": {
    "focus_hours": 9.0,
    "min_rest_hours": 7.0,
    "ceilings": {
      "musculaire": 4.0,
      "cerveau": 4.0,
      "emotionnel_social": 4.0,
      "creatif_divergent": 4.0,
      "total": 10.0
    }
  }
}
```

---

### `POST /api/v1/templates`
Saves or updates custom template settings.

**Request Payload**:
```json
{
  "template_name": "regular",
  "focus_hours": 6.0,
  "min_rest_hours": 8.0,
  "ceilings": {
    "musculaire": 2.0,
    "cerveau": 2.0,
    "emotionnel_social": 2.0,
    "creatif_divergent": 2.0,
    "total": 8.0
  }
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "template_name": "regular"
}
```

---

## 2. Habits (Quests) Endpoints

### `GET /api/v1/habits`
Returns the user's active habits including the new effort metrics.

**Response (200 OK)**:
```json
[
  {
    "id": 1,
    "name": "lecture",
    "description": "Lire 20 pages",
    "type": "quantitative",
    "frequency": "daily",
    "scheduled_days": "0,1,2,3,4,5,6",
    "reminder_time": "21:00",
    "is_private": false,
    "is_reportable": true,
    "is_mandatory": false,
    "point_rewards": {},
    "daily_cap": 8,
    "daily_target": 1,
    "unit": "pages",
    "is_active": true,
    "effort_type": "cerveau",
    "effort_duration": 1.5
  }
]
```

---

### `POST /api/v1/habits` & `PUT /api/v1/habits/{id}`
Create or update a habit.

**Request Payload**:
```json
{
  "name": "lecture",
  "description": "Lire 20 pages",
  "type": "quantitative",
  "frequency": "daily",
  "scheduled_days": "0,1,2,3,4,5,6",
  "reminder_time": "21:00",
  "is_private": false,
  "is_reportable": true,
  "is_mandatory": false,
  "point_rewards": {},
  "daily_cap": 8,
  "daily_target": 1,
  "unit": "pages",
  "effort_type": "cerveau",
  "effort_duration": 1.5
}
```

---

## 3. Sub-steps Endpoints

### `POST /api/v1/goals/{goal_id}/substeps` & `PUT /api/v1/substeps/{substep_id}`
Create or update a sub-step.

**Request Payload**:
```json
{
  "title": "Acheter un livre",
  "description": "Visiter la librairie locale",
  "gold_reward": 50,
  "stats_json": [],
  "execution_order": 1,
  "is_life_lore": false,
  "effort_type": "emotionnel_social",
  "effort_duration": 1.0
}
```
