/**
 * Auto Theme Extension
 *
 * Syncs the pi theme with the terminal background color, which in turn drives
 * Ghostty's own color scheme (configured as `theme = light:…,dark:…`).
 *
 *   dark  → atom-one-dark
 *   light → solarized-light
 *
 * Polls every 2 seconds so theme changes land within a couple of seconds of
 * the terminal switching.
 *
 * Placement: ~/.pi/agent/extensions/auto-theme.ts
 */

import * as fs from "node:fs";
import * as tty from "node:tty";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const THEMES = {
	dark: "atom-one-dark",
	light: "solarized-light",
} as const;

/**
 * Queries the terminal background color via OSC 11 and returns its relative
 * luminance (0 = black, 1 = white). Resolves with -1 on failure.
 */
function queryBgLuminance(): Promise<number> {
	return new Promise((resolve) => {
		let fd: number;
		try {
			fd = fs.openSync("/dev/tty", "r+");
		} catch {
			return resolve(-1);
		}

		const stream = new tty.ReadStream(fd);
		stream.setRawMode(true);

		let buf = "";

		const cleanup = (result: number) => {
			clearTimeout(timer);
			stream.removeAllListeners();
			stream.setRawMode(false);
			stream.destroy();
			resolve(result);
		};

		const timer = setTimeout(() => cleanup(-1), 500);

		stream.on("data", (chunk: Buffer) => {
			buf += chunk.toString("latin1");
			// Response: ESC ] 11 ; rgb:RRRR/GGGG/BBBB ESC \
			const m = buf.match(
				/\x1b\]11;rgb:([0-9a-f]{4})\/([0-9a-f]{4})\/([0-9a-f]{4})/i,
			);
			if (m) {
				const r = parseInt(m[1], 16) / 0xffff;
				const g = parseInt(m[2], 16) / 0xffff;
				const b = parseInt(m[3], 16) / 0xffff;
				// Relative luminance (sRGB)
				cleanup(0.2126 * r + 0.7152 * g + 0.0722 * b);
			}
		});

		stream.on("error", () => cleanup(-1));

		// Send the OSC 11 query
		fs.writeSync(fd, "\x1b]11;?\x1b\\");
	});
}

async function isDarkMode(): Promise<boolean> {
	const luminance = await queryBgLuminance();
	// Unknown (-1) → assume dark
	return luminance < 0.5;
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
