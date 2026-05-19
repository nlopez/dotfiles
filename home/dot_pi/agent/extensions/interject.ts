import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/**
 * ctrl+enter — interrupt the current turn and resume with any queued
 * messages (queued via alt+enter while the agent was running).
 *
 * Queue messages with alt+enter as normal, then hit ctrl+enter to
 * abort the current turn so they're delivered immediately rather than
 * waiting for the turn to finish.
 *
 * No-op when idle or when there are no queued messages.
 */
export default function (pi: ExtensionAPI) {
  pi.registerShortcut("ctrl+enter", {
    description: "Interrupt current turn and deliver queued messages now",
    handler: async (ctx) => {
      if (ctx.isIdle()) return;
      if (!ctx.hasPendingMessages()) return;

      ctx.abort();
    },
  });
}
