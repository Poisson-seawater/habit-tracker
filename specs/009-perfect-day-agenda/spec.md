# Spec - Perfect Day Agenda

This document specifies the technical design, product vision, and database changes required to implement the "Perfect Day Agenda" feature in the Habit RPG Tracker.

---

## 1. Product Vision & User Story

As a user, I want to define a typical daily agenda (timeline/schedule) for each of my 4 Perfect Day templates (`week`, `weekend`, `recup`, `malade`).
This allows me to:
- Structure my days according to the context (e.g. intense coding on workdays, active rest on recovery days).
- Map specific time blocks to the RPG stats required to validate the Perfect Day (e.g. a "Morning Run" block maps to "Force" or "Santé").
- Visualize my ideal day as a color-coded timeline.
- Verify if my planned schedule has enough activities to meet the minimum stat thresholds required for a Perfect Day.

---

## 2. UI / UX Specifications (Mockup Details)

The mockup will demonstrate the following interface components, fully styled with the app's premium dark glassmorphism design:

1. **Template Switcher Tabs**:
   - Buttons to switch between **Semaine (Week) ⚔️**, **Weekend 💤**, **Récupération 🩹**, and **Malade 🤒**.

2. **24-Hour Visual Timeline**:
   - A horizontal color-coded bar representing the 24 hours of the day (00:00 to 23:59).
   - Shows block spans proportionally. Hovering displays details.

3. **Planned Blocks List**:
   - A chronologically ordered card list of all planned blocks for the current day template.
   - Each card displays:
     - Time range (e.g., `08:00 - 10:00`).
     - Activity Name (e.g., `Focus Code / deep work`).
     - Related RPG Stat and points contribution (e.g., `📖 Apprendre (+3 pts)`).
     - Focus Level tag (e.g., `Focus`, `Routine`, `Relax`, `Sommeil`).
     - "Delete" button.

4. **Block Editor / Creator Form**:
   - Allows users to add a new typical time block:
     - **Title**: String name of the activity.
     - **Time Range**: Start hour/minute to End hour/minute.
     - **RPG Stat**: Select which stat this activity supports.
     - **Points**: Point value this block contributes (for comparison against template thresholds).
     - **Type**: Focus/Routine/Relax/Sommeil.
   - Overlap check: flags time slots that conflict.

5. **Stat Validation Checklist**:
   - Compares the sum of stat points in the planned typical agenda blocks against the selected template's thresholds.
   - Displays indicators:
     - Green check (✅) if the agenda meets the template threshold.
     - Red circle (⭕) if the agenda falls short, helping the user adjust their schedule or thresholds.

---

## 3. Database Schema Recommendations

To store these typical agendas, we recommend introducing a new table `perfect_day_agendas` or modifying the existing `perfect_day_templates` table.

### Option A: Modifying `perfect_day_templates`
We can add an `agenda_json` column to the `perfect_day_templates` table:
```python
class PerfectDayTemplate(Base):
    __tablename__ = "perfect_day_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String, nullable=False)  # "week", "weekend", "recup", "malade"
    thresholds_json = Column(JSON, nullable=False)  # e.g., {"force": 16, "sante": 8}
    agenda_json = Column(JSON, nullable=True)  # List of blocks, e.g.:
    # [
    #   {"start": "08:00", "end": "10:00", "title": "Focus Work", "stat": "apprendre", "points": 5, "type": "focus"},
    #   {"start": "12:00", "end": "13:00", "title": "Lunch", "stat": "sante", "points": 2, "type": "relax"}
    # ]
```

### Option B: A New `PerfectDayAgendaBlock` Table
For more relational integrity:
```python
class PerfectDayAgendaBlock(Base):
    __tablename__ = "perfect_day_agenda_blocks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String, nullable=False)  # "week", "weekend", "recup", "malade"
    title = Column(String, nullable=False)
    start_time = Column(String, nullable=False)  # "HH:MM"
    end_time = Column(String, nullable=False)  # "HH:MM"
    associated_stat = Column(String, nullable=True)  # e.g. "discipline", "force"
    points = Column(Integer, default=0)
    category = Column(String, default="routine")  # "focus", "routine", "relax", "sommeil"
```

---

## 4. API Endpoints Contract (Draft)

When implementing the backend, these routes should be introduced:

### `GET /api/v1/perfect-days/templates/{template_name}/agenda`
Returns the list of typical agenda blocks for a specific template.
*Response (200 OK):*
```json
[
  {
    "id": 12,
    "title": "Morning Cardio",
    "start_time": "07:00",
    "end_time": "08:00",
    "associated_stat": "force",
    "points": 4,
    "category": "routine"
  }
]
```

### `POST /api/v1/perfect-days/templates/{template_name}/agenda`
Adds a new block to the template's typical agenda.
*Payload:*
```json
{
  "title": "Deep Work",
  "start_time": "08:30",
  "end_time": "12:00",
  "associated_stat": "apprendre",
  "points": 6,
  "category": "focus"
}
```

### `DELETE /api/v1/perfect-days/templates/{template_name}/agenda/{block_id}`
Deletes a specific block.
