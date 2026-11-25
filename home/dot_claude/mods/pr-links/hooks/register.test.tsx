import { expect, test } from "claude-code/testing";

const MESSAGE = {
  plugin: "pr-links",
  component: "AssistantMessage",
  requestId: "msg-1",
  surface: "terminal",
  props: { text: "", isFirstOfReply: true },
} as const;

const pr = (repo: string, n: number) => `https://github.com/${repo}/pull/${n}`;

function drawText(on: Parameters<Parameters<typeof test>[1]>[1]) {
  on("ui.render", ($, e) => {
    const { Text } = $.ui.resolve(e);
    return <Text>{(e.props as { text: string }).text}</Text>;
  });
}

test("refs link against the cwd's remote and the ghq clones", async ($, on) => {
  const ran: string[] = [];
  on("session.cwd", () => ({ value: "/repo" }));
  on("process.run", (_, e) => {
    ran.push(e.argv.join(" "));
    const stdout = e.argv[0] === "ghq" ? "github.com/acme/cloud-inventory\n" : "git@work.github.com:acme/api.git\n";
    return { value: { exitCode: 0, stdout, stderr: "" } };
  });
  drawText(on);

  const text = "Merged #34 and cloud-inventory#5.";
  const ui = await $.ui.mount({ ...MESSAGE, props: { ...MESSAGE.props, text } });
  expect((await ui.find({ type: "Text" }))?.text).toBe(
    `Merged [#34](${pr("acme/cloud-inventory", 34)}) and [cloud-inventory#5](${pr("acme/cloud-inventory", 5)}).`,
  );
  expect(ran).toEqual(["git remote get-url origin", "ghq list"]);

  // Text naming no other repo: #34 is the session's.
  const second = await $.ui.mount({ ...MESSAGE, requestId: "msg-2", props: { ...MESSAGE.props, text: "See #34." } });
  expect((await second.find({ type: "Text" }))?.text).toBe(`See [#34](${pr("acme/api", 34)}).`);
  expect(ran).toHaveLength(2);
  await ui.unmount();
  await second.unmount();
});

test("a ghq path names the repo without running git", async ($, on) => {
  const ran: string[] = [];
  on("session.cwd", () => ({ value: "/src/github.com/acme/api/main" }));
  on("process.run", (_, e) => {
    ran.push(e.argv.join(" "));
    return { value: { exitCode: 1, stdout: "", stderr: "" } };
  });
  drawText(on);

  const ui = await $.ui.mount({ ...MESSAGE, props: { ...MESSAGE.props, text: "babysit PR 21173" } });
  expect((await ui.find({ type: "Text" }))?.text).toBe(`babysit [PR 21173](${pr("acme/api", 21173)})`);
  expect(ran).toEqual([]);
  await ui.unmount();
});

test("bare refs stay plain outside a GitHub repo", async ($, on) => {
  on("session.cwd", () => ({ value: "/elsewhere" }));
  on("process.run", () => ({ value: { exitCode: 128, stdout: "", stderr: "not a git repo" } }));
  drawText(on);

  const ui = await $.ui.mount({ ...MESSAGE, props: { ...MESSAGE.props, text: "fixes #34" } });
  expect((await ui.find({ type: "Text" }))?.text).toBe("fixes #34");
  await ui.unmount();
});
