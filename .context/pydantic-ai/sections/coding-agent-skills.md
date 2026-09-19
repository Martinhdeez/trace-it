# [Coding Agent Skills](https://pydantic.dev/docs/ai/overview/coding-agent-skills/)

# Coding Agent Skills

If you're building Pydantic AI applications with a coding agent, you can install the Pydantic AI skill from the [`pydantic/skills`](https://github.com/pydantic/skills) repository to give your agent up-to-date framework knowledge.

[Agent skills](https://agentskills.io/) are packages of instructions and reference material that coding agents load on demand. With the skill installed, coding agents have access to Pydantic AI patterns, architecture guidance, and common task references covering [tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/), [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/), [structured output](https://pydantic.dev/docs/ai/core-concepts/output/), [streaming](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-events-and-final-output), [testing](https://pydantic.dev/docs/ai/guides/testing/), [multi-agent delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), [hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/), and [agent specs](https://pydantic.dev/docs/ai/core-concepts/agent-spec/).

Note

If you want to build agent skills for your Pydantic AI agent, see the [Agent Skills](https://pydantic.dev/docs/ai/capabilities/third-party/#agent-skills) entry in the Third-party capabilities section on the Capabilities page.

## Installation

### Claude Code

Install the [official Pydantic AI plugin](https://claude.com/plugins/pydantic-ai) from the Anthropic marketplace, which is available by default:

Terminal

```bash
claude plugin install pydantic-ai@claude-plugins-official
```

As an alternative, you can install from the [`pydantic/skills`](https://github.com/pydantic/skills) marketplace, which bundles the Pydantic AI skill alongside other Pydantic-maintained skills:

Terminal

```bash
claude plugin marketplace add pydantic/skills
claude plugin install ai@pydantic-skills
```

### Cross-Agent (agentskills.io)

Install the Pydantic AI skill using the [skills CLI](https://github.com/vercel-labs/skills):

Terminal

```bash
npx skills add pydantic/skills
```

This works with 30+ agents via the [agentskills.io](https://agentskills.io/) standard, including Claude Code, Codex, Cursor, and Gemini CLI.

### Library Skills

Pydantic AI also ships its skill bundled with the package, so you can install it directly from your project's dependencies via [library-skills.io](https://library-skills.io/):

Terminal

```bash
uvx library-skills --all
```

The `--all` flag is required because the skill is bundled in `pydantic-ai-slim`, which is a transitive dependency of the `pydantic-ai` meta-package. Without it, `library-skills` only scans direct dependencies and won't discover the skill.

Add `--claude` to also install into `.claude/skills/` alongside the default `.agents/skills/` directory, since Claude Code doesn't read from `.agents/`.

## See Also

-   [`pydantic/skills`](https://github.com/pydantic/skills): source repository
-   [agentskills.io](https://agentskills.io/): the open standard for agent skills
-   [library-skills.io](https://library-skills.io/): install agent skills bundled with your project's dependencies

---
