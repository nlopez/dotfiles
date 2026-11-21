/**
 * No Chat Comments
 *
 * Blocks write/edit calls whose added text contains comments that narrate the
 * edit or the conversation ("used to be x", "as requested", ...).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const PATTERN = /(\/\/|#|\/\*).*\b(changed from|previously (this|it)|used to be|as requested)\b/i;

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    let added = "";
    if (event.toolName === "write") {
      added = (event.input as { content?: string }).content ?? "";
    } else if (event.toolName === "edit") {
      const { edits } = event.input as { edits?: Array<{ newText: string }> };
      added = (edits ?? []).map((e) => e.newText).join("\n");
    } else {
      return undefined;
    }
    if (!PATTERN.test(added)) return undefined;
    const reason = "Write comments for the code, not the chat";
    ctx.ui.notify(reason, "warning");
    return { block: true, reason };
  });
}
