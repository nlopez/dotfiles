/**
 * tmux-status extension
 *
 * Sends a macOS terminal-notifier notification when the agent finishes
 * ("Complete", or "Waiting for input" if the last message ends with "?").
 * Clicking it switches to the tmux window and focuses the terminal.
 *
 * Window status markers are handled by tmux-agent-tabs (its pi-hook.ts),
 * and the pane picker by `tap`; this extension no longer touches tmux state.
 *
 * pi runs directly inside the tmux pane, so TMUX_PANE comes from the
 * environment.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // Only activate inside tmux.
  const tmuxPane = process.env.TMUX_PANE;
  if (!process.env.TMUX || !tmuxPane) return;

  // ── helpers ──────────────────────────────────────────────────────────────

  async function notify(message: string): Promise<void> {
    const { stdout: info } = await pi.exec("tmux", [
      "display-message",
      "-p",
      "-t",
      tmuxPane,
      "#{session_name} #{window_index} #{window_name}",
    ]);
    const parts = info.trim().split(" ");
    const sessionName = parts[0] ?? "";
    const windowIndex = parts[1] ?? "";
    const baseName = parts.slice(2).join(" ");

    const terminals: Array<[string, string]> = [
      ["iTerm2", "com.googlecode.iterm2"],
      ["ghostty", "com.mitchellh.ghostty"],
      ["kitty", "net.kovidgoyal.kitty"],
      ["WezTerm", "com.github.wez.wezterm"],
    ];
    let bundle = "com.apple.Terminal";
    for (const [app, id] of terminals) {
      const { code } = await pi.exec("pgrep", ["-xi", app]);
      if (code === 0) {
        bundle = id;
        break;
      }
    }

    // terminal-notifier runs -execute via /bin/sh with a minimal PATH that
    // won't include /opt/homebrew/bin. Resolve tmux's absolute path now so
    // the click command works regardless of the shell's PATH.
    const { stdout: tmuxWhich } = await pi.exec("which", ["tmux"]).catch(() => ({ stdout: "", stderr: "", code: 1 }));
    const tmuxBin = tmuxWhich.trim() || "tmux";

    const clickCmd = `'${tmuxBin}' switch-client -t '${sessionName}:${windowIndex}' 2>/dev/null; open -b '${bundle}'`;

    await pi.exec("terminal-notifier", [
      "-title",
      "pi",
      "-subtitle",
      baseName,
      "-message",
      message,
      "-activate",
      bundle,
      "-execute",
      clickCmd,
      "-sound",
      "Glass",
      "-group",
      `pi-${tmuxPane}`,
    ]);
  }

  // ── event handlers ───────────────────────────────────────────────────────

  pi.on("agent_end", async (event) => {
    try {
      // Walk messages in reverse to find the last assistant text.
      let lastText = "";
      for (let i = event.messages.length - 1; i >= 0; i--) {
        const msg = event.messages[i] as { role: string; content?: unknown };
        if (msg.role !== "assistant") continue;
        if (!Array.isArray(msg.content)) break;
        const text = (msg.content as Array<{ type: string; text?: string }>)
          .filter((c) => c.type === "text")
          .map((c) => c.text ?? "")
          .join("");
        if (text) {
          lastText = text;
          break;
        }
      }

      const asked = lastText.trimEnd().endsWith("?");
      await notify(asked ? "Waiting for input" : "Complete").catch(() => {
        // terminal-notifier may not be installed; ignore silently.
      });
    } catch {
      // Not fatal.
    }
  });
}
