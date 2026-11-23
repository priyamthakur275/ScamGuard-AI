import { describe, expect, it } from "vitest";
import { needsReview, REVIEW_BAND } from "@/lib/utils";

describe("review band", () => {
  it("flags only scores in [0.3, 0.7)", () => {
    expect(REVIEW_BAND).toEqual({ low: 0.3, high: 0.7 });
    expect(needsReview(0.29)).toBe(false);
    expect(needsReview(0.3)).toBe(true);
    expect(needsReview(0.5)).toBe(true);
    expect(needsReview(0.699)).toBe(true);
    expect(needsReview(0.7)).toBe(false);
    expect(needsReview(0.98)).toBe(false);
  });
});
