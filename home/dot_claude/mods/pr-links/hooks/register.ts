import type { Register } from "claude-code";
import { githubRepoFromPath, githubRepoFromRemote, linkifyPrRefs, repoIndex, type RepoIndex } from "./linkify";

type Run = (argv: string[], cwd: string) => Promise<{ exitCode: number | null; stdout: string }>;

// Looked up once per working directory and once per module load; a failed
// lookup counts as nothing found.
const repoByCwd = new Map<string, Promise<string | undefined>>();
let clones: Promise<RepoIndex | undefined> | undefined;

function sessionRepo(cwd: string, run: Run): Promise<string | undefined> {
  let repo = repoByCwd.get(cwd);
  if (!repo) {
    const fromPath = githubRepoFromPath(cwd);
    repo = fromPath
      ? Promise.resolve(fromPath)
      : run(["git", "remote", "get-url", "origin"], cwd).then(
          ({ exitCode, stdout }) => (exitCode === 0 ? githubRepoFromRemote(stdout) : undefined),
          () => undefined,
        );
    repoByCwd.set(cwd, repo);
  }
  return repo;
}

function cloneIndex(cwd: string, run: Run): Promise<RepoIndex | undefined> {
  clones ??= run(["ghq", "list"], cwd).then(
    ({ exitCode, stdout }) => (exitCode === 0 ? repoIndex(stdout.split("\n")) : undefined),
    () => undefined,
  );
  return clones;
}

export const register: Register = (on) => {
  on("ui.render", { component: "AssistantMessage" }, async ($, e, next) => {
    const { text } = e.props;
    if (e.props.isSummary || !/#|\bPRs?\s+\d|[Pp]ull [Rr]equests?\s+\d/.test(text)) return next(e);
    const run: Run = (argv, cwd) => $.process.run(argv, { cwd, timeoutMs: 2000 });
    const cwd = await $.session.cwd();
    const [repo, index] = await Promise.all([
      sessionRepo(cwd, run),
      /[A-Za-z]#\d/.test(text) ? cloneIndex(cwd, run) : undefined,
    ]);
    const linked = linkifyPrRefs(text, { sessionRepo: repo, index });
    return next(linked === text ? e : { ...e, props: { ...e.props, text: linked } });
  });
};
