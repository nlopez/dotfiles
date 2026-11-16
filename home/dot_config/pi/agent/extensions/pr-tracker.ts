/**
 * pr-tracker extension
 *
 * Tracks pull requests opened during the session (`gh pr create` output or a
 * GitHub MCP create-PR tool) and shows their live status in a widget below the
 * editor, plus a one-line summary in the footer.
 *
 * Polling: one batched GraphQL request per GitHub host covers every tracked PR.
 * The interval adapts: 30s while any check is running, 2m while PRs are open
 * and settled, stopped once every PR is merged or closed. Errors back off
 * exponentially up to 10m. A refresh also runs when a PR is added, after
 * `git push` / `gh pr` commands, and at the end of each agent run.
 *
 * On load, the active branch is replayed: PRs created by earlier tool calls are
 * picked up (including sessions that predate this extension), and add/remove
 * entries from /prs apply in order. The list follows /tree branches.
 *
 * /prs                 toggle the widget
 * /prs add <url>       track an existing PR
 * /prs rm <url|#n>     stop tracking a PR
 * /prs refresh         refresh now
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";

const ENTRY = "pr-tracker";
const PR_URL = /https?:\/\/([\w.-]+)\/([\w.-]+)\/([\w.-]+)\/pull\/(\d+)/g;
const PR_CREATE = /(?:^|[\s;&|(`$])(?:\S*\/)?gh\b[^\n;&|]*\bpr\s+create\b/;
const REFRESH_TRIGGER = /\bgit\s+push\b|\bgh\b[^\n;&|]*\bpr\s+(?:ready|merge|close|reopen|edit|review)\b/;

const FAST_MS = 30_000;
const SLOW_MS = 120_000;
const MAX_BACKOFF_MS = 600_000;
const MIN_GAP_MS = 10_000;
const WIDGET_MAX = 5;

type Checks = { pass: number; pending: number; fail: number };
type PrStatus = {
  title: string;
  state: "OPEN" | "MERGED" | "CLOSED";
  isDraft: boolean;
  review: string | null;
  mergeable: string;
  rollup: string | null;
  checks: Checks;
  unresolved: number;
};
type Tracked = {
  url: string;
  host: string;
  owner: string;
  repo: string;
  number: number;
  status?: PrStatus;
  error?: string;
};

function parsePr(url: string): Tracked | undefined {
  PR_URL.lastIndex = 0;
  const m = PR_URL.exec(url);
  if (!m) return undefined;
  const [, host, owner, repo, num] = m;
  return { url: `https://${host}/${owner}/${repo}/pull/${num}`, host, owner, repo, number: Number(num) };
}

function extractUrls(text: string): string[] {
  return [...text.matchAll(PR_URL)].map((m) => m[0]);
}

function resultText(content: unknown): string {
  if (!Array.isArray(content)) return "";
  return content
    .map((c) => (c && typeof c === "object" && "text" in c ? String((c as { text: unknown }).text) : ""))
    .join("\n");
}

/** PR URLs created by one tool call, or none if the call did not create a PR. */
function createdPrUrls(toolName: string, input: unknown, text: string, isError: boolean): string[] {
  if (toolName === "bash") {
    const command = String((input as { command?: string } | undefined)?.command ?? "");
    return PR_CREATE.test(command) ? extractUrls(text) : [];
  }
  if (/create_?pull_?request/i.test(toolName) && !isError) return extractUrls(text);
  return [];
}

const CHECK_FAIL = new Set([
  "FAILURE",
  "ERROR",
  "CANCELLED",
  "TIMED_OUT",
  "STARTUP_FAILURE",
  "ACTION_REQUIRED",
  "STALE",
]);
const CHECK_PENDING = new Set(["PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "EXPECTED"]);

function countChecks(contexts: any): Checks {
  const out = { pass: 0, pending: 0, fail: 0 };
  const buckets = [...(contexts?.checkRunCountsByState ?? []), ...(contexts?.statusContextCountsByState ?? [])];
  for (const { state, count } of buckets) {
    if (CHECK_FAIL.has(state)) out.fail += count;
    else if (CHECK_PENDING.has(state)) out.pending += count;
    else out.pass += count;
  }
  return out;
}

function buildQuery(prs: Tracked[]): string {
  const fields = prs
    .map(
      (p, i) => `p${i}: repository(owner: ${JSON.stringify(p.owner)}, name: ${JSON.stringify(p.repo)}) {
  pullRequest(number: ${p.number}) {
    title state isDraft reviewDecision mergeable
    reviewThreads(first: 100) { nodes { isResolved } }
    commits(last: 1) { nodes { commit { statusCheckRollup { state contexts(first: 1) {
      checkRunCountsByState { state count } statusContextCountsByState { state count }
    } } } } }
  }
}`,
    )
    .join("\n");
  return `query {\n${fields}\n}`;
}

export default function (pi: ExtensionAPI) {
  let prs: Tracked[] = [];
  let ctx: ExtensionContext | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let inFlight = false;
  let lastRefresh = 0;
  let failures = 0;
  let visible = true;

  // ── state ───────────────────────────────────────────────────────────────

  // Replays the active branch in order: PRs created by earlier tool calls
  // (including sessions that predate this extension) plus explicit add/remove
  // entries, so a later remove still wins over an earlier detection.
  function reconstruct(c: ExtensionContext) {
    const urls = new Map<string, Tracked>();
    const inputs = new Map<string, unknown>();
    const add = (url: string) => {
      const pr = parsePr(url);
      if (pr && !urls.has(pr.url)) urls.set(pr.url, prs.find((p) => p.url === pr.url) ?? pr);
    };
    for (const entry of c.sessionManager.getBranch()) {
      if (entry.type === "message") {
        const msg = entry.message as any;
        if (msg.role === "assistant" && Array.isArray(msg.content)) {
          for (const part of msg.content) if (part?.type === "toolCall") inputs.set(part.id, part.arguments);
        } else if (msg.role === "toolResult") {
          const found = createdPrUrls(msg.toolName, inputs.get(msg.toolCallId), resultText(msg.content), msg.isError);
          found.forEach(add);
        }
        continue;
      }
      if (entry.type !== "custom" || entry.customType !== ENTRY) continue;
      const data = entry.data as { action: "add" | "remove"; url: string };
      if (data.action === "add") add(data.url);
      else urls.delete(data.url);
    }
    prs = [...urls.values()];
  }

  function track(url: string): boolean {
    const pr = parsePr(url);
    if (!pr || prs.some((p) => p.url === pr.url)) return false;
    prs.push(pr);
    pi.appendEntry(ENTRY, { action: "add", url: pr.url });
    return true;
  }

  function untrack(pr: Tracked) {
    prs = prs.filter((p) => p !== pr);
    pi.appendEntry(ENTRY, { action: "remove", url: pr.url });
  }

  // ── polling ─────────────────────────────────────────────────────────────

  function nextDelay(): number | undefined {
    if (failures > 0) return Math.min(FAST_MS * 2 ** failures, MAX_BACKOFF_MS);
    const open = prs.filter((p) => !p.status || p.status.state === "OPEN");
    if (open.length === 0) return undefined;
    return open.some((p) => !p.status || p.status.checks.pending > 0) ? FAST_MS : SLOW_MS;
  }

  function schedule() {
    if (timer) clearTimeout(timer);
    timer = undefined;
    const delay = nextDelay();
    if (delay !== undefined) timer = setTimeout(() => void refresh(), delay);
  }

  async function fetchHost(host: string, group: Tracked[]) {
    const args = ["api", "graphql", "-f", `query=${buildQuery(group)}`];
    if (host !== "github.com") args.push("--hostname", host);
    const res = await pi.exec("gh", args, { timeout: 30_000 });
    let body: any;
    try {
      body = JSON.parse(res.stdout);
    } catch {
      throw new Error(res.stderr.trim() || `gh exited ${res.code}`);
    }
    if (!body?.data) throw new Error(body?.errors?.[0]?.message ?? (res.stderr.trim() || "no data"));
    group.forEach((p, i) => {
      const pr = body.data[`p${i}`]?.pullRequest;
      if (!pr) {
        p.error = body.errors?.find((e: any) => e.path?.[0] === `p${i}`)?.message ?? "not found";
        return;
      }
      p.error = undefined;
      const rollup = pr.commits?.nodes?.[0]?.commit?.statusCheckRollup;
      const next: PrStatus = {
        title: pr.title,
        state: pr.state,
        isDraft: pr.isDraft,
        review: pr.reviewDecision,
        mergeable: pr.mergeable,
        rollup: rollup?.state ?? null,
        checks: countChecks(rollup?.contexts),
        unresolved: (pr.reviewThreads?.nodes ?? []).filter((t: any) => !t.isResolved).length,
      };
      announce(p, p.status, next);
      p.status = next;
    });
  }

  function announce(p: Tracked, prev: PrStatus | undefined, next: PrStatus) {
    if (!prev || !ctx?.hasUI) return;
    const label = `#${p.number} ${p.repo}`;
    if (prev.state !== next.state && next.state !== "OPEN")
      ctx.ui.notify(`${label} ${next.state.toLowerCase()}`, "info");
    else if (prev.rollup !== next.rollup && next.rollup === "FAILURE")
      ctx.ui.notify(`${label}: checks failed`, "error");
    else if (prev.rollup !== next.rollup && next.rollup === "SUCCESS") ctx.ui.notify(`${label}: checks passed`, "info");
    else if (prev.review !== next.review && next.review === "CHANGES_REQUESTED")
      ctx.ui.notify(`${label}: changes requested`, "warning");
    else if (prev.review !== next.review && next.review === "APPROVED") ctx.ui.notify(`${label}: approved`, "info");
  }

  async function refresh(force = false) {
    if (inFlight || prs.length === 0) return schedule();
    if (!force && Date.now() - lastRefresh < MIN_GAP_MS) return schedule();
    inFlight = true;
    lastRefresh = Date.now();
    try {
      const active = prs.filter((p) => !p.status || p.status.state === "OPEN" || force);
      const byHost = new Map<string, Tracked[]>();
      for (const p of active) byHost.set(p.host, [...(byHost.get(p.host) ?? []), p]);
      const results = await Promise.allSettled([...byHost].map(([h, g]) => fetchHost(h, g)));
      const failed = results.find((r): r is PromiseRejectedResult => r.status === "rejected");
      failures = failed ? failures + 1 : 0;
      if (failed) for (const p of active) p.error ??= String(failed.reason?.message ?? failed.reason);
    } finally {
      inFlight = false;
      render();
      schedule();
    }
  }

  // ── rendering ───────────────────────────────────────────────────────────

  function rank(p: Tracked): number {
    const s = p.status;
    if (!s) return 2;
    if (s.state !== "OPEN") return 5;
    if (s.checks.fail > 0 || s.review === "CHANGES_REQUESTED" || s.mergeable === "CONFLICTING") return 0;
    if (s.checks.pending > 0) return 1;
    return 3;
  }

  function render() {
    if (!ctx?.hasUI) return;
    if (prs.length === 0) {
      ctx.ui.setWidget(ENTRY, undefined);
      ctx.ui.setStatus(ENTRY, undefined);
      return;
    }

    const open = prs.filter((p) => p.status?.state !== "MERGED" && p.status?.state !== "CLOSED");
    const failing = open.filter((p) => rank(p) === 0).length;
    const pending = open.filter((p) => rank(p) === 1).length;
    const summary = [`PRs ${open.length} open`, failing && `✗${failing}`, pending && `●${pending}`]
      .filter(Boolean)
      .join(" ");
    ctx.ui.setStatus(ENTRY, summary);

    if (!visible) return ctx.ui.setWidget(ENTRY, undefined);

    const sorted = [...prs].sort((a, b) => rank(a) - rank(b) || b.number - a.number);
    const shown = sorted.slice(0, WIDGET_MAX);
    const hidden = sorted.length - shown.length;

    ctx.ui.setWidget(
      ENTRY,
      (_tui, theme) => ({
        invalidate() {},
        render(width: number): string[] {
          const lines = shown.map((p) => {
            const s = p.status;
            const link = `\x1b]8;;${p.url}\x07#${p.number}\x1b]8;;\x07`;
            let icon = theme.fg("dim", "○");
            const parts: string[] = [];
            if (s) {
              if (s.state === "MERGED") icon = theme.fg("accent", "⇣");
              else if (s.state === "CLOSED") icon = theme.fg("dim", "✕");
              else if (s.isDraft) icon = theme.fg("muted", "◌");
              else icon = theme.fg("success", "●");

              if (s.state === "OPEN") {
                const c = s.checks;
                if (c.pass) parts.push(theme.fg("success", `✓${c.pass}`));
                if (c.pending) parts.push(theme.fg("warning", `●${c.pending}`));
                if (c.fail) parts.push(theme.fg("error", `✗${c.fail}`));
                if (s.review === "APPROVED") parts.push(theme.fg("success", "approved"));
                else if (s.review === "CHANGES_REQUESTED") parts.push(theme.fg("error", "changes"));
                else if (s.review === "REVIEW_REQUIRED") parts.push(theme.fg("dim", "review"));
                if (s.unresolved) parts.push(theme.fg("warning", `💬${s.unresolved}`));
                if (s.mergeable === "CONFLICTING") parts.push(theme.fg("error", "conflict"));
              } else parts.push(theme.fg("dim", s.state.toLowerCase()));
            }
            if (p.error) parts.push(theme.fg("error", "⚠"));
            const title = s ? s.title : theme.fg("dim", "loading…");
            const head = `${icon} ${link} ${theme.fg("muted", p.repo)} `;
            const tail = parts.length ? `  ${parts.join(" ")}` : "";
            const room = Math.max(8, width - visibleWidth(head) - visibleWidth(tail));
            return truncateToWidth(`${head}${truncateToWidth(title, room)}${tail}`, width);
          });
          if (hidden > 0) lines.push(theme.fg("dim", `  +${hidden} more · /prs to list`));
          return lines;
        },
      }),
      { placement: "belowEditor" },
    );
  }

  // ── events ──────────────────────────────────────────────────────────────

  function start(c: ExtensionContext) {
    ctx = c;
    failures = 0;
    reconstruct(c);
    render();
    void refresh(true);
  }

  pi.on("session_start", async (_e, c) => start(c));
  pi.on("session_tree", async (_e, c) => start(c));
  pi.on("session_shutdown", async () => {
    if (timer) clearTimeout(timer);
    timer = undefined;
  });

  pi.on("tool_result", async (event) => {
    const urls = createdPrUrls(event.toolName, event.input, resultText(event.content), event.isError);
    let added = false;
    for (const url of urls) added = track(url) || added;
    const command = event.toolName === "bash" ? String((event.input as { command?: string })?.command ?? "") : "";
    if (added) render();
    if (added || REFRESH_TRIGGER.test(command)) void refresh(added);
  });

  pi.on("agent_end", async () => void refresh());

  // ── command ─────────────────────────────────────────────────────────────

  pi.registerCommand("prs", {
    description: "Tracked PRs: toggle widget, or add <url> | rm <url|#n> | refresh | list",
    handler: async (args, c) => {
      ctx = c;
      const [sub, arg] = args.trim().split(/\s+/);
      if (!sub) {
        visible = !visible;
        render();
        return;
      }
      if (sub === "add") {
        if (!arg || !track(arg)) return c.ui.notify("Usage: /prs add <PR url> (not already tracked)", "error");
        render();
        return refresh(true);
      }
      if (sub === "rm") {
        const n = arg?.replace(/^#/, "");
        const pr = prs.find((p) => p.url === parsePr(arg ?? "")?.url || String(p.number) === n);
        if (!pr) return c.ui.notify(`Not tracked: ${arg ?? ""}`, "error");
        untrack(pr);
        render();
        return schedule();
      }
      if (sub === "refresh") return refresh(true);
      if (sub === "list") {
        if (prs.length === 0) return c.ui.notify("No tracked PRs", "info");
        const items = prs.map(
          (p) => `#${p.number} ${p.repo} ${p.status?.state.toLowerCase() ?? "?"} — ${p.status?.title ?? p.url}`,
        );
        const picked = await c.ui.select("Tracked PRs (enter opens in browser)", items);
        const pr = picked ? prs[items.indexOf(picked)] : undefined;
        if (pr) await pi.exec("open", [pr.url]);
        return;
      }
      c.ui.notify("Usage: /prs [add <url> | rm <url|#n> | refresh | list]", "error");
    },
  });
}
