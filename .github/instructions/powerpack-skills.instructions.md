---
applyTo: "src/speckit_powerpack/assets/**/*.md,.specify/extensions/**/*.md,.github/skills/**/*.md,.github/agents/**/*.md,.github/prompts/**/*.md"
---

# PowerPack and generated skill rules

- Keep the semantic contract portable across supported agents. Copilot-specific syntax/layout is an adapter concern.
- Prefer native Spec Kit extension commands plus thin companion presets for upstream command composition. Do not rebuild a monolithic legacy preset runtime.
- Do not manually treat generated `.github/skills/speckit-*`, `.github/agents/speckit.*`, or `.github/prompts/speckit.*` files as authoritative source. Change the extension/preset/template source and rescaffold when possible.
- When one PowerPack command references another Spec Kit/extension command in a source template, use the agent-neutral command-reference mechanism supported by Spec Kit rather than embedding one agent's literal invocation form.
- Do not use a fixed portable `allowed-tools` list merely to mirror Copilot, Claude, Codex, or another single agent. Express required capabilities and permitted effects instead.
- Tool availability never expands mutation authority. Read/search/retrieval may be broad; writes must stay within the capability's explicit mutation surface.
- Hooks that produce durable workflow facts must persist/reload PowerPack JSON state. They must not depend on environment variables exported by a previous independent hook.
- Optional Copilot Canvas/UI integration must consume machine-readable PowerPack state and invoke the same command/runtime contract; never duplicate convergence/review semantics in UI JavaScript.
