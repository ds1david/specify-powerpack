# Portability

PowerPack's project workflow follows:

```text
DISCOVER CAPABILITY → SELECT STRATEGY → EXECUTE CONTRACT
```

It avoids assuming a language, framework, build tool or operating system.

## Supported host model

The CLI is Python-based and intended for Linux, WSL, macOS and Windows. CI exercises multiple Python versions on Ubuntu, Windows and macOS.

First-install wrappers are deliberately thin:

- `install.sh` → `install.py`
- `install.ps1` → `install.py`

Python owns the cross-platform bootstrap logic.

## Browserless review portability

The supported review path has no Chrome/Chromium/Playwright/CDP/Web2API dependency. It requires Codex CLI plus account/network access to ChatGPT backend and the GitHub App.

This removes browser-profile and cross-OS browser-session coupling, particularly the former Windows/WSL split.

## Project execution portability

Quality gates are discovered from the consuming project. PowerPack does not embed one universal Maven/Gradle/npm/pytest command.

Unknown or ambiguous capability resolution fails closed unless the project defines a deterministic custom gate.

## External-service boundary

Browserless does not mean offline. Project discovery/context and GitHub connector discovery require ChatGPT backend access; PR evidence requires GitHub through Codex Apps.

These account-scoped backend and connector surfaces are not treated as stable public OpenAI API contracts. PowerPack therefore keeps them isolated behind provider modules and fails closed when observed behavior changes.

See [`DECISIONS_AND_TRADEOFFS.md`](DECISIONS_AND_TRADEOFFS.md).
