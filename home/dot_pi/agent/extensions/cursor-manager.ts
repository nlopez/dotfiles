/**
 * cursor-manager extension
 *
 * Configures the Pi input cursor:
 *   - Shape:      blinking block (\x1b[1 q / DECSCUSR 1)
 *   - Visibility: hidden at startup, visible only while the terminal window
 *                 has focus, hidden again the moment focus leaves
 *
 * How it works
 * ────────────
 * Pi's TUI has a `showHardwareCursor` flag (default false). When false every
 * render call ends with \x1b[?25l so the cursor is always hidden. When true
 * the cursor is shown at the input caret after each render.
 *
 * This extension:
 *   1. Enables terminal focus-event reporting (\x1b[?1004h) so the OS sends
 *      \x1b[I on focus gain and \x1b[O on focus loss.
 *   2. Intercepts those sequences via ctx.ui.onTerminalInput() before Pi can
 *      misinterpret them, consuming them so no render is triggered.
 *   3. Toggles tui.setShowHardwareCursor(true/false) — the proper TUI-level
 *      knob — so Pi's own render loop respects the hidden state and won't
 *      re-show the cursor on the next render cycle.
 *   4. Re-applies \x1b[1 q on every focus-in because some terminals reset
 *      cursor shape when the window regains focus.
 *
 * Requirements
 * ────────────
 * - `showHardwareCursor: false` in settings.json (enforced by
 *   modify_settings.json.tmpl) so the TUI starts with cursor hidden.
 * - All modern terminals: WezTerm, Ghostty, iTerm2, kitty, Alacritty.
 * - Under tmux: `set -g focus-events on` in .tmux.conf.
 *
 * Placement: ~/.pi/agent/extensions/cursor-manager.ts
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { TUI } from "@earendil-works/pi-tui";

// ── ANSI escape sequences ────────────────────────────────────────────────────

/** Enable terminal focus-in / focus-out reporting. */
const FOCUS_EVENTS_ON = "\x1b[?1004h";
/** Disable terminal focus-event reporting. */
const FOCUS_EVENTS_OFF = "\x1b[?1004l";
/** DECSCUSR 1 — blinking block cursor shape. */
const CURSOR_BLINK_BLOCK = "\x1b[1 q";
/** DECSCUSR 0 — reset cursor shape to the terminal's own default. */
const CURSOR_RESET = "\x1b[0 q";

/** Sequence sent by the terminal when the window gains focus. */
const FOCUS_IN = "\x1b[I";
/** Sequence sent by the terminal when the window loses focus. */
const FOCUS_OUT = "\x1b[O";

// ── Module-level cleanup handle ──────────────────────────────────────────────
// Matches the pattern used by auto-theme.ts. Safe here because focus state is
// inherently window-level: only one window has focus at a time.

let unsubscribeFocus: (() => void) | null = null;

// ── Extension entry point ────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  pi.on("session_start", (_event, ctx) => {
    // ── Capture TUI reference ────────────────────────────────────────────────
    // setWidget passes the live TUI instance to the factory. We register a
    // zero-height widget (no rendered lines, no visual footprint) purely to
    // obtain that reference so we can call tui.setShowHardwareCursor() later.
    let tui: TUI | undefined;
    ctx.ui.setWidget("__cursor_mgr", (t) => {
      tui = t;
      return {
        render: () => [],
        invalidate: () => {},
      };
    });

    // ── Enable focus reporting + prime cursor shape ──────────────────────────
    // The cursor starts hidden (showHardwareCursor is false from settings).
    // We set the blinking-block shape now so it's already in effect the moment
    // showHardwareCursor flips to true on the first focus-in event.
    process.stdout.write(FOCUS_EVENTS_ON);
    process.stdout.write(CURSOR_BLINK_BLOCK);

    // ── Intercept focus events ───────────────────────────────────────────────
    unsubscribeFocus = ctx.ui.onTerminalInput((data) => {
      if (data === FOCUS_IN) {
        // Window gained focus — enable cursor and enforce blinking-block shape.
        // Re-applying \x1b[1 q is cheap and guards against terminals that reset
        // cursor shape when the window comes back into focus.
        tui?.setShowHardwareCursor(true);
        process.stdout.write(CURSOR_BLINK_BLOCK);
        return { consume: true };
      }

      if (data === FOCUS_OUT) {
        // Window lost focus — hide cursor.
        // Using tui.setShowHardwareCursor(false) rather than a raw \x1b[?25l
        // ensures Pi's own render loop respects the hidden state and won't
        // re-show the cursor when it next renders.
        tui?.setShowHardwareCursor(false);
        return { consume: true };
      }
    });
  });

  pi.on("session_shutdown", () => {
    // Deregister the terminal input listener.
    unsubscribeFocus?.();
    unsubscribeFocus = null;

    // Restore terminal defaults: disable focus reporting, reset cursor shape.
    // Pi will also call hideCursor() as part of its own teardown, but writing
    // these here ensures cleanup even on unclean exits where Pi hooks may not
    // fully execute.
    process.stdout.write(FOCUS_EVENTS_OFF);
    process.stdout.write(CURSOR_RESET);
  });
}
