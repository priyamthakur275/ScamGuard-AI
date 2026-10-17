# TrustLens: evidence-aware scam analysis and safety guidance

TrustLens explains a ScamGuard result: what evidence the existing detection pipeline found, which stage of a
typical scam each piece belongs to, what to do, what known pattern it resembles, and why the result may be wrong.

**TrustLens adds no new score.** The classifier, the ThreatScorer fusion formula, the verdict thresholds and the
retriever are unchanged. TrustLens only reads their outputs.

## What already existed vs. what is new

| Part | Status |
|---|---|
| TF-IDF + linear SVM classifier probability (`scam_probability`) | Existing (research pipeline) |
| Fused risk score and verdict (`threat_score`, ThreatScorer log-odds fusion) | Existing |
| Intent and protective regex patterns, genuine-transaction guard | Existing |
| Scam X-Ray: phrase spans with stage (hook / pressure / ask / cash-out) and explanation | Existing |
| Hybrid retriever + CRAG evaluator (CORRECT / AMBIGUOUS / INCORRECT) over 52 cited patterns | Existing |
| **TrustLens report** (`metadata.trustlens`) combining the above | **New** |
| **Scam Journey Mapper**, evidence-for/against panel, uncertainty section | **New** |
| **Evidence-driven safe-action recommendations** | **New** |
| **Similar-pattern panel** with source link, shown only when the evaluator accepts the match | **New** |
| **How a genuine message differs**: each matched tactic contrasted with genuine behaviour, plus a genuine library format | **New** |

## Architecture and data flow

```
text -> MessageService._run_pipeline
          classifier probability -> ThreatScorer fusion -> verdict / threat_score    (existing, unchanged)
          scam_xray.xray(text)  -> metadata.xray                                     (existing)
          trustlens.build_trustlens(verdict, scam_probability, threat_score,
                                    risk_level, xray)  -> metadata.trustlens         (new)
             |- evidence_for      <- X-Ray spans (phrase, intent, stage, why)
             |- evidence_against  <- protective patterns that matched (+ phrase)
             |- journey           <- the 4 stages; detected only with matched phrases
             |- recommendations   <- fixed safety actions keyed by matched intents
             |- similar_pattern   <- HybridRetriever + grade_retrieval (CRAG rules)
             |- genuine_contrast  <- matched tactics -> what a genuine message does instead,
             |                       plus a genuine library format chosen by those tactics (scams only)
             '- uncertainty       <- conflicts, insufficient evidence, missing context,
                                     classifier/fused disagreement, short text
frontend: components/analysis/trust-lens.tsx  <- lib/trustlens.ts parseTrustLens()
```

- Retrieval stays separate from the verdict: a similar pattern is displayed, never fed into the score.
- A match is shown only when the evaluator grades it **CORRECT**. AMBIGUOUS and INCORRECT never display a match;
  if the retriever fails the panel says it is unavailable and the verdict is unaffected.
- If `build_trustlens` fails, the analysis is returned without `metadata.trustlens` (logged, not fatal).
- The frontend validates the payload; missing or malformed data shows "TrustLens analysis isn't available"
  instead of guessed content. Scans saved before TrustLens existed show the same notice.

## API changes

Backward compatible. Every analysis response (`/public/quick-check`, `/messages/scan`, `/messages/analyze`,
`/copilot/analyze` → `analysis`, history) now includes `metadata.trustlens`. No field was removed or renamed and no
new endpoint was needed.

```jsonc
"trustlens": {
  "version": 1,
  "verdict": "scam", "risk_level": "high",
  "classifier_probability": 0.9998,   // model alone
  "risk_score": 0.9999,               // fused score the verdict uses
  "summary": "4 scam signs matched across 3 stage(s) of a typical scam.",
  "evidence_for":   [{"phrase": "Share the OTP", "intent": "asks_for_secret", "label": "...", "stage": "ask", "why": "..."}],
  "evidence_against": [{"pattern": "warns_not_to_share", "phrase": "...", "why": "..."}],
  "genuine_transaction": false,
  "journey": [{"stage": "hook", "name": "Hook", "meaning": "...", "detected": false, "evidence": []}, ...],
  "recommendations": [{"id": "secret", "text": "..."}],
  "similar_pattern": {"status": "match|ambiguous|none|unavailable", "relevance": 0.71, "match": {...} | null, "genuine_match": {...} | null},
  "genuine_contrast": {"points": [{"label": "...", "scam_phrase": "...", "genuine": "..."}], "example": {"title": "...", "text": "...", "source_url": "https://..."} | null} | null,
  "uncertainty": {"conflicting": false, "insufficient": false, "missing_context": ["..."], "may_be_wrong": ["..."]},
  "disclaimer": "This is a risk assessment ..."
}
```

## Files

New: `backend/app_service/services/trustlens.py`, `backend/tests/test_trustlens.py`,
`frontend/src/lib/trustlens.ts`, `frontend/src/components/analysis/trust-lens.tsx`, `docs/TRUSTLENS.md`.

Modified: `backend/app_service/services/message_service.py` (attaches the report after the X-Ray),
`frontend/src/components/analysis/verdict-card.tsx` (full panel on scan results),
`frontend/src/components/landing/quick-check.tsx` (collapsible panel on the quick check).

## Tests (run on 2026-10-18)

| Command | Result |
|---|---|
| `pytest tests` (backend) | 348 passed |
| `pytest ml_common/tests ml_training/tests ml_service/tests` | 307 passed |
| `npm run typecheck`, `npm run lint`, `npm run build` | clean |
| `npm test` (vitest, includes `parseTrustLens`) | 15 passed |
| Browser check (Playwright, production build, local backend) | all scenarios below passed, no page errors |

`tests/test_trustlens.py` covers: explicit OTP request; protective "do not share your OTP" warning; urgency
without a request; a genuine bank debit alert; conflicting scam and protective evidence; an unfamiliar message with
insufficient evidence; malformed X-Ray data; retrieval unavailable (verdict unchanged); similar pattern shown only
when accepted; API compatibility (existing fields and `metadata.xray` unchanged); TrustLens failure not breaking
the analysis. Tests check that TrustLens reports what the real model and rules produced; they do not force
verdicts.

Browser scenarios: real scam message on desktop with keyboard expansion of a journey stage; genuine OTP message on
a 390 px phone screen (no horizontal scrolling); stubbed malformed TrustLens payload (fallback notice); stubbed
server error and slow response (loading button, error message, no TrustLens shown).

Frontend unit tests (vitest) cover the payload parser: missing/malformed reports, stages never marked without evidence, matches without an https source dropped, and the genuine-contrast section. Rendered states were verified in the browser.

## Demonstration walkthrough (example messages, labelled as examples)

1. **Example scam:** "Dear customer your SBI account will be blocked today. Share the OTP sent to your phone at
   http://sbi-kyc.xyz". Expected display: Pressure, Ask and Cash-out detected, Hook not detected; recommendations
   about OTPs, links and verifying through the official app; similar pattern "Fake bank KYC update / account block
   SMS" with its RBI source.
2. **Example genuine OTP:** "482913 is your OTP for login. Do not share this OTP with anyone. SBI never asks for
   your OTP." Expected display: no stage detected, the warning listed under "Points the other way", resemblance to
   the genuine OTP format.
3. **Example conflict:** "Never share your OTP with anyone. To avoid suspension, share the OTP sent to your mobile
   with our verification officer today." Expected display: the "evidence conflicts" notice.
4. **Example unfamiliar:** "ok see you there". Expected display: insufficient-evidence notice and "rests only on
   the classifier".

The actual numbers shown come from the live model at the time of the check and may differ from the values above.

## Limitations

- Evidence is regex-based: it describes wording, not intent. New scams can avoid the patterns and genuine
  messages can use them; TrustLens says so in "Why this may be wrong".
- The risk score is not a calibrated probability; TrustLens labels it as a score.
- The pattern library has 52 entries (42 scam, 10 genuine); many real scams will show "No known scam pattern".
- Recommendations are fixed texts chosen by matched evidence, not personalised advice.
- English and some Hinglish only, as for the rest of the rule engine. With the Hindi interface the headings and labels are Hindi; the detailed explanations stay in English.
