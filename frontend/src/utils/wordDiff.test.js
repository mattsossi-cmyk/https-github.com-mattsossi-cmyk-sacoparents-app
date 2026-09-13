/**
 * wordDiff — unit tests for the LCS word-level diff powering the
 * `/admin/nudge-copy` Restore preview (iter189g).
 *
 * Behavior lock:
 *   * Removed word tokens surface on the `current` side.
 *   * Added word tokens surface on the `incoming` side.
 *   * Whitespace is preserved but the `DiffText` renderer never
 *     visually highlights a pure-whitespace token (test enforces
 *     input reconstruction — the property that guarantees no words
 *     are dropped or duplicated).
 *   * Identical inputs produce zero annotations on both sides.
 *   * Empty current → every incoming word is `added`.
 *   * Null / undefined inputs are treated as empty strings.
 */
import { wordDiff } from "./wordDiff";

const changedWords = (arr, side) =>
  arr
    .filter((t) => (side === "current" ? t.removed : t.added))
    .map((t) => t.text)
    .filter((s) => /\S/.test(s));

const concat = (arr) => arr.map((t) => t.text).join("");

describe("wordDiff · LCS word-level diff", () => {
  test("identical strings produce zero annotations", () => {
    const d = wordDiff("hello world", "hello world");
    expect(changedWords(d.current, "current")).toEqual([]);
    expect(changedWords(d.incoming, "incoming")).toEqual([]);
  });

  test("realistic softer-variant swap highlights only the changed words", () => {
    const cur = "Would you like to send these highlights to your co-parent?";
    const inc = "Share these highlights with your co-parent?";
    const d = wordDiff(cur, inc);
    expect(changedWords(d.current, "current")).toEqual([
      "Would", "you", "like", "to", "send", "to",
    ]);
    expect(changedWords(d.incoming, "incoming")).toEqual(["Share", "with"]);
  });

  test("empty current marks every incoming word as added", () => {
    const d = wordDiff("", "brand new headline text");
    expect(changedWords(d.incoming, "incoming")).toEqual([
      "brand", "new", "headline", "text",
    ]);
    expect(changedWords(d.current, "current")).toEqual([]);
  });

  test("empty incoming marks every current word as removed", () => {
    const d = wordDiff("some existing wording", "");
    expect(changedWords(d.current, "current")).toEqual([
      "some", "existing", "wording",
    ]);
    expect(changedWords(d.incoming, "incoming")).toEqual([]);
  });

  test("token sequences reconstruct the exact input strings", () => {
    // Property test: concatenating every token verbatim on each side
    // must faithfully reproduce the input — no words lost or duplicated.
    const cur = "  leading space  and trailing  ";
    const inc = "leading  space  now  trailing";
    const d = wordDiff(cur, inc);
    expect(concat(d.current)).toBe(cur);
    expect(concat(d.incoming)).toBe(inc);
  });

  test("null / undefined inputs are treated as empty strings", () => {
    expect(() => wordDiff(null, "hello")).not.toThrow();
    expect(() => wordDiff("hello", undefined)).not.toThrow();
    expect(() => wordDiff(null, null)).not.toThrow();
    const d = wordDiff(null, "one two");
    expect(changedWords(d.incoming, "incoming")).toEqual(["one", "two"]);
  });
});
