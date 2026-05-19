/**
 * draft-pr extension
 *
 * Intercepts any `gh pr create` command and ensures it always includes
 * the --draft flag. If --draft is already present the command is left
 * unchanged. If it is absent the flag is injected (before the first
 * newline / end of command) and the user is notified.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (!isToolCallEventType("bash", event)) return;

    const { command } = event.input;
    if (!command) return;

    // Only act on lines that contain `gh pr create`.
    if (!command.includes("gh pr create")) return;

    // Already a draft – nothing to do.
    if (/--draft\b|-d\b/.test(command)) return;

    // Inject --draft right after `gh pr create`.
    event.input.command = command.replace(
      /(gh\s+pr\s+create)/,
      "$1 --draft",
    );

    ctx.ui.notify("Injected --draft into gh pr create", "info");
  });
}
