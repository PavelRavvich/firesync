# FireSync - Infrastructure as Code for Firestore

## Project Overview

**FireSync** is a Python-based tool for managing Firestore database schemas as code. It enables version control and deployment automation for:
- Composite indexes
- Single-field indexes
- TTL (Time-To-Live) policies

Built by Pavel Ravvich and licensed under the MIT License.

## Core Concepts

### Workflow Pattern
FireSync follows a Terraform-like workflow:
1. **Pull** - Export current Firestore schema from GCP to local JSON files
2. **Plan** - Compare local schema files against remote Firestore state
3. **Apply** - Deploy local schema changes to Firestore

### Environment Management
Supports multiple environments (dev, staging, production) with separate GCP service account credentials stored in `secrets/gcp-key-{env}.json`.

## Project Structure

```
firesync/
├── core/                   # Python package with core functionality
│   ├── __init__.py
│   ├── config.py           # Configuration and environment management
│   ├── gcloud.py           # GCloud CLI wrapper
│   ├── normalizers.py      # Data normalization functions
│   ├── operations.py       # Resource-specific operations
│   └── schema.py           # Schema file loading and validation
├── tests/                  # Unit tests (stdlib unittest)
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_normalizers.py
│   ├── test_operations.py
│   └── test_schema.py
├── firestore_pull.py       # CLI: Exports remote Firestore schema to local JSON
├── firestore_plan.py       # CLI: Compares local vs remote, shows diff
├── firestore_apply.py      # CLI: Applies local schema to Firestore
├── firestore_schema/       # Schema definitions (gitignored for remote state)
│   ├── composite-indexes.json
│   ├── field-indexes.json
│   └── ttl-policies.json
└── secrets/                # GCP service account keys (never commit!)
    ├── gcp-key-dev.json
    ├── gcp-key-staging.json
    └── gcp-key-production.json
```

## Tools & Scripts

### firestore_pull.py
Exports current Firestore configuration from GCP to local JSON files.

**Usage:**
```bash
./firestore_pull.py --env=dev
./firestore_pull.py --env=production
ENV=staging ./firestore_pull.py
```

**What it exports:**
- Composite indexes → `firestore_schema/composite-indexes.json`
- Field indexes → `firestore_schema/field-indexes.json`
- TTL policies → `firestore_schema/ttl-policies.json`

### firestore_plan.py
Compares local schema files against remote Firestore state and shows what would change.

**Usage:**
```bash
./firestore_plan.py --env=dev
./firestore_plan.py --env=staging --schema-dir=custom_schema
```

**Output indicators:**
- `[+] WILL CREATE` - Resource exists locally but not remotely
- `[-] WILL DELETE` - Resource exists remotely but not locally
- `[~] WILL UPDATE` - Resource exists in both but differs

### firestore_apply.py
Applies local schema definitions to Firestore using gcloud commands.

**Usage:**
```bash
./firestore_apply.py --env=dev
./firestore_apply.py --env=production --schema-dir=custom_schema
```

**Behavior:**
- Skips resources that already exist (idempotent)
- Logs all gcloud commands before execution
- Handles permission errors gracefully

## Development Guidelines

### Architecture Patterns

The codebase follows a modular architecture with clear separation of concerns:

1. **core.config** - Configuration and environment management
   - `Environment` enum for type-safe environment values
   - `FiresyncConfig` dataclass for configuration state
   - Validates credentials and paths on initialization

2. **core.gcloud** - GCloud CLI wrapper
   - `GCloudClient` class encapsulates all gcloud interactions
   - Cross-platform binary detection (Windows vs Unix)
   - Handles authentication, command execution, error handling

3. **core.normalizers** - Data normalization
   - Pure functions for extracting and normalizing schema data
   - Handles multiple GCP API response formats
   - Ensures consistent comparison between local and remote schemas

4. **core.schema** - Schema file operations
   - Loading and saving JSON schema files
   - Validation functions for each resource type
   - `SchemaFile` class with file name constants

5. **core.operations** - Resource-specific logic
   - `CompositeIndexOperations` for composite indexes
   - `FieldIndexOperations` for single-field indexes
   - `TTLPolicyOperations` for TTL policies
   - Each class provides: normalize, compare, build_create_command

6. **CLI Scripts** (firestore_pull.py, firestore_plan.py, firestore_apply.py)
   - Thin wrappers that orchestrate the core modules
   - Handle command-line argument parsing
   - Provide user-facing output and error messages

### Code Style

- **Type hints:** Use type annotations on all function signatures
- **Dataclasses:** Use for configuration and data structures
- **Enums:** Use for fixed sets of values (Environment, QueryScope, etc.)
- **Docstrings:** Include for all public functions and classes
- **Pathlib:** Use `pathlib.Path` instead of `os.path`
- **F-strings:** Use for string formatting
- **Logging:** Use `logging` module instead of print in library code
- **Status indicators:** Print with `[!]` errors, `[+]` success, `[~]` info in CLI scripts

### Testing

- **Framework:** Use stdlib `unittest` (no external dependencies)
- **Structure:** Mirror source structure in `tests/` directory
- **Coverage:** Test all public functions and methods
- **Mocking:** Use `unittest.mock` for external dependencies (filesystem, subprocess)
- **Run tests:** `python -m unittest discover tests`

Example test pattern:
```python
import unittest
from unittest.mock import patch
from core.config import FiresyncConfig

class TestFiresyncConfig(unittest.TestCase):
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_from_args_success(self, mock_read_text, mock_exists):
        mock_exists.return_value = True
        mock_read_text.return_value = '{"project_id": "test", "client_email": "test@test.com"}'
        config = FiresyncConfig.from_args(env="dev")
        self.assertEqual(config.project_id, "test")
```

### Cross-platform Compatibility

Handle Windows vs Unix gcloud binary in `core.gcloud`:
```python
def get_gcloud_binary() -> str:
    return "gcloud.cmd" if platform.system() == "Windows" else "gcloud"
```

### Error Handling

- **Validation:** Check inputs early in `config.py`
- **Exceptions:** Let library code raise exceptions with context
- **Exit codes:** CLI scripts catch exceptions and call `sys.exit(1)` on errors
- **Logging:** Use logger.error() for debugging, print() for user messages
- **Graceful degradation:** Apply operations tolerate "already exists" errors

### Security

- **NEVER commit service account keys** - store in `secrets/` (gitignored)
- **Validate credentials** in `FiresyncConfig.from_args()`
- **Extract project_id** from key file (don't hardcode)
- **Service account auth** in `GCloudClient.activate_service_account()`

### GCP Integration

GCloud wrapper pattern in `core.gcloud.GCloudClient`:
- Always specify `--project={project_id}` in commands
- Use `--format=json` for programmatic parsing
- Use `--quiet` flag in apply commands to skip confirmations
- Authenticate service account before any gcloud operations
- Use `run_command_tolerant()` for idempotent apply operations

### Schema File Format

All schema JSON files are arrays of objects following GCP's Firestore API format:
- `composite-indexes.json` - Array of composite index definitions
- `field-indexes.json` - Array of field configuration objects
- `ttl-policies.json` - Array of TTL policy definitions

### Normalization Logic

Implemented in `core.normalizers` module:
- Normalize field order for composite indexes (alphabetically sorted)
- Handle both `collectionGroupId` and `collectionGroup` field names
- Parse collection names from resource paths when direct field is missing
- Convert enum values to lowercase for consistent comparison
- Extract fields from both direct properties and nested resource names

## Dependencies

**Required:**
- Python 3.7+
- Google Cloud SDK (`gcloud` CLI)
- GCP service account with Firestore permissions:
  - `datastore.indexes.list`
  - `datastore.indexes.create`
  - `datastore.indexes.update`
  - `firebase.projects.get`

**Python stdlib only** - no external packages required.

## Common Workflows

### Initial Setup
```bash
# 1. Place service account key
mkdir -p secrets/
cp ~/Downloads/gcp-key.json secrets/gcp-key-dev.json

# 2. Pull current schema
./firestore_pull.py --env=dev

# 3. Commit schema to git
git add firestore_schema/
git commit -m "Initial Firestore schema"
```

### Making Schema Changes
```bash
# 1. Edit schema JSON files manually
vim firestore_schema/composite-indexes.json

# 2. Preview changes
./firestore_plan.py --env=dev

# 3. Apply changes
./firestore_apply.py --env=dev

# 4. Commit changes
git add firestore_schema/
git commit -m "Add index for user queries"
```

### Promoting to Production
```bash
# 1. Apply dev schema to staging
./firestore_apply.py --env=staging

# 2. Verify in staging environment
# ... manual testing ...

# 3. Apply to production
./firestore_plan.py --env=production
./firestore_apply.py --env=production
```

## Limitations & Known Issues

- **Delete operations:** Plan shows deletions but Apply doesn't implement them (safety feature)
- **Field index updates:** May show as "already exists" if configuration matches
- **TTL period changes:** Displays planned updates but may require manual verification
- **Cross-region indexes:** Not explicitly handled, assumes single region per project

## Future Enhancements

Consider implementing:
- Delete functionality with `--force` flag
- Dry-run mode for Apply
- Diff output formatting (colored terminal output)
- Backup before apply
- Rollback capability
- Support for Firestore Security Rules
- CI/CD integration examples
