# Contributing to FireSync

Thank you for your interest in contributing to FireSync! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment for all contributors

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/firesync.git
   cd firesync
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/pavelravvich/firesync.git
   ```

## Development Setup

### Prerequisites

- Python 3.7 or higher
- Google Cloud SDK (gcloud CLI)
- GCP service account with Firestore permissions for testing

### Environment Setup

1. Create test GCP projects for development:
   - `your-test-dev`
   - `your-test-staging`
   - `your-test-production`

2. Set up service account keys:
   ```bash
   mkdir -p secrets/
   # Add your test service account keys
   ```

3. Test the scripts:
   ```bash
   ./firestore_pull.py --env=dev
   ./firestore_plan.py --env=dev
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-security-rules-support`
- `fix/ttl-parsing-error`
- `docs/update-readme-examples`
- `refactor/improve-error-handling`

### Workflow

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the coding standards

3. Test your changes thoroughly

4. Commit with clear messages:
   ```bash
   git commit -m "Add support for security rules export"
   ```

5. Keep your branch updated:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

## Coding Standards

### Python Style

FireSync follows these conventions:

#### Import Style
```python
# Compact imports on one line
import argparse, json, os, pathlib, subprocess, sys
```

#### File Operations
```python
# Use pathlib for file operations
path = pathlib.Path("firestore_schema/composite-indexes.json")
data = json.loads(path.read_text(encoding="utf-8"))
```

#### String Formatting
```python
# Use f-strings
print(f"[~] Environment: {env}")
print(f"[+] Successfully exported {count} indexes")
```

#### Error Messages
```python
# Use clear prefixes for output
print(f"[!] Error: {error_message}")    # Errors
print(f"[+] Success: {success_msg}")    # Success
print(f"[~] Info: {info_message}")      # Info
print(f"[-] Removed: {item}")           # Deletions
```

#### Cross-platform Compatibility
```python
# Handle Windows vs Unix differences
GCLOUD = "gcloud.cmd" if platform.system() == "Windows" else "gcloud"
```

#### Error Handling
```python
# Validate inputs early
if not env:
    print("[!] Please provide --env flag or set ENV environment variable.")
    sys.exit(1)

# Use try-except for external operations
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as e:
    print(f"[!] Failed to parse {path}: {e}")
    sys.exit(1)
```

### Code Organization

- Keep scripts standalone and executable
- Add shebang: `#!/usr/bin/env python3`
- Use descriptive variable names
- Avoid unnecessary abstractions
- No external dependencies (stdlib only)

### Documentation

- Add docstrings only for complex functions
- Use clear, concise comments where logic isn't obvious
- Update README.md when adding new features
- Update CLAUDE.MD with architectural decisions

## Testing

### Manual Testing

Test your changes across all three environments:

```bash
# Test pull
./firestore_pull.py --env=dev

# Test plan
./firestore_plan.py --env=dev

# Test apply (in test project only!)
./firestore_apply.py --env=dev
```

### Cross-platform Testing

If possible, test on:
- Linux
- macOS
- Windows

### Edge Cases to Test

- Empty schema files
- Missing service account keys
- Invalid JSON
- Permission errors
- Network failures
- Large schemas (100+ indexes)

## Submitting Changes

### Pull Request Process

1. Update documentation if needed
2. Ensure all tests pass
3. Update CHANGELOG.md (if it exists)
4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Create a Pull Request on GitHub

### Pull Request Guidelines

**Title:**
- Use clear, descriptive titles
- Examples: "Add support for Firestore Security Rules", "Fix TTL policy parsing"

**Description:**
Include:
- What changed and why
- How to test the changes
- Any breaking changes
- Related issue numbers (if applicable)

**Example PR Description:**
```markdown
## Summary
Adds support for exporting and applying Firestore Security Rules.

## Changes
- Added `firestore_rules_pull.py` script
- Added `firestore_rules_apply.py` script
- Updated README with rules documentation
- Added rules schema examples to CLAUDE.MD

## Testing
- Tested on dev/staging/production environments
- Verified rules export/apply cycle
- Tested with complex rule sets

## Breaking Changes
None

Fixes #42
```

## Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify it's not a configuration problem
3. Test with the latest version

### Bug Report Template

```markdown
## Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 13.0, Ubuntu 22.04, Windows 11]
- Python Version: [e.g., 3.9.7]
- gcloud Version: [output of `gcloud --version`]
- FireSync Version/Commit: [e.g., main branch, commit abc123]

## Additional Context
Error messages, logs, screenshots, etc.
```

## Suggesting Enhancements

### Feature Request Template

```markdown
## Feature Description
Clear description of the feature

## Use Case
Why is this feature needed? What problem does it solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
Other approaches you've considered

## Additional Context
Examples, mockups, related features, etc.
```

## Project Priorities

### High Priority
- Bug fixes
- Security improvements
- Cross-platform compatibility
- Documentation improvements

### Medium Priority
- New Firestore features support
- Performance optimizations
- Better error messages
- CLI improvements

### Low Priority
- Code refactoring (unless fixing bugs)
- Style changes
- Feature additions that complicate core workflow

## Questions?

If you have questions about contributing:
1. Check existing documentation (README.md, CLAUDE.MD)
2. Search existing issues
3. Open a new issue with the `question` label

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to FireSync!
