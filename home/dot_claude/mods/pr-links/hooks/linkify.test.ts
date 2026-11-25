import { expect, test } from "claude-code/testing";
import { githubRepoFromPath, githubRepoFromRemote, linkifyPrRefs, repoIndex } from "./linkify";

const index = repoIndex([
  "github.com/acme/service-discovery-platform",
  "github.com/acme/cloud-inventory",
  "github.com/acme/dd-go",
  "github.com/other/dd-go",
  "github.com/acme/sdp",
  "github.com/acme/web-app-shell",
  "gitlab.example.com/acme/ignored",
  ".worktrees/acme/web.branch",
]);
const ctx = { sessionRepo: "acme/api", index };
const pr = (repo: string, n: number) => `https://github.com/${repo}/pull/${n}`;

const cases: [string, string, Parameters<typeof linkifyPrRefs>[1]?][] = [
  // owner/repo#N
  ["see acme/foo#12.", `see [acme/foo#12](${pr("acme/foo", 12)}).`],
  ["(o/r#7)", `([o/r#7](${pr("o/r", 7)}))`],
  // bare #N and PR N against the session repo
  ["fixes #34, #35", `fixes [#34](${pr("acme/api", 34)}), [#35](${pr("acme/api", 35)})`, ctx],
  ["**#9**", `**[#9](${pr("acme/api", 9)})**`, ctx],
  ["babysit PR 21173 now", `babysit [PR 21173](${pr("acme/api", 21173)}) now`, ctx],
  ["PR #5 and PR#6", `[PR #5](${pr("acme/api", 5)}) and [PR#6](${pr("acme/api", 6)})`, ctx],
  ["fixes #34", "fixes #34"],
  ["PR 12", "PR 12"],
  // the text names one repo: bare refs follow it
  [`opened ${pr("x/y", 2)}: PR #2`, `opened ${pr("x/y", 2)}: [PR #2](${pr("x/y", 2)})`, ctx],
  ["x/y#1 then #2", `[x/y#1](${pr("x/y", 1)}) then [#2](${pr("x/y", 2)})`, ctx],
  // several repos named: bare refs stay plain
  ["x/y#1 and z/w#2, also #3", `[x/y#1](${pr("x/y", 1)}) and [z/w#2](${pr("z/w", 2)}), also #3`, ctx],
  // repo#N without owner, by name or initials of a known clone
  ["cloud-inventory#1204", `[cloud-inventory#1204](${pr("acme/cloud-inventory", 1204)})`, ctx],
  ["SDP#20975", `[SDP#20975](${pr("acme/sdp", 20975)})`, ctx],
  ["WAS#3", `[WAS#3](${pr("acme/web-app-shell", 3)})`, ctx],
  ["api#4", `[api#4](${pr("acme/api", 4)})`, ctx],
  ["dd-go#1 unknown#2 a#3", "dd-go#1 unknown#2 a#3", ctx],
  // whole code spans holding a ref
  ["`acme/images#12203`", `[\`acme/images#12203\`](${pr("acme/images", 12203)})`],
  ["`#76` and `PR 9`", `[\`#76\`](${pr("acme/api", 76)}) and [\`PR 9\`](${pr("acme/api", 9)})`, ctx],
  ["`cloud-inventory#3517`", `[\`cloud-inventory#3517\`](${pr("acme/cloud-inventory", 3517)})`, ctx],
  ["`echo o/r#1`", "`echo o/r#1`"],
  // left alone
  ["[o/r#1](https://x) o/r#1", `[o/r#1](https://x) [o/r#1](${pr("o/r", 1)})`],
  ["https://github.com/o/r/pull/5#issue-1 ok", "https://github.com/o/r/pull/5#issue-1 ok", ctx],
  ["```\no/r#1\n```\no/r#2", `\`\`\`\no/r#1\n\`\`\`\n[o/r#2](${pr("o/r", 2)})`],
  ["# Heading\n#12abc &#123; a/b/c#1 x/y#1a", "# Heading\n#12abc &#123; a/b/c#1 x/y#1a", ctx],
];

test("PR refs become links, and a second pass changes nothing", () => {
  for (const [input, output, context] of cases) {
    expect(linkifyPrRefs(input, context)).toBe(output);
    expect(linkifyPrRefs(output, context)).toBe(output);
  }
});

test("repos are read from remotes and ghq paths", () => {
  expect(githubRepoFromRemote("git@github.com:acme/dd-go.git")).toBe("acme/dd-go");
  expect(githubRepoFromRemote("git@work.github.com:acme/dd-go")).toBe("acme/dd-go");
  expect(githubRepoFromRemote("https://github.com/o/r")).toBe("o/r");
  expect(githubRepoFromRemote("ssh://git@github.com:22/o/r.git")).toBe("o/r");
  expect(githubRepoFromRemote("git@gitlab.example.com:o/r.git")).toBe(undefined);
  expect(githubRepoFromRemote("git@notgithub.com:o/r.git")).toBe(undefined);
  expect(githubRepoFromPath("/home/me/src/github.com/acme/cloud-inventory/master/x")).toBe("acme/cloud-inventory");
  expect(githubRepoFromPath("/home/me/src/github.com/acme")).toBe(undefined);
});
