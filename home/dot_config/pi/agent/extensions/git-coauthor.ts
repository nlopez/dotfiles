/**
 * git-coauthor extension
 *
 * Injects a "Co-authored-by: Pi" trailer into git commit commands run by the
 * agent via the bash tool. Only commits Pi actually executes are attributed —
 * manual commits you type yourself are never touched.
 *
 * Uses --trailer (git >= 2.32) so git's own deduplication rules apply:
 * amending a commit that already carries the trailer won't produce a duplicate.
 *
 * Works on compound commands (e.g. `cd /path && git commit -m "msg"`).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

// Matches `git commit` but not `git commit-graph`, `git commit-tree`, etc.
const GIT_COMMIT_RE = /\bgit\s+commit\b/;

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (!isToolCallEventType("bash", event)) return;

    const { command } = event.input;
    if (!command || !GIT_COMMIT_RE.test(command)) return;

    // Idempotent: skip if the trailer is already present (e.g. on retry).
    if (command.includes("Co-authored-by: Pi")) return;

    const modelId = ctx.model?.id ?? "";
    const email = modelId ? `noreply+${modelId}@example.org` : `noreply@example.org`;
    const trailer = `Co-authored-by: Pi <${email}>`;

    // Inject --trailer after every `git commit` in the command.
    // Handles compound commands: cd /path && git commit -m "msg"
    event.input.command = command.replace(/\bgit(\s+commit\b)/g, `git$1 --trailer "${trailer}"`);
  });
}
