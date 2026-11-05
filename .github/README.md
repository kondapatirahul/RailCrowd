# GitHub Collaboration Configuration

This directory contains repository collaboration automation and templates.

- `workflows/ci.yml`: installs Python dependencies and runs the test suite on pushes and pull requests targeting `main`.
- `PULL_REQUEST_TEMPLATE.md`: standardizes pull request descriptions.
- `ISSUE_TEMPLATE/bug_report.yml`: gathers reproducible bug reports.
- `ISSUE_TEMPLATE/feature_request.yml`: captures user problems and proposed improvements.

The CI workflow skips pytest when no test modules exist yet. Once application tests are added, it runs them automatically.

The workflow uses read-only repository permissions and does not require secrets for the current test setup.
