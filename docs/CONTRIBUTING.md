# Contributing to RailCrowd

## Branch workflow

Use a focused branch for each independently reviewable change.

Examples:
- `chore/repository-setup`
- `chore/backend-structure`
- `feature/train-search`
- `fix/crowd-report-expiry`
- `test/crowd-engine`

Do not commit directly to `main`.

## Commit message convention

Use concise conventional commit prefixes:

- `feat:` new functionality
- `fix:` bug fixes
- `chore:` project setup or maintenance
- `docs:` documentation
- `test:` tests
- `refactor:` internal restructuring
- `style:` presentation or formatting changes

Example:

`chore: add initial project documentation`

## Pull requests

Each pull request should:
1. Explain the user or developer problem being addressed.
2. Summarize the actual files and behavior changed.
3. Include test results when applicable.
4. Identify configuration or migration implications.
5. Avoid unrelated changes.

## Local change workflow

1. Update `main`.
2. Create a focused branch.
3. Make the change.
4. Run relevant tests.
5. Commit and push.
6. Open a pull request against `main`.
7. Review and merge.
8. Update the local `main` before the next dependent increment.

## Repository hygiene

Never commit `.env`, credentials, virtual environments, local SQLite databases, cache directories or generated test artifacts.
