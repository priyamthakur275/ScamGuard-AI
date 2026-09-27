# ScamGuard verification

## Final production pass — 25 September 2026

This pass audited and fixed the existing application in place. No features
were added, the architecture was not changed, the model and registry files
were not touched, and no new runtime dependencies were added.

### Fixes in this pass

Backend
- `GET /messages/history` and admin `GET /users` now validate paging
  (`skip >= 0`, `1 <= limit <= 200`). A negative offset previously reached the
  database (an error on PostgreSQL) and page size was unbounded. Regression
  test added (`test_history_rejects_out_of_range_paging`).

Frontend — functional
- Report exports (scan and case, PDF/JSON/CSV) now use the same token refresh
  as every other request, so they keep working after the 15-minute access
  token expires. Object URLs are revoked after the download starts.
- A failed registration or CAPTCHA-protected login now loads a new challenge;
  previously a wrong or expired challenge stayed on screen.
- Case actions (status, note, unlink) refresh in place instead of replacing the
  page with a loading skeleton.
- History risk filter now filters the threat level the table displays
  (including Critical); single-scan delete asks for confirmation.
- Dashboard high-risk count, list and badges use one consistent definition;
  the capped list says "Showing 5 of N".
- Analytics counters settle on the exact formatted value and respect reduced
  motion; trend chart fetches only the 30 scans it plots; errors offer Retry.
- Production build no longer depends on reaching Google Fonts: IBM Plex is
  self-hosted from `frontend/src/app/fonts` (SIL OFL licence included).

Frontend — UI
- History table fits the page; expanded rows wrap text; voice scans have an icon.
- Mobile: dashboard list rows and cards no longer clip; toasts stay on screen.
- Copilot input is full width, quick questions stay available, typed
  questions work; verdict card no longer repeats the same metrics twice.
- Export menu closes on outside click/Escape; single-slice donut has no gap;
  shortcut hints show Ctrl or ⌘ by platform; category labels (UPI, OTP, KYC);
  sentence-case copy and clearer error messages; landing sections aligned.

### Results (all run in this pass, after the final change)

| Check | Result |
|---|---|
| Backend pytest (full suite) | **517 passed** (516 existing + 1 new) |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed, no warnings or errors |
| `npm run build` | Passed |
| Browser E2E (`docs/verification/e2e_browser_checks.py`) | **29 / 29 passed**, 0 uncaught page errors |

The E2E suite ran against the production Next.js server, the real FastAPI
app, a local SQLite database and the shipped model. It covers: registration
with the real CAPTCHA (including a wrong answer followed by a fresh
challenge), login, logout, protected-route redirect; text, URL, email,
image/OCR (Tesseract), PDF, QR (ZBar) and voice-transcript scans; feedback;
Copilot quick and typed questions; scan PDF export; case creation from a
scan, status change, note, case PDF and JSON export; history width, threat
filter, CSV export, expand and delete; dashboard, analytics, cases, settings,
demo; admin denied for a regular user; dark theme; and at 390px, eight pages
plus a verdict with no page overflow and no clipped visible elements.
The only console error was the expected 403 on the admin denial check.
The E2E script needs Playwright, which is a test-only tool and is not added
to the project requirements.

### Deployment follow-up (same day)
- The production image (`infra/docker/Dockerfile.app_service`, used by
  `render.yaml`) started **4** uvicorn workers. One worker measured ~250 MB RSS
  after OCR, PDF and model use, so four exceed the 512 MB Render free instance
  and the container is killed for memory. The default is now 1 worker
  (`UVICORN_WORKERS`, also set in `render.yaml`).
- **PostgreSQL verified locally (PostgreSQL 16):** `alembic upgrade head` ran
  all five migrations on an empty database, then the app (DEBUG=false, real
  secret) passed an API smoke test: CAPTCHA registration, login, text/image
  OCR/PDF/QR scans, history (and 422 on bad paging), feedback, Copilot, case
  create/note/status, scan and case PDF reports, analytics, delete, clear.
- Docker itself was not run (not available in this environment), and the live
  Render/Vercel services and their logs were not accessible.

### Not verified in this pass
- Physical camera and microphone on a real device (browser-dependent).
- Server-side audio transcription: no provider is implemented.
- Docker Compose, the live Render/Vercel deployment, Windows `.bat` launchers.
- Live external URL fetching/redirect behaviour on the public internet.
- The model: registry records 19 training / 5 evaluation rows (recorded
  accuracy 0.60). Scores are from an experimental classifier; UI work does
  not change its accuracy.

---

# Previous pass (retained for reference)


Date: 25 September 2026. Source: the user's uploaded `ScamGuard-final-working.zip`.
This is an update of that project, not a replacement application.

## A. UI improvements

- Shared neutral light/dark surfaces, consistent Plex typography, borders, radii,
  spacing, semantic severity colors, focus states, and calmer transitions.
- Landing page explains the evidence-to-investigation workflow without fabricated
  dashboard statistics. Authentication uses the same visual system.
- Compact workspace navigation, working mobile menu, skip link, and modal focus
  containment. Cases and demo examples are keyboard-operable links/buttons.
- Dashboard prioritizes actual high-risk findings and recurring indicators. Its
  recent-scan scope is labeled; duplicate entities within one scan count once.
- One investigation entry for text, URL, email, image, PDF, QR, camera, and voice.
- Verdict emphasizes severity, category, threat score, confidence, evidence,
  recommendations, and working case/Copilot/report actions.
- History has real server pagination and explicitly scopes search/export to the
  currently loaded page. Settings, analytics, cases, admin and evaluation screens
  retain their existing functionality and inherit the shared design language.

## B–C. Functional bugs found and fixes

1. Unscoped local history could expose another account's scans or resurrect deleted
   results. History now comes from the authenticated server; legacy cached scans
   are removed. Failures display errors instead of cached data.
2. API failures could resend credentials/evidence to a hardcoded remote deployment.
   Requests now stay with the configured backend; duplicate remote warm-up calls
   were removed.
3. Camera attached its stream before the conditional video element mounted. It now
   attaches after mounting and refuses capture before a frame is ready.
4. Voice start exceptions, silence, missing microphone, denied permission, and
   browser/network errors needed handling. The voice UI now has bounded listening,
   cleanup, always-accessible pasted transcripts, and honest provider messaging.
5. Blank or unavailable OCR and textless PDFs produced filename-based predictions.
   They now fail extraction rather than invent analyzable evidence. OCR has a
   timeout. Tests use readable image fixtures and cover empty-extraction rejection.
6. URL safety validation could be skipped when transport/proxy setup failed first.
   Initial validation now runs before transport construction; redirect checks remain.
   Malformed schemes, whitespace and ports receive input errors.
7. Demo results exposed exports requiring a saved prediction. Persisted scan
   actions are now omitted for unsaved demo examples.
8. Unhandled case action failures and silent history-to-case failures now show
   errors. Case creation prevents repeat submissions while saving.
9. Default input preference was saved but ignored; it now selects the analysis tab.
   Notification delivery, history opt-out, and customizable warning behavior are
   not implemented and their controls are clearly disabled.
10. Removed unverified system-health and email-verification claims, dead notification
    and footer links, and an ineffective login/registration cancel control.
11. Theme initialization caused server/client hydration mismatches. Initial state
    is now consistent, with browser preferences applied after mount.
12. Batch completion feedback now reports how many items actually succeeded.
13. Technical explanations mislabeled scam probability as confidence; these are
    now distinct. Email addresses no longer produce partial UPI identifiers, and
    trailing email punctuation is trimmed.
14. History clearing stopped at 1,000 records; it now processes every user record.
    History CSV export neutralizes spreadsheet-formula prefixes.
15. Report downloads have a timeout and an accessible export control. Severity
    takes priority over a benign model label in the summary banner.
16. Docker Compose no longer silently accepts a public JWT signing key. The
    frontend Docker build sets its proxy target at build time. The backend image
    now includes Tesseract as well as ZBar. Docker was not run here.

## D. Runtime and E2E verification

The production Next.js server and real FastAPI application ran locally, using a
fresh disposable SQLite database and the shipped in-process model. Browser
checks used Chromium; no analysis API responses were fabricated. Test accounts,
example scam text, and generated input files are test fixtures, not product data.

**39 browser checks passed with zero uncaught page errors.** Detailed names are
in `docs/verification/browser-checks.json`.

| Flow | Observed result |
|---|---|
| Landing, registration, real CAPTCHA, login, logout | Passed |
| Dashboard, real text verdict, feedback | Passed |
| URL analysis | Private target blocked; lexical evidence and verdict displayed |
| Email | Submitted headers/body produced forensic evidence and a verdict |
| Image/OCR | Readable PNG went through installed Tesseract and real inference |
| PDF | Generated text PDF extracted and analyzed |
| QR | Missing ZBar produced an error; successful decoding not verified here |
| Voice transcript | Pasted transcript went through voice signals and real inference |
| Uploaded audio | Unconfigured provider produced an explicit error |
| Physical camera | Unavailable-device error verified; see device check below |
| Cases | Created from a scan, linked evidence, changed status, saved timeline note |
| Copilot | Evidence-template answer generated from the actual scan |
| Reports | PDF downloaded through the authenticated browser workflow |
| History | Stored scan visible; matching/nonmatching searches and paging controls checked |
| Analytics | Real saved-data summary and charts rendered |
| Demo | Real model inference; persisted actions absent |
| Settings | Unsupported controls disabled; default modality persisted and took effect |
| Admin | Regular user denied; isolated test administrator viewed users and evaluation |
| Robustness lab | Actual suite executed and displayed measured results |
| Backend unavailable | Injected 503 displayed a visible error, without cached scan fallback |
| Responsive | 768px and 390px dashboard/analyze/cases/analytics/settings: no page overflow |
| Mobile navigation and theme | Navigation worked; dark theme rendered |

The injected 503 is explicitly a failure-state test, not a production fallback.
Not every possible control, browser, device, or deployment condition was exhaustively
exercised. Windows batch launchers were reviewed but not executed on Windows.

A separate controlled-device browser run also passed camera preview, frame
capture, OCR and real inference using a generated test-video camera. This verifies
the stream-mount fix and capture pipeline, not physical camera hardware. The same
Chromium runtime reported SpeechRecognition unsupported, and its unavailable UI
was checked. See `docs/verification/device-checks.json`.

## E. Voice and microphone status

Transcript analysis is verified. Live speech recognition is browser-dependent;
this run does not prove real microphone speech-to-text works on a user's device.
No server transcription provider is implemented or configured. Entering a provider
name/key alone does not add an implementation. Pasted transcripts remain usable.
Browser speech recognition may send audio to the browser vendor; the UI says so.

## F. Backend/API integration

The existing `/messages/scan` extraction and ML pipeline remains the integration
point. Cases, reports, history, analytics and Copilot continue using their existing
APIs. All **11 original model/registry files** match the uploaded bytes. Model
weights were neither retrained nor replaced.

Authentication, CAPTCHA, RBAC, user isolation, upload bounds, body limits, missing
model behavior, reports, URL protections, and pipeline contracts are covered by
the backend test suite. This is not a penetration test or production certification.

## G–H. Final quality gates

| Check | Result |
|---|---|
| Complete backend pytest suite | **516 passed**, 278 dependency/deprecation warnings |
| TypeScript (`npm run typecheck`) | Passed |
| ESLint (`npm run lint`) | Passed, no warnings/errors |
| Production build (`npm run build`) | Passed |
| Production browser checks | **39 passed**, zero uncaught page errors |
| Git whitespace/error check | Passed |

The original baseline had 507 passing tests and two failing SSRF-status tests.
Seven extraction-honesty regressions were added. Two existing blank-image success
fixtures were corrected to real readable images, while blank-image rejection is
covered separately. Logs and selected screenshots are included under
`docs/verification/`.

## I. Remaining limitations

- The model registry records only **19 training rows and 5 evaluation rows**.
  Its recorded accuracy is 0.60 on that tiny evaluation set. UI polish does not
  make the detector validated, enterprise-grade security infrastructure.
- No successful physical microphone transcription was tested. No external audio
  provider exists. Real hardware/browser permission testing is still needed.
- ZBar is absent from this verification runtime. QR success remains unverified;
  the error path was tested. Camera QR capture is not implemented: camera captures
  use OCR, while the separate QR upload tab uses the decoder.
- Live external redirect/TLS success was not verified. Structural URL intelligence
  and SSRF handling were tested. Existing DNS-rebinding/response-size hardening
  deserves a separate security review before public deployment.
- PostgreSQL, Docker orchestration, external hosting, and Windows launchers were
  not executed here. SQLite and the local production frontend were exercised.
- Notifications, history opt-out, and custom warning preferences are unavailable
  and clearly disabled. No new notification delivery service was fabricated.
- Existing account export is limited to its backend's 1,000-record history batch;
  it was not expanded in this pass. Large-account export completeness and the
  existing avatar endpoint need separate hardening before public release.
- Automated tests do not establish that every toggle or failure condition in every
  browser works. The tested paths and known gaps are listed explicitly above.

## J. Exact startup instructions

Read **START_HERE.md**. It includes Windows, macOS/Linux, dependency installation,
private configuration, localhost URLs, quality checks, and OCR/QR requirements.
For Windows after dependencies are installed: run `python setup_local.py`, then
`start_all.bat`. The setup script preserves any existing environment files.
