/**
 * rex-session-start extension
 *
 * Pi has no command hooks, so `rex skill setup` cannot install the
 * SessionStart hook it gives Claude Code. This extension runs the same
 * command and adds its output to the system prompt as a `rex` section: the
 * Rex session and pane IDs, and the instruction to name the Rex session
 * after the task.
 *
 * Outside a Rex terminal the command prints nothing and no section is added.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  if (!process.env.REX_SESSION) return;

  let text = "";

  pi.on("session_start", async () => {
    try {
      const result = await pi.exec("rex", ["__internal", "session-start", "--agent", "pi"], {
        timeout: 10_000,
      });
      text = result.code === 0 ? result.stdout.trim() : "";
    } catch {
      text = "";
    }
  });

  pi.on("before_agent_start", async (event) => {
    if (text) event.systemPromptOptions.sections.rex = text;
  });
}
