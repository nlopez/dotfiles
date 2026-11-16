/**
 * Git Bypass Guard
 *
 * Blocks bash calls that skip git hooks or disable commit signing
 * (--no-verify, --no-gpg-sign, commit.gpgsign=false, ...). The rules live in
 * ~/.config/git/agent-bypass-guard, shared with the Claude Code hook.
 */

import { spawnSync } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const GUARD = join(homedir(), ".config/git/agent-bypass-guard");

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;
    const command = (event.input as { command?: string }).command ?? "";
    if (!/git|gpgsign|GIT_CONFIG/i.test(command)) return undefined;

    const result = spawnSync(GUARD, {
      input: JSON.stringify({ tool_input: { command } }),
      encoding: "utf8",
    });
    if (result.status !== 2) return undefined;

    const reason = result.stderr.trim();
    ctx.ui.notify("Blocked git hook/signing bypass", "warning");
    return { block: true, reason };
  });
}
