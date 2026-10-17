import { describe, expect, it } from "vitest";
import { markAgain, markKnown, newDeck, restoreDeck, shuffled } from "@/lib/flashcards";

describe("flashcard deck", () => {
  it("removes known cards and finishes when all are known", () => {
    let d = newDeck(["a", "b"]);
    d = markKnown(markKnown(d));
    expect(d.queue).toEqual([]);
    expect(d.known).toEqual(["a", "b"]);
    expect(markKnown(d)).toEqual(d);
  });

  it("brings a missed card back a few cards later", () => {
    const d = markAgain(newDeck(["a", "b", "c", "d", "e"]), 3);
    expect(d.queue).toEqual(["b", "c", "d", "a", "e"]);
    expect(d.missed).toEqual(["a"]);
    const end = markAgain(newDeck(["a", "b"]), 3);
    expect(end.queue).toEqual(["b", "a"]);
  });

  it("restores only valid saved progress and adds new cards", () => {
    expect(restoreDeck(null, ["a"])).toBeNull();
    expect(restoreDeck({ queue: "x" }, ["a"])).toBeNull();
    const r = restoreDeck({ queue: ["b", "zzz"], known: ["a"], missed: [] }, ["a", "b", "c"])!;
    expect(r.queue).toEqual(["b", "c"]);
    expect(r.known).toEqual(["a"]);
  });

  it("shuffles without losing cards", () => {
    const ids = ["a", "b", "c", "d"];
    expect(shuffled(ids, () => 0.3).sort()).toEqual(ids);
    expect(newDeck(["a", "a", "b"]).queue).toEqual(["a", "b"]);
  });
});
