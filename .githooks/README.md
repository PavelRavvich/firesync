# Git Hooks

This directory contains Git hooks for the FireSync project.

## Setup

To install the hooks, run:

```bash
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Or use git config to set the hooks directory:

```bash
git config core.hooksPath .githooks
```

## Available Hooks

### pre-commit

Runs all unit tests before allowing a commit. If any tests fail, the commit is aborted.

This ensures that:
- All 148 tests pass before code is committed
- Code quality is maintained
- Breaking changes are caught early

**Note:** Tests must pass locally before you can commit. This prevents broken code from entering the repository.
