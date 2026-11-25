/**
 * Rewrites GitHub PR references in markdown into markdown links.
 *
 * Shared by the Claude Code mod (hooks/register.ts) and the Pi extension
 * (~/.pi/agent/extensions/pr-links, which symlinks this file), so it imports
 * nothing and touches no runtime API.
 *
 * - `owner/repo#123` becomes `[owner/repo#123](https://github.com/owner/repo/pull/123)`.
 * - `#123` becomes `[#123](https://github.com/<defaultRepo>/pull/123)` when a
 *   default repo is known, and is left alone otherwise.
 *
 * Code spans, fenced code blocks, existing markdown links, autolinks and bare
 * URLs are left untouched, so the rewrite is idempotent. GitHub redirects
 * /pull/N to /issues/N when N is an issue.
 */

const PROTECTED = new RegExp(
  [
    // Fenced code block, to its closing fence or the end of the text.
    String.raw`(?:^|(?<=\n))[ \t]*(\`{3,}|~{3,})[^\n]*\n[\s\S]*?(?:\n[ \t]*\1[ \t]*(?=\n|$)|$)`,
    // Inline code span with a matching backtick run.
    String.raw`(\`+)[^\`][\s\S]*?\2`,
    // Markdown link or image, including reference-style `[text][ref]`.
    String.raw`!?\[[^\]\n]*\](?:\([^)\n]*\)|\[[^\]\n]*\])`,
    // Autolink.
    String.raw`<[a-z][a-z0-9+.-]*:[^>\s]*>`,
    // Bare URL.
    String.raw`\b[a-z][a-z0-9+.-]*:\/\/[^\s<>()\[\]]+`,
  ].join("|"),
  "gi",
);

// Groups 1 and 2 belong to PROTECTED's backreferences. owner follows GitHub
// login rules, repo GitHub repository name characters.
const REF = new RegExp(
  `${PROTECTED.source}|` +
    String.raw`(?<![\w./#&@-])(?:([A-Za-z0-9][A-Za-z0-9-]{0,38})\/([A-Za-z0-9._-]{1,100}))?#(\d{1,7})(?![\w-])`,
  "gi",
);

const REPO = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100}$/;

/**
 * Parses `owner/repo` from a GitHub remote URL (`git@github.com:o/r.git`,
 * `https://github.com/o/r`, `ssh://git@github.com/o/r.git`); undefined for any
 * other host.
 */
export function githubRepoFromRemote(remote: string): string | undefined {
  const match = remote
    .trim()
    .match(/^(?:[a-z+]+:\/\/)?(?:[^@/\s]+@)?github\.com[:/]([^/\s]+\/[^/\s]+?)(?:\.git)?\/?$/i);
  const repo = match?.[1];
  return repo && REPO.test(repo) ? repo : undefined;
}

export function linkifyPrRefs(text: string, defaultRepo?: string): string {
  if (!text.includes("#")) return text;
  const fallback = defaultRepo && REPO.test(defaultRepo) ? defaultRepo : undefined;
  return text.replace(
    REF,
    (match, _fence, _ticks, owner: string | undefined, name: string | undefined, number: string | undefined) => {
      if (number === undefined) return match;
      const repo = owner && name ? `${owner}/${name.replace(/\.git$/, "")}` : fallback;
      if (!repo || !REPO.test(repo)) return match;
      return `[${match}](https://github.com/${repo}/pull/${number})`;
    },
  );
}
