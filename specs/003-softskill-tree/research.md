# Research & Technical Decisions: Softskill Progress Tree

This document details the architectural research and decisions made for the Softskill Progress Tree.

## 1. Frontend Visualization Strategy

### Context
We need to render a nodes-and-edges graph (skill tree) on a single web page in Vanilla JS. The tree must support:
- Absolute positioning of skills (coordinates X/Y).
- Visual grouping/branches differentiated by color.
- Connecting lines showing prerequisite dependencies and similarity links.
- Interactive clicking to open details.
- Lightweight foot-print (<500ms render, zero external dependencies).

### Decision
Use a **pure inline SVG container** integrated into the DOM combined with absolute-positioned HTML nodes.
- **Rationale**: 
  - Canvas requires redrawing everything on interaction.
  - Heavy JS libraries (D3, Cytoscape) add complexity and load overhead.
  - SVG is native, responsive, CSS-stylable, and allows drawing lines (`<line>` or `<path>` elements) between DOM elements easily.
- **Implementation**:
  - The tree container will be a relative-positioned `div` wrapper.
  - Inside, a single `<svg>` element will stretch to 100% width and height to draw connection lines between skills.
  - Skill nodes will be rendered as absolute-positioned HTML `button` elements over the SVG canvas, using coordinates defined in the static JSON configuration file.
  - Visual status changes (locked, unlocked, in-progress) will be styled purely via CSS class toggles on the node elements.

---

## 2. Skill Tree Definition & Configuration Format

### Context
The tree's visual layout, branch colors, connections, and skill metadata must be defined statically as per user clarification.

### Decision
Use a single static JSON configuration file: `backend/src/data/softskills_tree.json`.

### Schema Format
```json
{
  "branches": {
    "communication": {
      "color": "#e74c3c",
      "pale_color": "#fadbd8"
    },
    "productivity": {
      "color": "#3498db",
      "pale_color": "#ebf5fb"
    }
  },
  "skills": [
    {
      "id": "ecoute",
      "name": "Écoute Active",
      "description": "Capacité à écouter attentivement sans interrompre.",
      "branch": "communication",
      "prerequisites": [],
      "related": [],
      "x": 200,
      "y": 100
    },
    {
      "id": "vente",
      "name": "Vente & Persuasion",
      "description": "Capacité à convaincre et présenter de la valeur.",
      "branch": "communication",
      "prerequisites": ["ecoute"],
      "related": ["orateur"],
      "x": 200,
      "y": 250
    },
    {
      "id": "orateur",
      "name": "Art Oratoire",
      "description": "Prendre la parole en public de manière structurée.",
      "branch": "communication",
      "prerequisites": ["ecoute"],
      "related": ["vente"],
      "x": 400,
      "y": 250
    }
  ]
}
```

### Rationale
- JSON is natively supported by both Python (FastAPI) and JavaScript (Frontend).
- Separates structural design (tree layout) from user state, keeping database size tiny.
- A cyclic dependency check will be executed on backend startup to ensure configuration validity.

---

## 3. Database Persistence & Migration

### Context
We must persist:
1. User-specific progress (level, completed status).
2. User's custom success test sentence for each skill.

### Decision
Introduce a single table `user_softskill_progress` with manual migration `v3_softskills.sql` under `backend/src/database/migrations/`.

### Table Schema
```sql
CREATE TABLE IF NOT EXISTS user_softskill_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    softskill_id VARCHAR(100) NOT NULL,
    success_criteria_test TEXT,
    current_level INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, softskill_id)
);
```

### Rationale
- Mapping `user_id` and `softskill_id` as a unique constraint simplifies lookups and updates.
- Decouples static skill metadata (stored in JSON) from user state, respecting SQLite storage guidelines.
