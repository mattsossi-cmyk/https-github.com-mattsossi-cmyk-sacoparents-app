/**
 * useStreakCelebration — smoke tests for the localStorage helper.
 * Full effect testing (confetti + toast) is skipped — it depends on
 * DOM canvas and would need a jsdom canvas polyfill. Instead we
 * verify the storage read/write round-trip so the "fire once per
 * device" contract is safe.
 */
import { _internals } from "./useStreakCelebration";

const { LS_KEY, THRESHOLDS, readCelebrated, writeCelebrated } = _internals;

describe("useStreakCelebration storage helpers", () => {
  beforeEach(() => { localStorage.clear(); });

  test("thresholds match the backend badge cutoffs (30 and 100)", () => {
    const ts = THRESHOLDS.map(([n]) => n);
    expect(ts).toEqual([30, 100]);
  });

  test("readCelebrated returns [] on cold start", () => {
    expect(readCelebrated()).toEqual([]);
  });

  test("readCelebrated returns [] on malformed JSON", () => {
    localStorage.setItem(LS_KEY, "not-json{{");
    expect(readCelebrated()).toEqual([]);
  });

  test("readCelebrated coerces to numbers and drops NaN", () => {
    localStorage.setItem(LS_KEY, JSON.stringify(["30", 100, "abc", null]));
    expect(readCelebrated()).toEqual([30, 100]);
  });

  test("writeCelebrated persists and readCelebrated round-trips", () => {
    writeCelebrated([30, 100]);
    expect(readCelebrated()).toEqual([30, 100]);
  });

  test("writeCelebrated on a broken localStorage is a no-op", () => {
    const orig = Storage.prototype.setItem;
    Storage.prototype.setItem = () => { throw new Error("quota"); };
    expect(() => writeCelebrated([30])).not.toThrow();
    Storage.prototype.setItem = orig;
  });
});
