/**
 * gh-attribution extension
 *
 * Appends a Pi co-authorship footer to the --body of any gh CLI call
 * that posts or edits GitHub content, whether issued by the agent (tool_call)
 * or by the user inside the pi prompt via ! / !! (user_bash).
 *
 * Covered subcommands: gh {pr,issue} {create,edit,comment,review} --body "..."
 *
 * Works on compound shell commands (e.g. `cd /path && gh pr edit 1 --body "..."`)
 * by operating on the raw command string before execution.
 *
 * Known limitations:
 * - --body-file is not intercepted (can't modify file content inline)
 * - $'...' ANSI-C quoting is not intercepted
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

// gh subcommands that post or edit content and accept --body
const GH_CONTENT_RE =
  /\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|review)\b/;

/**
 * Inject the Pi attribution footer into all --body "..." or --body '...'
 * occurrences in a shell command string that contain a gh content subcommand.
 * Returns null when no change was needed.
 */
function injectAttribution(command: string, footer: string): string | null {
  if (!GH_CONTENT_RE.test(command)) return null;
  if (!command.includes("--body")) return null;
  if (command.includes("Co-authored with Pi")) return null; // idempotent

  let modified = false;

  // Non-greedy prefix ensures each --body pairs with its nearest gh call.
  // Handles compound commands (&&, ||, ;) and multi-line continuations (\\\n).
  const result = command.replace(
    /(\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|review)\b[\s\S]*?)--body\s+("((?:[^"\\]|\\[\s\S])*)"|'((?:[^'\\]|\\.)*)')/g,
    (_match, prefix, _quoted, dqBody, sqBody) => {
      modified = true;
      const body = dqBody !== undefined ? dqBody : sqBody;
      // Always emit double-quoted; escape any embedded double quotes in body.
      const safeBody = body.replace(/"/g, '\\"');
      return `${prefix}--body "${safeBody}${footer}"`;
    },
  );

  return modified ? result : null;
}

export default function (pi: ExtensionAPI) {
  // ── Agent bash tool calls ────────────────────────────────────────────────
  pi.on("tool_call", async (event, ctx) => {
    if (!isToolCallEventType("bash", event)) return;

    const { command } = event.input;
    if (!command) return;

    const modelName = ctx.model?.name ?? "";
    const footer = `\n\n---\n*Co-authored with Pi${modelName ? ` (${modelName})` : ""}*`;

    const patched = injectAttribution(command, footer);
    if (patched !== null) {
      event.input.command = patched;
      ctx.ui.notify("Appended Pi attribution to gh --body", "info");
    }
  });

  // ── User-typed ! / !! commands inside the pi prompt ─────────────────────
  pi.on("user_bash", (event, _ctx) => {
    const modelName = _ctx.model?.name ?? "";
    const footer = `\n\n---\n*Co-authored with Pi${modelName ? ` (${modelName})` : ""}*`;

    const patched = injectAttribution(event.command, footer);
    if (patched === null) return;

    // Wrap pi's local bash backend with the patched command.
    // createLocalBashOperations() is the built-in executor.
    const { createLocalBashOperations } =
      require("@earendil-works/pi-coding-agent") as typeof import("@earendil-works/pi-coding-agent");
    const local = createLocalBashOperations();
    return {
      operations: {
        exec(
          _command: string,
          cwd: string,
          options: Parameters<typeof local.exec>[2],
        ) {
          return local.exec(patched, cwd, options);
        },
      },
    };
  });
}
