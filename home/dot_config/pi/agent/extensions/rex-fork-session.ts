/**
 * rex-fork-session extension
 *
 * Inside a Rex terminal, `/fork` and `/clone` open the forked Pi session in a
 * new Rex session instead of replacing the session in the current pane. The
 * current pane keeps the original conversation, so both branches stay live.
 *
 * The handler builds the fork file the same way Pi does, starts
 * `pi --session <fork>` in a new Rex session, and cancels the built-in fork.
 * For `/fork`, the selected prompt goes into the new editor through a
 * temporary file named by PI_REX_FORK_DRAFT_FILE.
 *
 * Rex.app clients attached to the current session switch to the new session
 * when Remote Control is on. If Rex cannot create the session, the built-in
 * fork runs in the current pane.
 */

import { existsSync, mkdtempSync, readFileSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { SessionManager } from "@earendil-works/pi-coding-agent";

const DRAFT_ENV = "PI_REX_FORK_DRAFT_FILE";

type Content = string | Array<{ type: string; text?: string }>;

function userText(content: Content): string {
  if (typeof content === "string") return content;
  return content
    .filter((part) => part.type === "text" && typeof part.text === "string")
    .map((part) => part.text)
    .join("");
}

export default function (pi: ExtensionAPI) {
  if (!process.env.REX_SESSION) return;
  const rexSession = process.env.REX_SESSION;

  pi.on("session_start", async (event, ctx) => {
    const draftFile = process.env[DRAFT_ENV];
    if (event.reason !== "startup" || !draftFile) return;
    delete process.env[DRAFT_ENV];
    try {
      const text = readFileSync(draftFile, "utf8");
      if (text && ctx.hasUI) ctx.ui.setEditorText(text);
    } catch {
      // The draft is optional; a missing file leaves the editor empty.
    } finally {
      rmSync(draftFile, { force: true });
    }
  });

  pi.on("session_before_fork", async (event, ctx) => {
    if (!ctx.hasUI) return;
    const sm = ctx.sessionManager;
    const currentFile = sm.getSessionFile();
    if (!currentFile || !existsSync(currentFile)) return;

    const selected = sm.getEntry(event.entryId);
    if (!selected) return;

    let targetLeafId: string | null;
    let draft = "";
    if (event.position === "at") {
      targetLeafId = selected.id;
    } else {
      if (selected.type !== "message" || selected.message.role !== "user") return;
      targetLeafId = selected.parentId;
      draft = userText(selected.message.content as Content);
    }

    let forkFile: string | undefined;
    if (targetLeafId) {
      forkFile = SessionManager.open(currentFile, sm.getSessionDir()).createBranchedSession(targetLeafId);
    } else {
      const fresh = SessionManager.create(ctx.cwd, sm.getSessionDir());
      fresh.newSession({ parentSession: currentFile });
      forkFile = fresh.getSessionFile();
    }
    if (!forkFile) return;

    let draftDir: string | undefined;
    const command = ["pi", "--session", forkFile];
    if (draft) {
      draftDir = mkdtempSync(join(tmpdir(), "pi-rex-fork-"));
      const draftFile = join(draftDir, "draft.txt");
      writeFileSync(draftFile, draft, { mode: 0o600 });
      command.unshift("env", `${DRAFT_ENV}=${draftFile}`);
    }

    let label = "pi-fork";
    const inspect = await pi.exec("rex", ["session", "inspect", rexSession, "--json"], { timeout: 5_000 });
    if (inspect.code === 0) {
      try {
        const current = JSON.parse(inspect.stdout).label;
        if (typeof current === "string" && current) label = `${current}-fork`;
      } catch {
        // Keep the default label.
      }
    }

    const created = await pi.exec(
      "rex",
      ["session", "new", label, "--cwd", ctx.cwd, "--interactive", "--json", "--", ...command],
      { timeout: 10_000 },
    );
    let newSession: string | undefined;
    if (created.code === 0) {
      try {
        newSession = JSON.parse(created.stdout).session_id;
      } catch {
        newSession = undefined;
      }
    }

    if (!newSession) {
      // The built-in fork writes its own file, so this one is an orphan.
      try {
        unlinkSync(forkFile);
      } catch {
        // A fork from the first message has no file until Pi writes to it.
      }
      if (draftDir) rmSync(draftDir, { recursive: true, force: true });
      ctx.ui.notify(`Rex session failed; forking in this pane. ${created.stderr.trim()}`, "warning");
      return;
    }

    const clients = await pi.exec("rex", ["client", "ls", "-s", rexSession, "--json"], { timeout: 5_000 });
    if (clients.code === 0) {
      try {
        const list: Array<{ client_id: string; info?: { kind?: string } }> = JSON.parse(clients.stdout).clients ?? [];
        for (const client of list.filter((c) => c.info?.kind === "app")) {
          await pi.exec("rex", ["-C", client.client_id, "do", "session.select", `session_id=${newSession}`], {
            timeout: 5_000,
          });
        }
      } catch {
        // Switching the app view is optional.
      }
    }

    ctx.ui.notify(`Forked into Rex session "${label}"`, "info");
    return { cancel: true };
  });
}
