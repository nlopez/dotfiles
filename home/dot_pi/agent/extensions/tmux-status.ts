/**
 * tmux-status extension
 *
 * Mirrors the Claude hooks tmux window-title emoji behaviour for pi:
 *   🤖  – agent is working (turn_start: fires each time the LLM is called)
 *   ✳️  – agent finished without a question (agent_end)
 *   🛎️  – agent finished with a question (agent_end)
 *
 * Also fires a macOS terminal-notifier notification when the agent finishes.
 *
 * Because pi runs as a TUI process *directly inside* the tmux pane, we read
 * TMUX_PANE from the environment instead of walking the process tree the way
 * the Claude shell hooks do.
 *
 * turn_start is used (rather than before_agent_start) because it fires right
 * as the LLM is called — unambiguously "working" — and re-fires on every
 * tool-calling turn so the emoji stays correct throughout multi-turn runs.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

// Codepoints for the three emoji prefixes plus the variation-selector U+FE0F.
const EMOJI_PREFIX_RE = /^[\u{1F916}\u{2733}\u{1F6CE}\uFE0F\s]+/u;

function stripWindowEmoji(name: string): string {
	return name.replace(EMOJI_PREFIX_RE, "");
}

export default function (pi: ExtensionAPI) {
	// Only activate inside tmux.
	const tmuxPane = process.env.TMUX_PANE;
	if (!process.env.TMUX || !tmuxPane) return;

	// ── helpers ──────────────────────────────────────────────────────────────

	async function getWindowBase(): Promise<string> {
		const { stdout } = await pi.exec("tmux", [
			"display-message", "-p", "-t", tmuxPane, "#W",
		]);
		return stripWindowEmoji(stdout.trim());
	}

	async function setWindowTitle(emoji: string): Promise<void> {
		const base = await getWindowBase();
		// Disable auto-rename so our prefix sticks, then rename.
		await pi.exec("tmux", [
			"set-option", "-w", "-t", tmuxPane, "automatic-rename", "off",
		]);
		await pi.exec("tmux", [
			"rename-window", "-t", tmuxPane, `${emoji} ${base}`,
		]);
	}

	async function notify(message: string): Promise<void> {
		const { stdout: info } = await pi.exec("tmux", [
			"display-message", "-p", "-t", tmuxPane,
			"#{session_name} #{window_index} #{window_name}",
		]);
		const parts = info.trim().split(" ");
		const sessionName = parts[0] ?? "";
		const windowIndex = parts[1] ?? "";
		const baseName = stripWindowEmoji(parts.slice(2).join(" "));

		const terminals: Array<[string, string]> = [
			["iTerm2",   "com.googlecode.iterm2"],
			["ghostty",  "com.mitchellh.ghostty"],
			["kitty",    "net.kovidgoyal.kitty"],
			["WezTerm",  "com.github.wez.wezterm"],
		];
		let bundle = "com.apple.Terminal";
		for (const [app, id] of terminals) {
			const { code } = await pi.exec("pgrep", ["-xi", app]);
			if (code === 0) { bundle = id; break; }
		}

		const clickCmd =
			`tmux switch-client -t '${sessionName}:${windowIndex}' 2>/dev/null; open -b '${bundle}'`;

		await pi.exec("terminal-notifier", [
			"-title",    "pi",
			"-subtitle", baseName,
			"-message",  message,
			"-activate", bundle,
			"-execute",  clickCmd,
			"-sound",    "Glass",
			"-group",    `pi-${tmuxPane}`,
		]);
	}

	// ── event handlers ───────────────────────────────────────────────────────

	// 🤖 – fires every time the LLM is about to be called (each turn).
	// Using turn_start rather than before_agent_start because it fires right
	// as the LLM call begins and re-fires during every tool-calling turn.
	pi.on("turn_start", async () => {
		try {
			await setWindowTitle("🤖");
		} catch {
			// Not fatal.
		}
	});

	// ✳️ / 🛎️ – pick emoji based on whether the last assistant message ends "?".
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
				if (text) { lastText = text; break; }
			}

			const lastChar = lastText.trimEnd().slice(-1);
			const emoji = lastChar === "?" ? "🛎️" : "✳️";
			await setWindowTitle(emoji);

			const notifyMsg = lastChar === "?" ? "Waiting for input" : "Complete";
			await notify(notifyMsg).catch(() => {
				// terminal-notifier may not be installed; ignore silently.
			});
		} catch {
			// Not fatal.
		}
	});
}
