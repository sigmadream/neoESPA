# Repository Guidelines

## Scope

- This file contains global authoring, communication, and documentation rules.
- Do not treat this file as a source of project-specific architecture, runtime, directory, or command assumptions.
- Keep project-specific guidance in separate repository-local documents when needed.

## Communication & Language

- Default all user-facing communication to Korean.
- Interviews, clarifying questions, progress updates, intermediate findings, summaries, final results, and operational guidance should be written in Korean.
- Write all artifacts such as `task.md`, `implementation_plan.md`, and `walkthrough.md`, and their accompanying explanations, in Korean.
- Keep code, commands, file paths, API field names, identifiers, and raw logs or errors in their original form.
- When quoting English logs or errors, preserve the original text and add a short Korean explanation when helpful.
- Only switch away from Korean when the user explicitly requests another language.

## Korean Writing Style

- Use polite honorific Korean for all Korean-facing documentation and responses.
- When revising existing Korean text, preserve the original meaning while improving the text in polite honorific style.
- Avoid non-professional intensifiers or adjectives such as `너무`, `매우`, and `많이` unless they are required for precision.
- For English and other languages, use polite, respectful phrasing.

## Markdown & Documentation Style

- Use Markdown headings to organize documents clearly.
- Prefer short, practical paragraphs and bullets.
- Keep examples minimal and concrete.
- Preserve technical literals exactly: code, commands, file paths, environment variables, identifiers, API fields, and error messages.
- Do not use decorative emphasis such as `**...**` for words or sentences unless it is structurally required.
- When editing documents, improve clarity, consistency, and tone without adding unnecessary flourish.

## Python Project Preferences

- Use `uv` to create, manage, and run Python projects.
- Prefer Pythonic code.
- Do not add type hints unless a separate instruction explicitly requires them.
- Use `pytest` for tests.
