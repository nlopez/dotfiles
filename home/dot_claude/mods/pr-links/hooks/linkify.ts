/**
 * Rewrites GitHub PR references in markdown into markdown links.
 *
 * Shared by the Claude Code mod (hooks/register.ts) and the Pi extension
 * (~/.pi/agent/extensions/pr-links, which symlinks this file), so it imports
 * nothing and touches no runtime API: callers look repos up and pass them in.
 *
 * - `owner/repo#123` links to that repo.
 * - `repo#123` and `SDP#123` link when `repo` is the name, or the initials of
 *   a name with three or more parts, of exactly one known clone.
 * - `#123` and `PR 123` link to the one repo the text itself names (PR URLs,
 *   `owner/repo#N` refs), else to the session's repo; they stay plain when the
 *   text names several repos, or no repo is known.
 * - A code span holding only a ref (`` `owner/repo#1` ``) links as a whole.
 *
 * Fenced code, other code spans, existing links, autolinks and URLs are left
 * alone, so the rewrite is idempotent. GitHub redirects /pull/N to /issues/N
 * when N is an issue.
 */

export type RepoIndex = ReadonlyMap<string, string>;

export interface RepoContext {
  /** `owner/repo` of the session's working directory. */
  sessionRepo?: string;
  /** Lowercased repo name or initials to `owner/repo`, from repoIndex(). */
  index?: RepoIndex;
}

const OWNER = String.raw`[A-Za-z0-9][A-Za-z0-9-]{0,38}`;
const NAME = String.raw`[A-Za-z0-9._-]{1,100}`;
const REPO = new RegExp(`^${OWNER}/${NAME}$`);
const NOT_AFTER = String.raw`(?<![\w./#&@-])`;
const NOT_BEFORE = String.raw`(?![\w-])`;

// Words that read as "PR" rather than a repo name in `PR#12`.
const PR_WORDS = new Set(["pr", "prs", "mr", "gh", "issue", "issues", "pull"]);

const PROTECTED = [
  // Fenced code block, to its closing fence or the end of the text.
  String.raw`(?:^|(?<=\n))[ \t]*(\`{3,}|~{3,})[^\n]*\n[\s\S]*?(?:\n[ \t]*\1[ \t]*(?=\n|$)|$)`,
  // Inline code span with a matching backtick run.
  String.raw`(\`+)([^\`][\s\S]*?)\2`,
  // Markdown link or image, including reference-style `[text][ref]`.
  String.raw`!?\[[^\]\n]*\](?:\([^)\n]*\)|\[[^\]\n]*\])`,
  // Autolink.
  String.raw`<[a-z][a-z0-9+.-]*:[^>\s]*>`,
  // Bare URL.
  String.raw`\b[a-z][a-z0-9+.-]*:\/\/[^\s<>()\[\]]+`,
].join("|");

// A ref: `owner/repo#N`, `name#N`, `#N`, or `PR N` / `PR #N`.
const REF_BODY =
  String.raw`(?:(${OWNER})\/(${NAME})|([A-Za-z][A-Za-z0-9._-]{0,99}))?#(\d{1,7})${NOT_BEFORE}` +
  String.raw`|\b(PRs?|[Pp]ull [Rr]equests?)\s+#?(\d{1,7})\b`;

// Groups: 1 fence, 2 ticks, 3 code body, 4 owner, 5 name, 6 bare name,
// 7 number, 8 PR word, 9 PR number.
const TOKEN = new RegExp(`${PROTECTED}|${NOT_AFTER}(?:${REF_BODY})`, "g");
const CODE_REF = new RegExp(`^\\s*${NOT_AFTER}(?:${REF_BODY})\\s*$`);

const NAMED_REPOS = new RegExp(
  String.raw`github\.com\/(${OWNER}\/${NAME})\/(?:pull|issues)\/\d` + `|${NOT_AFTER}(${OWNER}\\/${NAME})#\\d`,
  "g",
);

function cleanRepo(owner: string, name: string): string | undefined {
  const repo = `${owner}/${name.replace(/\.git$/, "")}`;
  return REPO.test(repo) && !/\/\.{1,2}$/.test(repo) ? repo : undefined;
}

/**
 * Parses `owner/repo` from a GitHub remote URL (`git@github.com:o/r.git`,
 * `https://github.com/o/r`, `ssh://git@github.com/o/r.git`, or an SSH alias
 * host such as `git@work.github.com:o/r`); undefined for any other host.
 */
export function githubRepoFromRemote(remote: string): string | undefined {
  const match = remote
    .trim()
    .match(/^(?:[a-z+]+:\/\/)?(?:[^@/\s]+@)?(?:[\w-]+\.)*github\.com(?::\d+)?[:/]([^/\s]+)\/([^/\s]+?)(?:\.git)?\/?$/i);
  return match ? cleanRepo(match[1], match[2]) : undefined;
}

/** Parses `owner/repo` from a ghq-style path, `…/github.com/<owner>/<repo>/…`. */
export function githubRepoFromPath(path: string): string | undefined {
  const match = path.match(/(?:^|\/)github\.com\/([^/]+)\/([^/]+)(?:\/|$)/);
  return match ? cleanRepo(match[1], match[2]) : undefined;
}

function initials(name: string): string | undefined {
  const parts = name.split(/[-_.]+/).filter(Boolean);
  return parts.length >= 3
    ? parts
        .map((p) => p[0])
        .join("")
        .toLowerCase()
    : undefined;
}

/**
 * Indexes `owner/repo` names (from `ghq list`: `github.com/owner/repo` lines;
 * other lines are skipped) by lowercased name and by initials. A key two repos
 * share is dropped, and an exact name wins over initials.
 */
export function repoIndex(lines: Iterable<string>): RepoIndex {
  const names = new Map<string, Set<string>>();
  const abbrevs = new Map<string, Set<string>>();
  const add = (map: Map<string, Set<string>>, key: string, repo: string) =>
    (map.get(key) ?? map.set(key, new Set()).get(key)!).add(repo);
  for (const line of lines) {
    const match = line.trim().match(/^github\.com\/([^/]+)\/([^/]+)$/i);
    const repo = match && cleanRepo(match[1], match[2]);
    if (!repo) continue;
    const name = repo.split("/")[1];
    add(names, name.toLowerCase(), repo);
    const abbrev = initials(name);
    if (abbrev) add(abbrevs, abbrev, repo);
  }
  const index = new Map<string, string>();
  for (const [key, repos] of abbrevs) if (repos.size === 1) index.set(key, [...repos][0]);
  for (const [key, repos] of names) {
    if (repos.size === 1) index.set(key, [...repos][0]);
    else index.delete(key);
  }
  return index;
}

/** The repo a bare `#N` in `text` refers to, or undefined when unclear. */
function bareRepo(text: string, { sessionRepo, index }: RepoContext): string | undefined {
  // Lowercased repo to the first spelling seen.
  const named = new Map<string, string>();
  const note = (repo: string) => named.has(repo.toLowerCase()) || named.set(repo.toLowerCase(), repo);
  for (const m of text.matchAll(NAMED_REPOS)) note(m[1] ?? m[2]);
  if (index) {
    for (const m of text.matchAll(new RegExp(`${NOT_AFTER}([A-Za-z][A-Za-z0-9._-]{0,99})#\\d`, "g"))) {
      const repo = !PR_WORDS.has(m[1].toLowerCase()) && index.get(m[1].toLowerCase());
      if (repo) note(repo);
    }
  }
  if (named.size > 1) return undefined;
  const [only] = named.values();
  if (!only) return sessionRepo;
  return sessionRepo?.toLowerCase() === only.toLowerCase() ? sessionRepo : only;
}

export function linkifyPrRefs(text: string, context: RepoContext = {}): string {
  if (!/#|\bPRs?\s+\d|[Pp]ull [Rr]equests?\s+\d/.test(text)) return text;
  const sessionRepo = context.sessionRepo && REPO.test(context.sessionRepo) ? context.sessionRepo : undefined;
  const fallback = bareRepo(text, { ...context, sessionRepo });

  const resolve = (groups: (string | undefined)[]): { repo: string; number: string } | undefined => {
    const [owner, name, bareName, number, prWord, prNumber] = groups;
    if (prWord) return fallback ? { repo: fallback, number: prNumber! } : undefined;
    if (number === undefined) return undefined;
    if (owner && name) {
      const repo = cleanRepo(owner, name);
      return repo ? { repo, number } : undefined;
    }
    if (bareName && !PR_WORDS.has(bareName.toLowerCase())) {
      const key = bareName.toLowerCase();
      const repo =
        sessionRepo && sessionRepo.split("/")[1].toLowerCase() === key ? sessionRepo : context.index?.get(key);
      return repo ? { repo, number } : undefined;
    }
    return fallback ? { repo: fallback, number } : undefined;
  };
  const url = ({ repo, number }: { repo: string; number: string }) => `https://github.com/${repo}/pull/${number}`;

  return text.replace(TOKEN, (match: string, ...args: unknown[]) => {
    const g = args.slice(0, 9) as (string | undefined)[];
    if (g[2] !== undefined) {
      // A code span: link it whole when it holds only a ref.
      const inner = g[2].match(CODE_REF);
      const ref = inner && resolve(inner.slice(1, 7));
      return ref ? `[${match}](${url(ref)})` : match;
    }
    if (g[6] === undefined && g[7] === undefined) return match;
    const ref = resolve(g.slice(3, 9));
    if (!ref) return match;
    return `[${match}](${url(ref)})`;
  });
}
