/**
 * program-status-blocked extension
 *
 * Pi reports its state to the terminal with the Program Status Protocol
 * (OSC 7501), but it only reports `blocked` for select/confirm/input/editor
 * dialogs. Dialogs built with `ctx.ui.custom()`, such as the
 * ask_user_question questionnaire, leave the status at `working`, so the
 * terminal never shows that Pi is waiting for an answer.
 *
 * This extension reports `blocked` (kind `question`) while a custom dialog is
 * open and restores `working` or `idle` when it closes.
 *
 * Spec: https://www.superlogical.com/rex/docs/build/program-status
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const APP = "pi";

function enabled(): boolean {
  const override = process.env.PI_PROGRAM_STATUS;
  if (override === "0") return false;
  if (override === "1") return true;
  // tmux and screen do not forward OSC 7501.
  if (process.env.TMUX || process.env.STY) return false;
  return process.env.TERM_PROGRAM === "rex";
}

function report(state: "blocked" | "working" | "idle", message?: string): void {
  const pairs = [`state=${state}`, `app=${APP}`];
  if (state === "blocked") pairs.push("kind=question");
  const text = (message ?? "").replace(/[\x00-\x1f\x7f]/g, " ").trim();
  if (text) pairs.push(`msg=${Buffer.from(text, "utf8").toString("base64")}`);
  process.stdout.write(`\x1b]7501;${pairs.join(":")}\x1b\\`);
}

export default function (pi: ExtensionAPI) {
  if (!enabled()) return;

  let running = false;
  let blocked = false;

  pi.on("agent_start", async () => {
    running = true;
  });

  pi.on("agent_settled", async () => {
    running = false;
  });

  pi.on("ui_prompt_start", async (event) => {
    if (event.kind !== "custom") return;
    blocked = true;
    report("blocked", event.title || "Waiting for your answer");
  });

  pi.on("ui_prompt_end", async () => {
    if (!blocked) return;
    blocked = false;
    report(running ? "working" : "idle", running ? pi.getSessionName() : undefined);
  });
}
