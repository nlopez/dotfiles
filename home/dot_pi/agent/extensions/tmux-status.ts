/**
 * tmux-status extension
 *
 * Mirrors the Claude hooks tmux window-title emoji behaviour for pi:
 *   🤖  – agent is processing (before_agent_start)
 *   ✳️  – agent finished without a question (agent_end)
 *   🛎️  – agent finished with a question, or is waiting for input (agent_end)
 *
 * Also fires a macOS terminal-notifier notification when the agent finishes.
 *
 * Because pi runs as a TUI process *directly inside* the tmux pane, we can
 * read TMUX_PANE from the environment instead of walking the process tree
 * the way the Claude shell hooks do.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

// Characters / codepoints that appear as leading emoji prefixes.
// Matches 🤖 ✳ ️ 🛎 ️ and the variation-selector \uFE0F, plus spaces.
const EMOJI_PREFIX_RE = /^[\u{1F916}\u{2733}\u{1F6CE}\uFE0F\s]+/u;

function stripWindowEmoji(name: string): string {
	return name.replace(EMOJI_PREFIX_RE, "");
}

export default function (pi: ExtensionAPI) {
	// Only do anything when pi is running inside tmux.
	const tmuxPane = process.env.TMUX_PANE;
	if (!process.env.TMUX || !tmuxPane) return;

	// Track the last assistant message text so we can decide ✳️ vs 🛎️ on stop.
	let lastAssistantText = "";

	// ── helpers ──────────────────────────────────────────────────────────────

	async function getWindowBase(): Promise<string> {
		const { stdout } = await pi.exec("tmux", [
			"display-message",
			"-p",
			"-t",
			tmuxPane,
			"#W",
		]);
		return stripWindowEmoji(stdout.trim());
	}

	async function setWindowTitle(emoji: string): Promise<void> {
		const base = await getWindowBase();
		await pi.exec("tmux", [
			"rename-window",
			"-t",
			tmuxPane,
			`${emoji} ${base}`,
		]);
	}

	async function notify(message: string): Promise<void> {
		// Resolve session + window info for the notification subtitle / click action.
		const { stdout: info } = await pi.exec("tmux", [
			"display-message",
			"-p",
			"-t",
			tmuxPane,
			"#{session_name} #{window_index} #{window_name}",
		]);
		const [sessionName, windowIndex, ...windowNameParts] = info.trim().split(" ");
		const windowName = windowNameParts.join(" ");
		const baseName = stripWindowEmoji(windowName);

		// Detect which terminal is running (same logic as notification.sh).
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

		const clickCmd = `tmux switch-client -t '${sessionName}:${windowIndex}' 2>/dev/null; open -b '${bundle}'`;

		await pi.exec("terminal-notifier", [
			"-title", "pi",
			"-subtitle", baseName,
			"-message", message,
			"-activate", bundle,
			"-execute", clickCmd,
			"-sound", "Glass",
			"-group", `pi-${tmuxPane}`,
		]);
	}

	// ── event handlers ───────────────────────────────────────────────────────

	// 🤖 – agent is about to start processing a user prompt.
	pi.on("before_agent_start", async () => {
		try {
			// Disable automatic renaming so our prefix sticks.
			await pi.exec("tmux", [
				"set-option", "-w", "-t", tmuxPane, "automatic-rename", "off",
			]);
			await setWindowTitle("🤖");
		} catch {
			// Not fatal – pi still works without tmux status.
		}
	});

	// Track the last assistant text so we know whether it ended with "?".
	pi.on("message_end", async (event) => {
		if (event.message.role !== "assistant") return;
		const { content } = event.message as { content: unknown };
		if (Array.isArray(content)) {
			const text = (content as Array<{ type: string; text?: string }>)
				.filter((c) => c.type === "text")
				.map((c) => c.text ?? "")
				.join("");
			if (text) lastAssistantText = text;
		} else if (typeof content === "string" && content) {
			lastAssistantText = content;
		}
	});

	// ✳️ / 🛎️ – agent finished; pick emoji based on trailing punctuation.
	pi.on("agent_end", async () => {
		try {
			const lastChar = lastAssistantText.trimEnd().slice(-1);
			const emoji = lastChar === "?" ? "🛎️" : "✳️";
			await setWindowTitle(emoji);

			const notifyMsg = lastChar === "?" ? "Waiting for input" : "Complete";
			await notify(notifyMsg).catch(() => {
				// terminal-notifier may not be installed; ignore.
			});
		} catch {
			// Not fatal.
		}
	});
}
