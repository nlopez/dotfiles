## Package Management

Always prefer **`uv`** for Python and **`pnpm`** for Node.js.

- Python: use `uv pip install`, `uv run`, `uv build` for project work; use `uv tool install` to install tools globally (the equivalent of `pip install --system` or `pipx`). Prefer `uvx <tool>` to run installed tools without pinning them.
- Node.js: use `pnpm install`, `pnpm run`, `pnpm exec` for project work; use `pnpm dlx` to run one-off packages (the equivalent of `npx`). Always pin versions when possible.

Never use `pip`, `python -m pip`, `npm`, or `yarn` directly. If `uv` or `pnpm` are not available on the system, note the limitation and fall back.

## Research and Uncertainty Protocol

When you are uncertain about something, or when official documentation and best practices would help you make a better decision, **you must search for authoritative sources before guessing**.

### When to search

- You are unsure about a library's API, configuration, or behavior
- You want to follow current best practices for a task
- You are working with unfamiliar code, tools, or frameworks
- You need to verify how something works rather than assume
- The user asks for recommendations or guidance on how to do something

### How to search

1. **Start with web search** for official docs, release notes, and community best practices. Prefer official documentation over third-party blog posts.
2. **Use the `gh` CLI for anything on github.com** — repos, issues, pull requests, code, releases, and GitHub-hosted docs. `gh` is authenticated, structured, and rate-limit-safe. **Never use `fetch_content`, `web_search`, or manual API calls for github.com URLs.**
3. **Use `fetch_content` for non-GitHub URLs** — documentation sites, blog posts, or other web pages with deeper context.

### Key principle

**When in doubt, search it out.** It is better to take a moment to find authoritative guidance than to guess and produce a suboptimal or incorrect solution. Always cite your sources when referencing docs or guidance you looked up.
