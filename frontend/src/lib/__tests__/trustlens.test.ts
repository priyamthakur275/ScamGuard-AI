import { describe, expect, it } from "vitest";
import { parseTrustLens } from "@/lib/trustlens";

const good = {
  version: 1,
  verdict: "scam",
  risk_level: "high",
  classifier_probability: 0.98,
  risk_score: 0.99,
  summary: "2 scam signs matched",
  evidence_for: [{ phrase: "share the OTP", intent: "asks_for_secret", label: "Asks for OTP", stage: "ask", why: "Banks never ask." }],
  evidence_against: [],
  genuine_transaction: false,
  journey: [
    { stage: "hook", name: "Hook", meaning: "m", detected: false, evidence: [] },
    { stage: "ask", name: "Ask", meaning: "m", detected: true, evidence: [{ phrase: "share the OTP", intent: "asks_for_secret", label: "Asks for OTP", stage: "ask", why: "w" }] },
  ],
  recommendations: [{ id: "secret", text: "Do not share OTPs." }],
  similar_pattern: { status: "match", match: { title: "Fake KYC", source_url: "https://rbi.org.in/x", shared_tactics: ["asks_for_secret"] }, genuine_match: null },
  uncertainty: { conflicting: false, insufficient: false, missing_context: ["Who sent it."], may_be_wrong: ["Wording only."] },
  disclaimer: "Risk assessment, not proof.",
};

describe("parseTrustLens", () => {
  it("keeps the backend's numbers and always returns the four stages in order", () => {
    const r = parseTrustLens(good)!;
    expect(r.classifier_probability).toBe(0.98);
    expect(r.risk_score).toBe(0.99);
    expect(r.journey.map((j) => j.stage)).toEqual(["hook", "pressure", "ask", "cashout"]);
    expect(r.journey.find((j) => j.stage === "ask")!.detected).toBe(true);
    expect(r.journey.find((j) => j.stage === "pressure")!.detected).toBe(false);
  });

  it("returns null for missing or malformed payloads", () => {
    for (const bad of [undefined, null, "x", 5, {}, { verdict: 5, journey: [] }, { verdict: "scam", journey: "x" }]) {
      expect(parseTrustLens(bad)).toBeNull();
    }
  });

  it("never marks a stage detected without evidence", () => {
    const r = parseTrustLens({ ...good, journey: [{ stage: "hook", detected: true, evidence: [] }] })!;
    expect(r.journey.every((j) => !j.detected)).toBe(true);
  });

  it("drops a similar-pattern match without an https source", () => {
    const r = parseTrustLens({ ...good, similar_pattern: { status: "match", match: { title: "X", source_url: "http://x" } } })!;
    expect(r.similar_pattern.match).toBeNull();
    expect(r.similar_pattern.status).toBe("none");
  });

  it("treats unknown retrieval status as unavailable and missing scores as null", () => {
    const r = parseTrustLens({ ...good, classifier_probability: "high", risk_score: undefined, similar_pattern: { status: "weird" } })!;
    expect(r.similar_pattern.status).toBe("unavailable");
    expect(r.classifier_probability).toBeNull();
    expect(r.risk_score).toBeNull();
  });
});

describe("genuine contrast", () => {
  it("keeps valid points and drops an example without an https source", () => {
    const r = parseTrustLens({
      ...good,
      genuine_contrast: { points: [{ label: "Asks for OTP", scam_phrase: "share the OTP", genuine: "Real ones never ask." }, { label: "" }], example: { text: "x", source_url: "ftp://x" } },
    })!;
    expect(r.genuine_contrast!.points).toHaveLength(1);
    expect(r.genuine_contrast!.example).toBeNull();
  });
  it("is null when absent or empty", () => {
    expect(parseTrustLens(good)!.genuine_contrast).toBeNull();
    expect(parseTrustLens({ ...good, genuine_contrast: { points: [] } })!.genuine_contrast).toBeNull();
  });
});
