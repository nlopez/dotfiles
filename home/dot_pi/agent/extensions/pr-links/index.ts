/**
 * pr-links extension
 *
 * Draws GitHub PR references in assistant text as markdown links:
 * `owner/repo#123` always, bare `#123` against the GitHub `origin` remote of
 * the session's working directory. Display only: the session and the model's
 * context keep the original text. The rewrite lives in ./linkify.ts, the same
 * file the Claude Code pr-links mod uses.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { githubRepoFromRemote, linkifyPrRefs } from "./linkify";

export default function (pi: ExtensionAPI) {
  // Transformers are synchronous, so the repo is looked up once per session;
  // bare refs stay plain until it resolves.
  let repo: string | undefined;

  pi.on("session_start", async (_event, ctx) => {
    repo = undefined;
    const cwd = ctx.cwd;
    try {
      const result = await pi.exec("git", ["remote", "get-url", "origin"], { cwd, timeout: 2000 });
      if (ctx.cwd === cwd && result.code === 0) repo = githubRepoFromRemote(result.stdout);
    } catch {
      // Not a git repo, or git is missing: bare refs stay plain.
    }
  });

  pi.registerMarkdownTransformer((markdown, { messageType }) =>
    messageType === "assistant" ? linkifyPrRefs(markdown, repo) : markdown,
  );
}
