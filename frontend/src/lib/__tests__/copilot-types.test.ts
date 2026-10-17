import { describe, expect, it } from "vitest";
import { normalizeVerdict, parseStreamEvent } from "@/lib/copilot/types";

describe("normalizeVerdict", () => {
  it("rejects payloads without is_scam", () => {
    expect(normalizeVerdict({ fraud_index: 90 })).toBeNull();
    expect(normalizeVerdict(null)).toBeNull();
  });
  it("clamps numbers and fills missing lists", () => {
    const v = normalizeVerdict({ is_scam: true, fraud_index: 250, confidence_percentage: -4 })!;
    expect(v.fraud_index).toBe(100);
    expect(v.confidence_percentage).toBe(0);
    expect(v.risk_tier).toBe("High");
    expect(v.matched_tactics).toEqual([]);
    expect(v.retrieval_grade).toBe("INCORRECT");
  });
});

describe("parseStreamEvent", () => {
  it("parses token, done and error events", () => {
    expect(parseStreamEvent("token", '{"text":"Hi "}')).toEqual({ type: "token", text: "Hi " });
    expect(parseStreamEvent("done", '{"kind":"guidance"}')).toEqual({ type: "done", kind: "guidance" });
    const e = parseStreamEvent("error", '{"message":"x","retryable":false}');
    expect(e).toMatchObject({ type: "error", message: "x", retryable: false });
  });
  it("ignores bad JSON and unknown events", () => {
    expect(parseStreamEvent("token", "{not json")).toBeNull();
    expect(parseStreamEvent("mystery", "{}")).toBeNull();
  });
});
