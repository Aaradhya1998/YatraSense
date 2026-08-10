# [Project Name TBD] — Crowd Intelligence Platform for Heritage Tourism

A dual-interface system that helps tourists know the best time to visit a monument, and helps site authorities monitor and respond to crowd density in real time — piloted at Shaniwarwada Fort, Pune.

Built for Smart India Hackathon (internal college round). Solo-built with limited teammate support under a 10-day timeline.

## Problem

Tourists have no real-time visibility into monument hours, crowd density, or the best time to visit. Site authorities have no real-time crowd-monitoring tools and resort to blunt, reactive measures (e.g., blanket visitor caps) instead of proactive management. See `PRD.md` for full problem framing.

## What it does

- **Tourist dashboard**: monument hours, ticket/parking prices, current crowd status, and a "best time to visit" recommendation.
- **Authority dashboard**: real-time crowd density (Low/Medium/High) estimated from a video feed via computer vision, with automatic alerts when density crosses a threshold.
- **Predictive layer**: forecasts near-term crowd levels by combining the live crowd trend with historical time-of-day/day-of-week patterns.

## Tech Stack

- Python 3.11+
- OpenCV + Ultralytics YOLOv8 (person detection)
- scikit-learn (predictive layer)
- FastAPI (backend)
- Streamlit (both dashboards)
- JSON/CSV or SQLite (data storage)

Full technical spec: see `PRD.md`. Full data flow: see `DFD_Level0_Context.mermaid` and `DFD_Level1_Detailed.mermaid`.

## Project Structure

```
project/
├── backend/
│   ├── main.py                  # FastAPI app, route definitions
│   ├── cv_engine.py             # video -> person count pipeline
│   ├── density_classifier.py    # count -> Low/Medium/High
│   ├── predictive_engine.py     # trend + historical pattern -> forecast
│   ├── alert_service.py         # threshold check -> alert state
│   └── models/
│       └── yolov8n.pt           # pretrained weights
├── data/
│   ├── monument_info.json       # hours, tickets, parking (curated)
│   ├── historical_pattern.csv   # synthetic day/hour crowd pattern
│   └── sample_videos/
│       ├── low_crowd.mp4
│       └── high_crowd.mp4
├── frontend/
│   ├── tourist_view.py          # Streamlit page 1
│   └── authority_dashboard.py   # Streamlit page 2
├── requirements.txt
├── PRD.md
├── DFD_Level0_Context.mermaid
├── DFD_Level1_Detailed.mermaid
└── README.md
```

## Setup

```bash
# clone / open the project directory
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` should include at minimum:
```
fastapi
uvicorn
opencv-python
ultralytics
scikit-learn
pandas
numpy
streamlit
```

## Running It

```bash
# Terminal 1 — start the backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — start the tourist dashboard
streamlit run frontend/tourist_view.py

# Terminal 3 — start the authority dashboard
streamlit run frontend/authority_dashboard.py
```

## Demo Script

1. Open the tourist dashboard — show monument info and current recommendation.
2. Start the CV engine on `low_crowd.mp4` — show density reads LOW, dashboards update.
3. Swap the input to `high_crowd.mp4` — show density climbs to HIGH, forecast updates, an alert fires on the authority dashboard in real time.
4. Close on the predictive forecast text ("likely HIGH in ~20 min") to highlight the differentiator beyond simple counting.

## Known Demo Simplifications (be upfront about these if asked)

- The "camera feed" is a pre-recorded sample video, not a live camera — framed in the pitch as a stand-in for a live entrance camera.
- The historical crowd pattern dataset is synthetically generated, not scraped real footfall data.
- No live GPS/routing, no multi-site itinerary planning, no real CCTV integration — see `PRD.md` Section 6 for the full out-of-scope list and roadmap items.

## Roadmap (not built in this phase)

- Multi-site trip planning across a city
- AI-based recognition of carvings/artifacts with contextual audio (e.g., instrument sounds tied to carved reliefs)
- Real CCTV/live camera integration
- Local business/food suggestions with a monetization layer
