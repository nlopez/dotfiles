/**
 * gh-attribution extension
 *
 * Appends a Pi co-authorship footer to GitHub content posted via gh CLI,
 * whether issued by the agent (tool_call) or the user inside the pi prompt
 * via ! / !! (user_bash).
 *
 * Covered subcommands: gh {pr,issue} {create,edit,comment,review}
 *                      gh api .../pulls/<n>/comments/<n>/replies
 *
 * Two body delivery mechanisms are handled:
 *   --body "..."      → footer appended to the inline string in the command
 *   --body-file <path> → footer appended to the file on disk before gh reads it
 *                        (-F <path> shorthand also supported; stdin "-" is skipped)
 *
 * Works on compound shell commands (e.g. `cd /path && gh pr edit 1 --body "..."`)
 * by operating on the raw command string before execution.
 *
 * Known limitations:
 * - --body-file - (stdin) cannot be intercepted
 * - $'...' ANSI-C quoting in --body is not intercepted
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

// gh subcommands that post or edit content
const GH_CONTENT_RE = /\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|review)\b/;

/**
 * Matches a Pi footer at the end of a body (actual newlines, optional trailing whitespace).
 * Used to strip any pre-existing footer before appending a fresh one, ensuring that
 * multiple edits to the same PR/issue never accumulate duplicate footers.
 */
const FOOTER_RE = /\r?\n\r?\n---\r?\n\*Co-authored with Pi[^*]*\*\s*$/;

/** Remove any existing Pi footer from a body string. */
function stripFooter(body: string): string {
  return body.replace(FOOTER_RE, "");
}

// Matches --body-file <path> or -F <path> (quoted or unquoted, not stdin)
const BODY_FILE_RE = /(?:--body-file|-F)\s+(?:"([^"]+)"|'([^']+)'|(?!-)(\S+))/;

// gh api calls to PR review-comment reply endpoints
// e.g.: gh api repos/owner/repo/pulls/123/comments/456/replies -f body="..."
const GH_API_REPLY_RE = /\bgh\s+api\b[\s\S]*?\/pulls\/\d+\/comments\/\d+\/replies\b/;

/** Build the footer string from the current model name. */
function buildFooter(modelName: string): string {
  return `\n\n---\n*Co-authored with Pi${modelName ? ` (${modelName})` : ""}*`;
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
 * Append the footer to a --body-file target on disk.
 * Resolves relative paths against `cwd`. Skips stdin ("-").
 * Returns true if the file was modified.
 */
function injectBodyFile(command: string, footer: string, cwd: string): boolean {
  if (!BODY_FILE_RE.test(command)) return false;

  const m = command.match(BODY_FILE_RE);
  if (!m) return false;

  const rawPath = m[1] ?? m[2] ?? m[3];
  if (!rawPath || rawPath === "-") return false; // stdin — uninterceptable

  const filePath = resolve(cwd, rawPath);
  let content: string;
  try {
    content = readFileSync(filePath, "utf8");
  } catch {
    return false; // file doesn't exist yet or unreadable — skip
  }

  // Strip any existing footer first so repeated edits never accumulate duplicates.
  const newContent = stripFooter(content) + footer;
  if (newContent === content) return false; // already exactly correct, skip write

  writeFileSync(filePath, newContent, "utf8");
  return true;
}

/** Apply all strategies to a command; returns what changed. */
function applyAttribution(command: string, footer: string, cwd: string): { command: string; modified: boolean } {
  if (GH_CONTENT_RE.test(command)) {
    const inlined = injectInlineBody(command, footer);
    if (inlined !== null) return { command: inlined, modified: true };

    const filePatched = injectBodyFile(command, footer, cwd);
    return { command, modified: filePatched };
  }

  if (GH_API_REPLY_RE.test(command)) {
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
