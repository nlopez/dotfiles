/**
 * Rm Guard
 *
 * Blocks bash calls that delete files permanently (rm, find -delete) and
 * points the agent at `trash`. The rules live in ~/.local/bin/agent-rm-guard,
 * shared with the Claude Code hook.
 */

import { spawnSync } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const GUARD = join(homedir(), ".local/bin/agent-rm-guard");

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;
    const command = (event.input as { command?: string }).command ?? "";
    if (!/\brm\b|-delete/.test(command)) return undefined;

    const result = spawnSync(GUARD, {
      input: JSON.stringify({ tool_input: { command } }),
      encoding: "utf8",
    });
    if (result.status !== 2) return undefined;

    const reason = result.stderr.trim();
    ctx.ui.notify("Blocked permanent delete; use trash", "warning");
    return { block: true, reason };
  });
}
