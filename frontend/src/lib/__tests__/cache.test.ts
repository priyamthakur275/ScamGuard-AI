import { beforeEach, describe, expect, it, vi } from "vitest";
import { cached, invalidate } from "@/lib/api/cache";

describe("api cache", () => {
  beforeEach(() => invalidate());

  it("reuses a fresh value and shares in-flight requests", async () => {
    const load = vi.fn().mockResolvedValue([1]);
    const [a, b] = await Promise.all([cached("history:0:50", load), cached("history:0:50", load)]);
    expect(a).toEqual([1]); expect(b).toEqual([1]);
    await cached("history:0:50", load);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("expires after the TTL", async () => {
    let t = 0;
    const load = vi.fn().mockResolvedValue("x");
    await cached("k", load, 100, () => t);
    t = 150;
    await cached("k", load, 100, () => t);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("invalidates by prefix and does not cache failures", async () => {
    const load = vi.fn().mockResolvedValue("v");
    await cached("history:0:50", load);
    await cached("analytics:all", load);
    invalidate("history:");
    await cached("history:0:50", load);
    await cached("analytics:all", load);
    expect(load).toHaveBeenCalledTimes(3);
    const bad = vi.fn().mockRejectedValueOnce(new Error("down")).mockResolvedValue("ok");
    await expect(cached("x", bad)).rejects.toThrow("down");
    await expect(cached("x", bad)).resolves.toBe("ok");
  });
});
