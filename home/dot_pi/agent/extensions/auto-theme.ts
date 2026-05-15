/**
 * Auto Theme Extension
 *
 * Syncs the pi theme with the macOS appearance setting, which in turn drives
 * Ghostty's own color scheme (configured as `theme = light:…,dark:…`).
 *
 *   dark  → atom-one-dark
 *   light → solarized-light
 *
 * Polls every 2 seconds so theme changes land within a couple of seconds of
 * the system switching.
 *
 * Placement: ~/.pi/agent/extensions/auto-theme.ts
 */

import { exec } from "node:child_process";
import { promisify } from "node:util";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const execAsync = promisify(exec);

const THEMES = {
	dark: "atom-one-dark",
	light: "solarized-light",
} as const;

async function isDarkMode(): Promise<boolean> {
	try {
		const { stdout } = await execAsync(
			"osascript -e 'tell application \"System Events\" to tell appearance preferences to return dark mode'",
		);
		return stdout.trim() === "true";
	} catch {
		return false;
	}
}

export default function (pi: ExtensionAPI) {
	let intervalId: ReturnType<typeof setInterval> | null = null;

	pi.on("session_start", async (_event, ctx) => {
		const dark = await isDarkMode();
		let current: "dark" | "light" = dark ? "dark" : "light";
		ctx.ui.setTheme(THEMES[current]);

		intervalId = setInterval(async () => {
			const next: "dark" | "light" = (await isDarkMode()) ? "dark" : "light";
			if (next !== current) {
				current = next;
				ctx.ui.setTheme(THEMES[current]);
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
