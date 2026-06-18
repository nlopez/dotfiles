/**
 * gh-attribution extension
 *
 * Appends a Pi co-authorship footer to GitHub content posted via gh CLI,
 * whether issued by the agent (tool_call) or the user inside the pi prompt
 * via ! / !! (user_bash).
 *
 * Covered subcommands: gh {pr,issue} {create,edit,comment,review}
 *                      gh api .../pulls/<n>/comments/<n>/replies
 *                      gh api -X PATCH .../pulls/<n>  (direct REST body update)
 *                      gh api -X PATCH .../issues/<n> (direct REST body update)
 *
 * Two body delivery mechanisms are handled:
 *   --body "..."      → footer appended to the inline string in the command
 *   --body-file <path> → footer appended to the file on disk before gh reads it
 *                        (-F <path> shorthand also supported; stdin "-" is skipped)
 *
 *   If --body-file references a file that doesn't exist yet at interception time
 *   (e.g. the file is written by a heredoc earlier in the same compound bash call),
 *   a deferred `printf '%b' '...' >> <file>` is injected into the command string
 *   immediately before the `gh` invocation.  A `grep -qF` guard prevents double-
 *   attribution if the same command block is re-run without recreating the file.
 *
 * Works on compound shell commands (e.g. `cd /path && gh pr edit 1 --body "..."`)
 * by operating on the raw command string before execution.
 *
 * The footer is always placed at the very end of the body. Any pre-existing Pi
 * footer found anywhere in the body (not just at the end) is stripped before the
 * fresh footer is appended, so repeated edits — including cases where content was
 * added after a previous footer — never accumulate duplicates.
 *
 * Note: gh pr/issue comment --edit-last is handled correctly; --body is injected
 * the same way as for new comments and the existing footer is stripped globally.
 *
 * Known limitations:
 * - --body-file - (stdin) cannot be intercepted
 * - $'...' ANSI-C quoting in --body is not intercepted
 * - --editor / --web flags open an external editor or browser and cannot be intercepted
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

// gh subcommands that post or edit content
const GH_CONTENT_RE = /\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|review)\b/;

/**
 * Matches a Pi footer anywhere in a body (global, not end-anchored).
 * Intentionally does NOT consume the trailing newline after the footer line —
 * that lets the regex match two back-to-back footers in a single pass (the
 * \n\n separator between them stays intact for the second match), and any
 * leftover newlines are cleaned up by the subsequent trimEnd in stripFooter.
 *
 * ⚠️  This regex has the `g` flag — always reset lastIndex before reuse.
 */
const FOOTER_RE = /\r?\n\r?\n---\r?\n\*Co-authored with \[Pi\][^*]*\*[ \t]*/g;

/**
 * Remove every Pi footer from a body string and trim trailing CR/LF chars.
 * Trimming ensures the fresh footer's leading \n\n is the only separator
 * between the body content and the attribution line, regardless of how many
 * blank lines or CRLF endings were left behind after stripping.
 */
function stripFooter(body: string): string {
  FOOTER_RE.lastIndex = 0;
  return body.replace(FOOTER_RE, "").replace(/[\r\n]+$/, "");
}

// Matches --body-file <path> or -F <path> (quoted or unquoted, not stdin)
const BODY_FILE_RE = /(?:--body-file|-F)\s+(?:"([^"]+)"|'([^']+)'|(?!-)(\S+))/;

// gh api calls to PR review-comment reply endpoints
// e.g.: gh api repos/owner/repo/pulls/123/comments/456/replies -f body="..."
const GH_API_REPLY_RE = /\bgh\s+api\b[\s\S]*?\/pulls\/\d+\/comments\/\d+\/replies\b/;

// gh api -X PATCH calls that update the top-level body of a PR or issue directly.
// e.g.: gh api -X PATCH repos/owner/repo/pulls/1 -f body="..."
//       gh api -X PATCH repos/owner/repo/issues/1 -f body="..."
// The (?!\/) lookahead prevents matching sub-resource paths like /pulls/1/reviews.
const GH_API_PATCH_RE = /\bgh\s+api\b[\s\S]*?-X\s+PATCH\b[\s\S]*?\/(?:pulls|issues)\/\d+(?!\/)/;

/** Build the footer string from the current model name. */
function buildFooter(modelName: string): string {
  return `\n\n---\n*Co-authored with [Pi](https://pi.dev)${modelName ? ` (${modelName})` : ""}*`;
}

/**
 * Rewrite --body "..." / --body '...' occurrences in a shell command string.
 * Returns null when nothing matched or was already attributed.
 */
function injectInlineBody(command: string, footer: string): string | null {
  if (!command.includes("--body")) return null;

  let modified = false;
  const result = command.replace(
    /(\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|review)\b[\s\S]*?)--body\s+("((?:[^"\\]|\\[\s\S])*)"|'((?:[^'\\]|\\.)*)')/g,
    (_match, prefix, _quoted, dqBody, sqBody) => {
      modified = true;
      const body = dqBody !== undefined ? dqBody : sqBody;
      // Strip any existing footer first so repeated edits never accumulate duplicates.
      const safeBody = stripFooter(body).replace(/"/g, '\\"');
      return `${prefix}--body "${safeBody}${footer}"`;
    },
  );
  return modified ? result : null;
}

/**
 * Rewrite -f body=... / -F body=... in a `gh api` reply call.
 * Returns null if nothing matched or footer is already present.
 */
function injectApiReplyBody(command: string, footer: string): string | null {
  let modified = false;
  const result = command.replace(
    /(-[fF]\s+body=|--(?:field|raw-field)\s+body=)("((?:[^"\\]|\\[\s\S])*)"|'((?:[^'\\]|\\[\s\S])*)'|(\S+))/g,
    (_match, flagPrefix, _quoted, dqBody, sqBody, bareBody) => {
      modified = true;
      const body = dqBody !== undefined ? dqBody : sqBody !== undefined ? sqBody : bareBody ?? "";
      // Strip any existing footer first so repeated edits never accumulate duplicates.
      const safeBody = stripFooter(body).replace(/"/g, '\\"');
      return `${flagPrefix}"${safeBody}${footer}"`;
    },
  );
  return modified ? result : null;
}

/**
 * Escape a string for safe embedding inside a single-quoted POSIX shell argument.
 * Single quotes themselves become '\''  (end-quote, escaped-quote, re-open-quote).
 * Literal newlines become the \n escape sequence so that
 * `printf '<result>'` reproduces them correctly.
 */
function shellEscapeForPrintf(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/'/g, "'\\''").replace(/\n/g, "\\n");
}

/**
 * Append the footer to a --body-file target on disk.
 * Resolves relative paths against `cwd`. Skips stdin ("-").
 *
 * Returns:
 *   true          — file was patched in-place (it existed at hook time)
 *   string        — a modified command string with a deferred `printf >> <file>`
 *                   injected just before the `gh` invocation (file didn't exist yet,
 *                   e.g. it's created by a heredoc earlier in the same compound command)
 *   false         — nothing could be done (no --body-file flag, stdin, or unresolvable)
 */
function injectBodyFile(command: string, footer: string, cwd: string): string | boolean {
  if (!BODY_FILE_RE.test(command)) return false;

  const m = command.match(BODY_FILE_RE);
  if (!m) return false;

  const rawPath = m[1] ?? m[2] ?? m[3];
  if (!rawPath || rawPath === "-") return false; // stdin — uninterceptable

  const filePath = resolve(cwd, rawPath);
  let content: string;
  try {
    content = readFileSync(filePath, "utf8");
    // File exists — patch it in-place (fast path).
    // Strip any existing footer first so repeated edits never accumulate duplicates.
    const newContent = stripFooter(content) + footer;
    if (newContent === content) return false; // already exactly correct, skip write
    writeFileSync(filePath, newContent, "utf8");
    return true;
  } catch {
    // File doesn't exist yet — it will be created by an earlier step in the same
    // compound command (e.g. a heredoc).  Fall through to deferred injection.
  }

  // Deferred strategy: inject a `printf >> <file>` shell command immediately
  // before the `gh` invocation so the footer is appended at execution time.
  //
  // We guard with `grep -qF` so that re-running the same command block never
  // produces duplicate footers (the heredoc recreates the file, but just in case).
  const ghIdx = command.search(GH_CONTENT_RE);
  if (ghIdx === -1) return false;

  const escapedFooter = shellEscapeForPrintf(footer);
  // Use a shell group so the guard + append + gh all share one exit-status chain.
  // The printf uses %b to expand \n sequences.
  const appendCmd = `grep -qF 'Co-authored with [Pi]' ${rawPath} 2>/dev/null || printf '%b' '${escapedFooter}' >> ${rawPath}`;

  const before = command.slice(0, ghIdx);
  const after = command.slice(ghIdx);

  // Choose a separator that fits the surrounding context.
  // If `before` already ends with a newline (heredoc EOF on its own line), just
  // add the command on the next line joined with &&; otherwise use ' && \n'.
  const sep = /\n\s*$/.test(before) ? "" : " && \n";
  return `${before}${sep}${appendCmd} && \\
${after}`;
}

/** Apply all strategies to a command; returns what changed. */
function applyAttribution(command: string, footer: string, cwd: string): { command: string; modified: boolean } {
  if (GH_CONTENT_RE.test(command)) {
    const inlined = injectInlineBody(command, footer);
    if (inlined !== null) return { command: inlined, modified: true };

    const fileResult = injectBodyFile(command, footer, cwd);
    if (typeof fileResult === "string") return { command: fileResult, modified: true };
    return { command, modified: fileResult };
  }

  if (GH_API_REPLY_RE.test(command) || GH_API_PATCH_RE.test(command)) {
    const rewritten = injectApiReplyBody(command, footer);
    if (rewritten !== null) return { command: rewritten, modified: true };
  }

  return { command, modified: false };
}

export default function (pi: ExtensionAPI) {
  // ── Agent bash tool calls ────────────────────────────────────────────────
  pi.on("tool_call", async (event, ctx) => {
    if (!isToolCallEventType("bash", event)) return;

    const { command } = event.input;
    if (!command) return;

    const footer = buildFooter(ctx.model?.name ?? "");
    const { command: patched, modified } = applyAttribution(command, footer, ctx.cwd);

    if (modified) {
      event.input.command = patched;
      ctx.ui.notify("Appended Pi attribution to gh --body", "info");
    }
  });

  // ── User-typed ! / !! commands inside the pi prompt ─────────────────────
  pi.on("user_bash", (event, ctx) => {
    const footer = buildFooter(ctx.model?.name ?? "");
    const { command: patched, modified } = applyAttribution(event.command, footer, ctx.cwd);

    if (!modified) return;

    const { createLocalBashOperations } =
      require("@earendil-works/pi-coding-agent") as typeof import("@earendil-works/pi-coding-agent");
    const local = createLocalBashOperations();
    return {
      operations: {
        exec(_command: string, cwd: string, options: Parameters<typeof local.exec>[2]) {
          return local.exec(patched, cwd, options);
        },
      },
    };
  });
}
