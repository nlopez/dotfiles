/**
 * chezmoi-reload extension
 *
 * Watches a sentinel file written by the chezmoi run_onchange_after_reload-shells
 * script and triggers a Pi reload (extensions, skills, prompts, themes) once the
 * agent is idle — without injecting any keystrokes into the tmux pane.
 *
 * Flow:
 *   chezmoi apply
 *     └─► run_onchange_after_reload-shells writes ~/.local/state/chezmoi-pi-reload
 *           └─► this extension detects the file (via fs.watchFile polling)
 *                 └─► deletes the file to prevent double-trigger
 *                       └─► queues /chezmoi-reload as a follow-up message
 *                             └─► command handler calls ctx.reload()
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { watchFile, unwatchFile, existsSync, unlinkSync } from "node:fs";
import { join } from "node:path";

const SENTINEL = join(process.env.HOME ?? "", ".local", "state", "chezmoi-pi-reload");
const POLL_INTERVAL_MS = 2000;

export default function (pi: ExtensionAPI) {
  // ── Command: the actual reload handler ──────────────────────────────────────
  // ctx.reload() is only available in ExtensionCommandContext (command handlers),
  // so the file-watcher below queues this command rather than calling reload directly.
  pi.registerCommand("chezmoi-reload", {
    description: "Internal: reload extensions/skills/prompts triggered by chezmoi apply",
    handler: async (_args, ctx) => {
      await ctx.reload();
    },
  });

  // ── Watcher lifecycle ────────────────────────────────────────────────────────
  let watching = false;

  function startWatcher() {
    if (watching) return;
    watching = true;

    watchFile(SENTINEL, { interval: POLL_INTERVAL_MS, persistent: false }, (curr) => {
      // curr.nlink === 0 means the file does not exist (stat returned ENOENT).
      if (curr.nlink === 0) return;

      // File appeared — consume it immediately to prevent re-triggering.
      try {
        unlinkSync(SENTINEL);
      } catch {
        // Another process beat us to it; safe to ignore.
        return;
      }

      // Queue the reload to fire once the agent finishes any in-progress turn.
      // deliverAs: "followUp" waits until the agent is fully idle, so Pi is
      // never interrupted mid-response.
      pi.sendUserMessage("/chezmoi-reload", { deliverAs: "followUp" });
    });
  }

  function stopWatcher() {
    if (!watching) return;
    watching = false;
    unwatchFile(SENTINEL);
  }

  // ── Session lifecycle ────────────────────────────────────────────────────────
  pi.on("session_start", () => {
    // Also handle the case where the sentinel was written before Pi started:
    // the first watchFile stat call will fire immediately if the file exists.
    startWatcher();
  });

  pi.on("session_shutdown", () => {
    stopWatcher();
  });
}
