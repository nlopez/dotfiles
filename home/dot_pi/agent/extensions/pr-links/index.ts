/**
 * pr-links extension
 *
 * Draws GitHub PR references in assistant text as markdown links; see
 * ./linkify.ts, the same file the Claude Code pr-links mod uses. Display only:
 * the session and the model's context keep the original text.
 *
 * Transformers are synchronous, so the lookups run at session start: the
 * session's repo from a ghq-style path, else `git remote get-url origin`; the
 * clone index from `ghq list`. Refs that need one stay plain until it lands.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { githubRepoFromPath, githubRepoFromRemote, linkifyPrRefs, repoIndex, type RepoContext } from "./linkify";

export default function (pi: ExtensionAPI) {
  let context: RepoContext = {};

  async function stdout(command: string, args: string[], cwd: string): Promise<string | undefined> {
    try {
      const result = await pi.exec(command, args, { cwd, timeout: 2000 });
      return result.code === 0 ? result.stdout : undefined;
    } catch {
      return undefined;
    }
  }

  pi.on("session_start", async (_event, ctx) => {
    const cwd = ctx.cwd;
    const current: RepoContext = { sessionRepo: githubRepoFromPath(cwd) };
    context = current;
    const [remote, clones] = await Promise.all([
      current.sessionRepo ? undefined : stdout("git", ["remote", "get-url", "origin"], cwd),
      stdout("ghq", ["list"], cwd),
    ]);
    if (context !== current) return;
    context = {
      sessionRepo: current.sessionRepo ?? (remote ? githubRepoFromRemote(remote) : undefined),
      index: clones ? repoIndex(clones.split("\n")) : undefined,
    };
  });

  pi.registerMarkdownTransformer((markdown, { messageType }) =>
    messageType === "assistant" ? linkifyPrRefs(markdown, context) : markdown,
  );
}
