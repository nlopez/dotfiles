import type { Register } from "claude-code";
import { githubRepoFromRemote, linkifyPrRefs } from "./linkify";

// The GitHub repo behind each working directory, for bare `#123` refs.
const repoByCwd = new Map<string, Promise<string | undefined>>();

function repoFor(cwd: string, run: () => Promise<{ exitCode: number | null; stdout: string }>) {
  let repo = repoByCwd.get(cwd);
  if (!repo) {
    repo = run().then(
      ({ exitCode, stdout }) => (exitCode === 0 ? githubRepoFromRemote(stdout) : undefined),
      () => undefined,
    );
    repoByCwd.set(cwd, repo);
  }
  return repo;
}

export const register: Register = (on) => {
  on("ui.render", { component: "AssistantMessage" }, async ($, e, next) => {
    if (e.props.isSummary || !e.props.text.includes("#")) return next(e);
    const cwd = await $.session.cwd();
    const repo = await repoFor(cwd, () =>
      $.process.run(["git", "remote", "get-url", "origin"], { cwd, timeoutMs: 2000 }),
    );
    const text = linkifyPrRefs(e.props.text, repo);
    return next(text === e.props.text ? e : { ...e, props: { ...e.props, text } });
  });
};
