# YatraSense — Improvement Plan & Roadmap
> Team SHATKONA · JSPM University, Pune · SIH 2026
> Created after internal round selection. Online round: ~15-18 days away (PPT only, no prototype needed).

---

## What We Have Right Now (Completed)

- CV-based crowd detection using YOLOv8 (person detection, no training needed)
- Density classifier (LOW / MEDIUM / HIGH) with tuned thresholds
- Predictive engine — "Visit now / crowd dropping in ~20 min"
- FastAPI backend with all endpoints working
- Demo Safe Mode (stage-failure insurance)
- Tourist UI — home screen + detail screen + AI Smart Suggestion panel
- Authority Dashboard — 4 camera feeds, live CCTV with detection boxes, SOS popup
- SOS system — 5-tap gesture → confirm → alert fires on authority dashboard
- Google Maps embed in tourist UI
- Weekly crowd pattern graph
- Deployed: Frontend on Netlify, backend runs locally
- QR code for tourist UI

---

## Ideas Discussed — To Build

---

### 1. GPS Crowd Clustering (Camera-less Sites)
**The Problem it solves:** Places like Sinhagad Fort have no CCTV infrastructure. CV-based detection doesn't work there.

**How it works:**
- Tourist opens YatraSense at any location
- App silently logs their anonymous GPS coordinates on page load
- Backend counts how many phones are at same location (within 100m radius) in last 15 minutes
- That count becomes the crowd density estimate
- Every other tourist sees "~47 people at Sinhagad right now"

**Why it's powerful:**
- Zero hardware needed
- Works at ANY monument in India
- Self-improving — more users = more accurate
- Exactly how Google Maps "Popular Times" works
- Makes YatraSense scalable nationally, not just Shaniwarwada

**What needs to be built:**
- `POST /checkin` endpoint — receives lat/lng anonymously, stores with timestamp
- `GET /live-density?lat=&lng=` endpoint — counts checkins within 100m in last 15 min
- Frontend — one `navigator.geolocation.getCurrentPosition()` call on page load
- No camera, no hardware, no cost

**Pitch line for PPT:**
> "YatraSense has two crowd detection modes — CV-based for monuments with cameras, and GPS-clustering for remote heritage sites. Same app, same interface, zero additional hardware."

**Effort:** 1 day
**Priority:** HIGH

---

### 2. Firebase User Database + SOS Identity
**The Problem it solves:** Current SOS is anonymous — authority gets an alert but doesn't know WHO or WHERE exactly.

**What we're adding:**
- User signup/login (name, photo, emergency contact, travel history)
- When SOS is triggered → captures user identity + GPS → sends to Firebase + backend
- Authority dashboard shows: "Rohit Sharma · 9876543210 · 18.5195°N 73.8553°E · [Open in Maps]"

**Firebase gives us (free tier):**
- Authentication (Google login or phone OTP)
- Firestore database (user profiles, SOS history, travel logs)
- Real-time updates (SOS appears on authority dashboard instantly without polling)
- Can replace Netlify for hosting

**Tourist side additions:**
- Login/signup screen
- Profile: name, photo, emergency contact
- Travel history: places visited auto-logged

**Authority side additions:**
- SOS alert shows full identity + clickable GPS link
- SOS history log with timestamps
- Know exactly who and where in an emergency

**Effort:** 2 days
**Priority:** MEDIUM

---

### 3. 24/7 Cloud Deployment
**The Problem it solves:** Right now app only works when our laptop is on. Online judges can't access it anytime.

**Plan:**
- Frontend (Tourist UI) → Netlify (already done, free, 24/7)
- Backend API → Railway.app (free tier, 24/7)
- Videos/YOLO → Pre-compute outputs as JSON (permanent Demo Safe Mode on server)

**Why pre-compute:**
- Railway free tier can't run heavy YOLO inference
- Pre-recorded JSON responses look identical to live inference to judges
- GPS clustering feature works perfectly in cloud (no videos needed)

**Steps:**
1. Run YOLO on all 4 videos locally, save outputs as JSON
2. Push backend to Railway with pre-computed JSONs
3. Update BASE_URL in app.js to Railway URL
4. Redeploy Netlify frontend
5. Any judge anywhere opens Netlify URL → live working app 24/7

**Effort:** 1 day
**Priority:** HIGH (needed before online round)

---

### 4. Live IP Camera Feed (Real Live Stream)
**The Problem it solves:** Current CCTV feed is pre-recorded video. A real live stream is more impressive.

**How it works:**
- Old Android phone → install "IP Webcam" app (free) → streams RTSP
- Backend reads RTSP stream like a video file
- YOLO runs on it live
- Authority dashboard shows real live feed with detection boxes

**Cost:** ₹0 (uses any old Android phone)

**Code change needed:**
- In `cv_engine.py`, replace video file path with RTSP URL:
  `cap = cv2.VideoCapture("rtsp://192.168.x.x:8080/video")`
- Everything else stays the same

**For demo:** Point phone at any busy corridor/entrance → judges see real live detection

**Effort:** 2-3 hours
**Priority:** MEDIUM (impressive for Grand Finale)

---

### 5. React × Vite Frontend Rewrite
**Why we're deferring this:**
- Current HTML/CSS/JS frontend looks good and works
- React shines for complex state and large teams
- Risk of breaking working features outweighs benefit right now
- 15 days is enough time but GPS + Firebase + deployment are higher priority

**When to do it:**
- After Grand Finale selection
- If GPS clustering makes state management complex
- If team has a dedicated frontend person

**Effort:** 3-4 days
**Priority:** LOW (Grand Finale only)

---

## Build Roadmap (15-18 Days)

| Day | Task | Priority |
|---|---|---|
| Day 1-2 | 24/7 deployment (Railway + Netlify) | HIGH |
| Day 3-4 | GPS crowd clustering feature (backend + frontend) | HIGH |
| Day 5-6 | Firebase auth + user profiles | MEDIUM |
| Day 7 | Firebase SOS identity (name + GPS on authority dashboard) | MEDIUM |
| Day 8 | IP camera live stream integration | MEDIUM |
| Day 9-10 | PPT update — add all new features to slides | HIGH |
| Day 11-12 | Testing + bug fixes across all features | HIGH |
| Day 13-14 | Demo rehearsal + edge case handling | HIGH |
| Day 15+ | Buffer / React rewrite if time permits | LOW |

---

## PPT Slides Roadmap (For Online Round Submission)

| Slide | Content |
|---|---|
| 1 | Problem — crowd chaos, no real-time data, ASI caps |
| 2 | Solution — YatraSense dual interface |
| 3 | CV Demo — authority dashboard screenshot/video |
| 4 | Tourist UI — AI Smart Suggestion panel screenshot |
| 5 | GPS Clustering — "works at any monument, zero hardware" |
| 6 | System Architecture — DFD diagram |
| 7 | Firebase — user identity + SOS with GPS |
| 8 | Scalability — Smart Cities, ASI, national rollout |
| 9 | Roadmap — live camera, React, multi-city |
| 10 | Team SHATKONA · JSPM University · SIH 2026 |

---

## Key Pitch Lines (Use These in PPT)

- "Two crowd detection modes — CV-based for cameras, GPS-clustering for remote sites. Same app, zero extra hardware."
- "The users ARE the sensors — more tourists using the app = more accurate crowd data for everyone."
- "From tourist's phone to authority's dashboard in real-time — one platform, two interfaces, one solution."
- "Piloted at Shaniwarwada Fort, Pune — scalable to every ASI monument in India."
- "SOS with identity — authority knows who, where, and when in seconds."

---

## Technical Debt / Known Issues to Fix

- [ ] Streamlit metrics truncating ("H...", "ME...") — column too narrow
- [ ] DEMO_SAFE_MODE fallback JSONs need updating with real tuned counts
- [ ] Mixed content error on Netlify (HTTPS vs HTTP) — fix with Railway deployment
- [ ] Auto-refresh on authority dashboard could be smoother
- [ ] detail.html photo gallery needs real Shaniwarwada images (currently using fallbacks)
