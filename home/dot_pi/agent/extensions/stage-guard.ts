/**
 * Stage Guard
 *
 * Blocks bash calls that stage every change in the work tree (git add -A, .,
 * -u; git commit -a), which would commit other sessions' unfinished edits.
 * The rules live in ~/.local/bin/agent-stage-guard, shared with the Claude
 * Code hook.
 */

import { spawnSync } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const GUARD = join(homedir(), ".local/bin/agent-stage-guard");

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;
    const command = (event.input as { command?: string }).command ?? "";
    if (!/\bgit\b/.test(command)) return undefined;

    const result = spawnSync(GUARD, {
      input: JSON.stringify({ tool_input: { command } }),
      encoding: "utf8",
    });
    if (result.status !== 2) return undefined;

    const reason = result.stderr.trim();
    ctx.ui.notify("Blocked blanket git staging; stage paths explicitly", "warning");
    return { block: true, reason };
  });
}
