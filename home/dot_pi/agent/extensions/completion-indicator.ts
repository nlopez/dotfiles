import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

let pendingSummary: string | null = null;

const extractLength = (messages: Array<{ role: string; content: any }>): number =>
  messages.reduce((sum, m) => {
    const c = m.content;
    if (typeof c === "string") return sum + c.length;
    if (Array.isArray(c))
      return sum + c.reduce((s, x) => s + String(x.text ?? "").length, 0);
    return sum + String(c).length;
  }, 0);

export default function (pi: ExtensionAPI) {
  	// When agent starts
  pi.on("agent_start", async (_event, ctx) => {
    pendingSummary = null;
    });

  	// When agent ends: notify + save stats for the next turn
  pi.on("agent_end", async (event, ctx) => {
    const messages = event.messages ?? [];
    const toolCalls = messages.filter((m) => m.role === "toolResult").length;
    const charCount = extractLength(messages);

    pendingSummary = `Completed (${toolCalls} tool(s), ${charCount} chars)`;

      // Pop-up notifications (no clutter in the prompt area)
    ctx.ui.notify("✅ Agent completed!", "success");
    ctx.ui.notify(`Stats: ${pendingSummary}`, "info");
    });

  	// Inject summary into the chat thread on the next interaction
  pi.on("context", async (event, _ctx) => {
    if (!pendingSummary) return { messages: event.messages };

    const msgs = [...event.messages];
    msgs.push({
      role: "toolResult",
      content: `\n---\n${pendingSummary}\n---\n`,
      });

    pendingSummary = null;
    return { messages: msgs };
    });
}
