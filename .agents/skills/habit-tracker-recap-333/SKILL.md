---
name: "habit-tracker-recap-333"
description: "Gère le tableau de bord Recap 3-3-3 (3 objectifs, 3 compétences, 3 activités d'allostasie) : épinglage, synchronisation avec la DB, navigation par focus, et rédemption en direct."
compatibility: "Habit Tracker MVP/V3/V4"
metadata:
  purpose: "Administering and interacting with the 3-3-3 Recap Dashboard Panel"
---

# Habit Tracker 3-3-3 Recap Panel

This skill documents the **3-3-3 Recap Panel** feature of Gabriel's Habit RPG Tracker. It allows a quick dashboard view of 3 goal sub-steps, 3 key softskills, and 3 active daily/weekly allostasis rewards, with direct check-ins and redirect navigation links.

---

## 🗄️ Database Schema (`users` updates)

Two columns were added to the `users` table to persist the IDs of pinned items:

| Column | Type | Description |
|---|---|---|
| `pinned_substeps` | TEXT | SQLite string storing JSON serialized list of pinned sub-step IDs (e.g. `[1, 3]`). Default `[]`. |
| `pinned_softskills` | TEXT | SQLite string storing JSON serialized list of pinned softskill IDs (e.g. `["ecoute_active"]`). Default `[]`. |

---

## 📡 REST API Routes

### 1. Retrieve Profile (including Pins)
- **Endpoint**: `GET /api/v1/profile`
- **Response fields**:
  - `pinned_substeps`: list of integers.
  - `pinned_softskills`: list of strings.

### 2. Save Pinned Items
- **Endpoint**: `PUT /api/v1/profile/pins`
- **Request payload**:
  ```json
  {
    "pinned_substeps": [1, 2, 3],
    "pinned_softskills": ["ecoute_active", "articulation_claire"]
  }
  ```
- **Constraints**:
  - The list of pinned sub-steps must contain at most 3 items.
  - The list of pinned softskills must contain at most 3 items.
- **Response**: `200 OK` with updated profile payload.

---

## 🎨 Frontend Stacking and Layout

### Card Placement & Structure
- The widget `#recap-3-3-3-panel` sits in the left column on the main page, directly above the character sheet.
- **Vertical Stack**: The three categories (*Objectifs*, *Compétences*, and *Allostasie*) are stacked vertically using flexbox rules:
  ```css
  .recap-grid {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
  }
  ```

### Interactive Functionality
1. **Goal Sub-step Click**: Redirects the user to the `Objectifs & Graphes` tab, scrolls the corresponding SVG tree node into center view, and triggers a flashing scale-up pulse animation (`pulse-highlight`).
2. **Softskill Click**: Redirects the user to the `Softskills` tab, scrolls the corresponding hexagonal node into view, and triggers the pulse animation.
3. **Allostasis claim**: Allows validation of daily/weekly items from the shop category directly inside the widget. If completed, it displays a green checkmark `✓ Fait`.

### Pin Selection Drawer
- Opening the drawer `#recap-pin-drawer` displays checkboxes for all incomplete items.
- Checkboxes are limited to a maximum of 3 selections per category via client-side event listeners disabling additional checkboxes.
