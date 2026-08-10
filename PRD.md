# Product Requirements Document
**Project type:** Smart India Hackathon — internal college round | 10-day solo build with limited teammate support
**Name:** TBD (not finalized — do not hardcode any project name into code, configs, or UI strings; use a placeholder constant instead)

---

## 1. Problem Statement

Tourists visiting historical and cultural monuments in India often lack real-time visibility into visiting hours, current crowd density, and the best time to visit — resulting in long queues, poor visit experiences, and unintentional contribution to overcrowding. Site authorities lack real-time crowd-monitoring tools and rely on reactive, blunt measures (e.g., blanket visitor caps) rather than proactive, data-driven crowd management. There is currently no unified system connecting tourist-side planning with authority-side real-time monitoring.

## 2. Solution Overview

A dual-interface crowd intelligence system, piloted at a single monument (Shaniwarwada Fort, Pune), consisting of:
1. A **tourist-facing interface**: static monument info + a recommendation engine for best visiting time + live crowd status.
2. An **authority-facing interface**: a real-time dashboard showing crowd density (estimated via computer vision on a camera feed) with threshold-based alerts.
3. A **predictive layer** connecting both: forecasts near-term crowd levels by combining live crowd trend with historical time-of-day/day-of-week patterns.

## 3. Users & User Stories

**Persona A — Tourist**
- As a tourist, I want to see a monument's hours, ticket price, and parking info so I can plan my visit.
- As a tourist, I want to know the best day/time to visit so I avoid long queues.
- As a tourist, I want to see current crowd status before I leave, so I can decide whether to go now or later.

**Persona B — Site Authority / Staff**
- As site staff, I want a live view of current crowd density so I can judge whether intervention is needed.
- As site staff, I want to be alerted automatically when density crosses a safety/comfort threshold, so I don't have to constantly watch a screen.
- As site staff, I want a short-term forecast (not just current state) so I can act proactively rather than reactively.

## 4. Functional Requirements

| ID | Requirement |
|---|---|
| FR1 | System shall display static monument info (name, location, opening/closing hours, ticket price, parking price) |
| FR2 | System shall estimate person count from a video feed using a person-detection model |
| FR3 | System shall classify current crowd density into Low / Medium / High based on estimated count |
| FR4 | System shall maintain a historical crowd pattern dataset keyed by day-of-week and hour-of-day |
| FR5 | System shall generate a short-term forecast (next ~20-30 min) combining live trend and historical pattern |
| FR6 | System shall trigger an alert event when density crosses from a lower state to High |
| FR7 | Tourist interface shall display: static info, current density, and a "best time to visit" recommendation |
| FR8 | Authority interface shall display: current density, forecast, and a list of active/recent alerts |
| FR9 | System shall allow swapping which sample video represents the "current" feed, to demonstrate state transitions (Low↔High) live |

## 5. Non-Functional Requirements

- Runs fully on a local laptop (CPU only, no GPU dependency required) — model choice (YOLOv8n) must reflect this.
- No live camera hardware integration required — video input is a pre-recorded file simulating a live feed. This must be clearly documented as a demo simplification, not represented as production-ready live ingestion.
- No user authentication/login required for this build phase.
- No persistent multi-user database required — flat files or SQLite are sufficient.

## 6. Explicitly Out of Scope (do not build; roadmap only)

- Multi-site trip planning / multi-day itinerary generation
- Local food/restaurant suggestions or ad-based monetization
- AI-based carving/landmark image recognition ("scan a carving to learn about it")
- Real live CCTV/camera hardware integration
- Standalone emergency SOS feature (safety alerting is folded into the authority alert system only, not a separate tourist-facing panic button)
- Any real historical footfall dataset — the historical pattern dataset used in this build is synthetic and must be labeled as illustrative wherever displayed or logged

## 7. System Architecture

```
[Sample Video File]
      |
      v
[CV Engine: person detection] --count--> [Density Classifier: Low/Med/High]
                                                |              |
                                                v              v
                                    [Predictive Engine]   [Alert Service]
                                    (trend + historical)   (threshold check)
                                                |              |
                                                v              v
                                          [FastAPI Backend]
                                          /monument-info
                                          /crowd-status
                                          /alerts
                                                |
                              -------------------------------------
                              |                                   |
                              v                                   v
                     [Tourist Dashboard]                [Authority Dashboard]
                     (Streamlit)                          (Streamlit)
```

See accompanying files `DFD_Level0_Context.mermaid` (external entities and data flows in/out of the system) and `DFD_Level1_Detailed.mermaid` (internal process breakdown with labeled data flows D1-D9) for the full data flow diagram.

## 8. Data Dictionary (referenced by DFD flows D1-D9)

| Flow ID | Data | Format | Producer → Consumer |
|---|---|---|---|
| D1 | person_count | integer, per sampled frame | CV Engine → Density Classifier |
| D2 | density_label, rolling_count | enum {LOW, MEDIUM, HIGH}, integer | Density Classifier → Predictive Engine, Alert Service |
| D3 | expected_density | lookup by (day_of_week, hour) | historical_pattern.csv → Predictive Engine |
| D4 | forecast_label, forecast_text | enum + string, e.g. "HIGH in ~20 min" | Predictive Engine → Backend |
| D5 | alert_event | {timestamp, message, density_at_trigger} | Alert Service → Backend |
| D6 | monument static data | JSON object (see schema below) | monument_info.json → Backend |
| D7 | monument info response | JSON | Backend → Tourist Dashboard |
| D8 | crowd status response | JSON {current_density, forecast} | Backend → Tourist Dashboard, Authority Dashboard |
| D9 | alerts response | JSON array of alert objects | Backend → Authority Dashboard |

## 9. Data Schemas

**`monument_info.json`**
```json
{
  "name": "string",
  "location": {"lat": 0.0, "lng": 0.0},
  "hours": {"open": "HH:MM", "close": "HH:MM"},
  "ticket_price": {"indian": 0, "foreign": 0, "currency": "INR"},
  "parking_price": 0
}
```

**`historical_pattern.csv`** columns: `day_of_week` (Mon-Sun), `hour` (0-23), `expected_density` (LOW/MEDIUM/HIGH)
*Note: this file is synthetically generated for demo purposes, not scraped real data.*

**API response — `GET /crowd-status`**
```json
{
  "current_density": "MEDIUM",
  "person_count_estimate": 18,
  "forecast": {
    "label": "HIGH",
    "text": "Likely to reach HIGH in ~20 minutes",
    "eta_minutes": 20
  }
}
```

**API response — `GET /alerts`**
```json
[
  {"timestamp": "2026-08-10T14:32:00", "message": "Density crossed into HIGH", "density_at_trigger": "HIGH"}
]
```

## 10. Algorithm Specifications

**Density classification (P2):** Fixed thresholds on rolling-average person count.
- `count < 10` → LOW
- `10 <= count <= 25` → MEDIUM
- `count > 25` → HIGH
*(Thresholds must be tuned against the actual sample videos used — do not assume these numbers are final; validate against real detection output before demo.)*

**Predictive forecast (P3):** Weighted combination of live trend and historical pattern.
```
trend_slope = (latest_count - count_N_readings_ago) / N
historical_component = expected_density_for(current_day, current_hour)  # mapped to numeric scale
forecast_score = (0.6 * trend_slope) + (0.4 * historical_component)
forecast_label = map forecast_score back to LOW/MEDIUM/HIGH
```
*(Weights 0.6/0.4 are a starting point — tune empirically against demo scenarios.)*

**Alert trigger (P4):** Fire an alert event only on a state transition into HIGH (i.e., previous state != HIGH and current state == HIGH) — do not fire repeatedly every frame while already in HIGH state.

## 11. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Computer Vision | OpenCV + Ultralytics YOLOv8 (`yolov8n.pt`, pretrained, `person` class only) |
| Predictive layer | scikit-learn `LinearRegression`, or a plain weighted heuristic (pandas/numpy) |
| Backend/API | FastAPI |
| Frontend | Streamlit (two pages: tourist view, authority dashboard) |
| Data storage | Flat files (JSON/CSV) or SQLite — no full RDBMS needed |
| Version control | Git |

## 12. Build Order / Milestones

1. CV Engine standalone — verify real person-count output against both sample videos before building anything downstream
2. Density Classifier — tune thresholds against real CV output from step 1
3. Historical pattern CSV (synthetic) + Predictive Engine
4. Alert Service + FastAPI routes wiring all of the above
5. Streamlit tourist view + authority dashboard consuming the API
6. End-to-end run: swap sample videos live to prove LOW↔HIGH transitions work correctly

## 13. Success Criteria for Demo

- Live run shows: (a) tourist recommendation output, (b) CV counter correctly classifying both sample videos differently, (c) an alert firing in real time on the authority dashboard when density crosses into HIGH.
- All demo simplifications (simulated feed, synthetic historical data) are disclosed proactively in the pitch, not discovered by judge questioning.
