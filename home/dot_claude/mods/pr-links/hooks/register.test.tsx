import { expect, test } from "claude-code/testing";

const MESSAGE = {
  plugin: "pr-links",
  component: "AssistantMessage",
  requestId: "msg-1",
  surface: "terminal",
  props: { text: "Opened acme/web#12 and #34, see `o/r#5`.", isFirstOfReply: true },
} as const;

test("PR refs are drawn as links, bare ones against the origin repo", async ($, on) => {
  on("session.cwd", () => ({ value: "/repo" }));
  on("process.run", () => ({
    value: { exitCode: 0, stdout: "git@github.com:acme/api.git\n", stderr: "" },
  }));
  on("ui.render", ($, e) => {
    const { Text } = $.ui.resolve(e);
    return <Text>{(e.props as { text: string }).text}</Text>;
  });

  const ui = await $.ui.mount(MESSAGE);
  expect((await ui.find({ type: "Text" }))?.text).toBe(
    "Opened [acme/web#12](https://github.com/acme/web/pull/12) and " +
      "[#34](https://github.com/acme/api/pull/34), see `o/r#5`.",
  );
  await ui.unmount();
});

test("bare refs stay plain outside a GitHub repo", async ($, on) => {
  on("session.cwd", () => ({ value: "/elsewhere" }));
  on("process.run", () => ({ value: { exitCode: 128, stdout: "", stderr: "not a git repo" } }));
  on("ui.render", ($, e) => {
    const { Text } = $.ui.resolve(e);
    return <Text>{(e.props as { text: string }).text}</Text>;
  });

  const ui = await $.ui.mount({ ...MESSAGE, props: { text: "fixes #34", isFirstOfReply: true } });
  expect((await ui.find({ type: "Text" }))?.text).toBe("fixes #34");
  await ui.unmount();
});
