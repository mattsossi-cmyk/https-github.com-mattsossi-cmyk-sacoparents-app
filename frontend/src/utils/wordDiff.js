/**
 * Word-level LCS diff — powers the Restore preview on
 * `/admin/nudge-copy` (iter189g). Standalone (no React imports) so
 * it can be unit-tested cleanly.
 *
 * Returns two aligned token arrays annotated with `removed` / `added`
 * flags. Whitespace is preserved as its own tokens so callers can
 * render them verbatim without adding visual highlight.
 *
 *   wordDiff("old", "new") -> {
 *     current:  [{ text, removed: bool }, …]  // "before" side
 *     incoming: [{ text, added:   bool }, …]  // "after"  side
 *   }
 *
 * Uses classic O(n·m) LCS dynamic programming. Fine for our inputs —
 * headline is 6-120 chars (~1-25 tokens), subhead is 10-600 chars
 * (~2-120 tokens). Null / undefined inputs are treated as empty
 * strings.
 */
export function wordDiff(a, b) {
  const toksA = (a || "").split(/(\s+)/);
  const toksB = (b || "").split(/(\s+)/);
  const m = toksA.length;
  const n = toksB.length;
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (toksA[i - 1] === toksB[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }
  const current = [];
  const incoming = [];
  let i = m;
  let j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && toksA[i - 1] === toksB[j - 1]) {
      current.unshift({ text: toksA[i - 1], removed: false });
      incoming.unshift({ text: toksB[j - 1], added: false });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      incoming.unshift({ text: toksB[j - 1], added: true });
      j--;
    } else {
      current.unshift({ text: toksA[i - 1], removed: true });
      i--;
    }
  }
  return { current, incoming };
}
