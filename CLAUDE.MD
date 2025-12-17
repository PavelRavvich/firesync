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
├── firestore_pull.py       # Exports remote Firestore schema to local JSON
├── firestore_plan.py       # Compares local vs remote, shows diff
├── firestore_apply.py      # Applies local schema to Firestore
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

### Code Style
- Use compact imports: `import argparse, json, os, pathlib, subprocess, sys`
- Prefer pathlib for file operations
- Use f-strings for formatting
- Keep scripts standalone and executable (`#!/usr/bin/env python3`)
- Print status with visual indicators: `[!]` errors, `[+]` success, `[~]` info

### Cross-platform Compatibility
Handle Windows vs Unix gcloud binary:
```python
GCLOUD = "gcloud.cmd" if platform.system() == "Windows" else "gcloud"
```

### Error Handling
- Validate environment and credentials before GCP calls
- Use `subprocess.run(..., check=True)` for critical commands
- Provide actionable error messages with context
- Exit with `sys.exit(1)` on fatal errors

### Security
- **NEVER commit service account keys** - store in `secrets/` (gitignored)
- Validate that `secrets/gcp-key-{env}.json` exists before use
- Extract `project_id` and `client_email` from key file (don't hardcode)
- Use service account activation instead of user credentials

### GCP Integration
- Always specify `--project={PROJECT_ID}` in gcloud commands
- Use `--format=json` for programmatic parsing
- Use `--quiet` flag in apply commands to skip confirmations
- Authenticate service account before any gcloud operations

### Schema File Format
All schema JSON files should be arrays of objects following GCP's Firestore API format:
- `composite-indexes.json` - Array of composite index definitions
- `field-indexes.json` - Array of field configuration objects
- `ttl-policies.json` - Array of TTL policy definitions

### Normalization Logic
When comparing schemas:
- Normalize field order for composite indexes (alphabetically sorted)
- Handle both `collectionGroupId` and `collectionGroup` field names
- Parse collection names from resource paths when direct field is missing
- Convert enum values to lowercase for consistent comparison

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
