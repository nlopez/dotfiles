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
 *
 * All setWindowTitle calls are serialised through a promise queue so that a
 * slow turn_start rename can never land after a faster agent_end rename and
 * leave the robot stuck. Title cleanup on exit is handled by the pi() shell
 * wrapper in .zshrc, which runs after the process exits and is immune to
 * async timing issues inside the extension.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { mkdir, writeFile, unlink } from "node:fs/promises";
import { join } from "node:path";

// Codepoints for the three emoji prefixes plus the variation-selector U+FE0F.
const EMOJI_PREFIX_RE = /^[\u{1F916}\u{2733}\u{1F6CE}\uFE0F\s]+/u;

function stripWindowEmoji(name: string): string {
	return name.replace(EMOJI_PREFIX_RE, "");
}

export default function (pi: ExtensionAPI) {
	// Only activate inside tmux.
	const tmuxPane = process.env.TMUX_PANE;
	if (!process.env.TMUX || !tmuxPane) return;

	// ── runtime model tracking ───────────────────────────────────────────────
	// Write the live model name to a per-pane state file so that out-of-process
	// tools (e.g. pi-model-name, called by the zsh gh() wrapper) can read the
	// runtime model rather than the settings.json default — correctly reflecting
	// mid-session /model or Ctrl+P changes.
	const MODEL_STATE_DIR = join(process.env.HOME ?? "", ".local/state/pi/pane-models");
	const modelFile = join(MODEL_STATE_DIR, tmuxPane.replace("%", ""));

	async function writeModel(model: { name?: string; id: string }): Promise<void> {
		try {
			await mkdir(MODEL_STATE_DIR, { recursive: true });
			await writeFile(modelFile, model.name ?? model.id, "utf8");
		} catch { /* non-fatal */ }
	}

	pi.on("session_start", (_event, ctx) => {
		if (ctx.model) void writeModel(ctx.model);
	});

	pi.on("model_select", (event) => {
		void writeModel(event.model);
	});

	pi.on("session_shutdown", () => {
		void unlink(modelFile).catch(() => {});
	});

	// ── serial title queue ───────────────────────────────────────────────────
	// Serialise every rename through a promise chain so concurrent turn_start
	// and agent_end calls can't interleave their tmux exec pairs and stamp the
	// wrong emoji last.
	let titleQueue: Promise<void> = Promise.resolve();

	function enqueueTitle(emoji: string): void {
		titleQueue = titleQueue
			.then(() => setWindowTitle(emoji))
			.catch(() => {}); // not fatal
	}

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
	pi.on("turn_start", () => {
		enqueueTitle("🤖");
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
			enqueueTitle(emoji);

			const notifyMsg = lastChar === "?" ? "Waiting for input" : "Complete";
			await notify(notifyMsg).catch(() => {
				// terminal-notifier may not be installed; ignore silently.
			});
		} catch {
			// Not fatal.
		}
	});

	// Title cleanup is handled by the pi() shell wrapper in .zshrc after exit.
}
