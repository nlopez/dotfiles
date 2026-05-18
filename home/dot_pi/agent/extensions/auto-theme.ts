/**
 * Auto Theme Extension
 *
 * Syncs the pi theme with macOS appearance (dark / light mode).
 *
 *   dark  → atom-one-dark
 *   light → solarized-light
 *
 * Polls every 2 seconds. Requires two consecutive agreeing readings before
 * switching themes so that a single flaky result never causes a flip.
 *
 * Detection uses `defaults read -g AppleInterfaceStyle` instead of an OSC 11
 * TTY query. The TTY approach opened a second ReadStream on /dev/tty while
 * pi's TUI was already reading from the same fd; the terminal's response could
 * be consumed by pi's input handler, causing timeouts that returned -1 and were
 * treated as "dark" — making the theme flicker when actually in light mode and
 * leaving different messages painted with different themes in the same session.
 *
 * macOS only — exits early on other platforms so the extension is safe to
 * deploy via chezmoi on Linux/Windows hosts without modification.
 *
 * Placement: ~/.pi/agent/extensions/auto-theme.ts
 */

import { execFile } from "node:child_process";
import { platform } from "node:os";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const THEMES = {
	dark: "solarized-dark",
	light: "solarized-light",
} as const;

/**
 * Returns true when macOS is in Dark Mode.
 * `defaults read -g AppleInterfaceStyle` prints "Dark" and exits 0 in dark
 * mode; exits with code 1 (and no output) in light mode.
 */
function isDarkMode(): Promise<boolean> {
	return new Promise((resolve) => {
		execFile(
			"defaults",
			["read", "-g", "AppleInterfaceStyle"],
			(err, stdout) => {
				resolve(stdout.trim() === "Dark");
			},
		);
	});
}

export default function (pi: ExtensionAPI) {
	if (platform() !== "darwin") return;

	let intervalId: ReturnType<typeof setInterval> | null = null;

	pi.on("session_start", async (_event, ctx) => {
		const dark = await isDarkMode();
		let current: "dark" | "light" = dark ? "dark" : "light";
		ctx.ui.setTheme(THEMES[current]);

		// Pending reading that must be confirmed by the next poll before we switch.
		let pending: "dark" | "light" | null = null;

		intervalId = setInterval(async () => {
			const reading: "dark" | "light" = (await isDarkMode()) ? "dark" : "light";

			if (reading === current) {
				// Stable — clear any pending candidate.
				pending = null;
				return;
			}

			if (reading === pending) {
				// Second consecutive reading that disagrees with current → switch.
				current = reading;
				pending = null;
				ctx.ui.setTheme(THEMES[current]);
			} else {
				// First reading that disagrees — wait for confirmation.
				pending = reading;
			}
		}, 2000);
	});

	pi.on("session_shutdown", () => {
		if (intervalId !== null) {
			clearInterval(intervalId);
			intervalId = null;
		}
	});
}
