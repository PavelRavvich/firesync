# FireSync

[![PyPI version](https://img.shields.io/pypi/v/firestore-schema-migration.svg)](https://pypi.org/project/firestore-schema-migration/)
[![Tests](https://github.com/PavelRavvich/firesync/actions/workflows/pipeline.yml/badge.svg)](https://github.com/PavelRavvich/firesync/actions/workflows/pipeline.yml)
[![Coverage](https://img.shields.io/badge/coverage-84%25-green.svg)](https://github.com/PavelRavvich/firesync/actions/workflows/pipeline.yml)
[![Python 3.8-3.14](https://img.shields.io/badge/python-3.8--3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](https://github.com/PavelRavvich/firesync)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CodeQL](https://img.shields.io/badge/CodeQL-enabled-brightgreen?logo=github)](https://github.com/PavelRavvich/firesync/security/code-scanning)
[![TruffleHog](https://img.shields.io/badge/TruffleHog-enabled-blue?logo=security)](https://github.com/PavelRavvich/firesync/security)

**Infrastructure as Code for Google Cloud Firestore**

FireSync is a lightweight Python tool that brings version control and deployment automation to your Firestore database schema. Manage composite indexes, single-field indexes, and TTL policies using a familiar pull-plan-apply workflow inspired by Terraform.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Commands Overview](#commands-overview)
- [Workspace Configuration](#workspace-configuration)
- [Usage Examples](#usage-examples)
- [Schema Files](#schema-files)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🔄 **Version Control** - Track Firestore schema changes in git
- 🔍 **Plan Before Apply** - Preview changes before deploying
- 🛡️ **Safety First** - Idempotent operations, no accidental deletions
- 🔑 **Flexible Auth** - Use any GCP service account key
- 🐍 **Zero Dependencies** - Pure Python stdlib, just needs gcloud CLI
- 🪟 **Cross-Platform** - Works on Linux, macOS, and Windows

## Quick Start

### Prerequisites

- Python 3.8+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (gcloud CLI)
- GCP service account with Firestore permissions:
  - `datastore.indexes.list`
  - `datastore.indexes.create`
  - `datastore.indexes.update`
  - `firebase.projects.get`

### Installation

Install from PyPI:

```bash
pip install firestore-schema-migration
```

This installs the `firesync` command globally.

**Alternative: Install from source**

```bash
git clone https://github.com/PavelRavvich/firesync.git
cd firesync
pip install -e .
```

### All Commands

Get help on any command:

```bash
firesync --help
firesync pull --help
firesync plan --help
firesync apply --help
firesync env --help
```

**Available Commands:**

- `firesync init` - Initialize workspace with config.yaml
- `firesync env add <name>` - Add environment to workspace
- `firesync env remove <name>` - Remove environment from workspace
- `firesync env list` - List all environments
- `firesync env show <name>` - Show environment details
- `firesync pull` - Export Firestore schema to local files
- `firesync plan` - Compare local vs remote schemas
- `firesync apply` - Deploy local schema to Firestore

### Quick Setup

1. Initialize workspace:
```bash
firesync init
```

2. Add your environments:
```bash
# Using direct path to key file
firesync env add dev --key-path=./secrets/gcp-key-dev.json --description="Development"

# Using environment variable (auto-detects JSON content or file path)
firesync env add prod --key-env=GCP_PROD_KEY --description="Production"
```

3. Pull schemas from all environments:
```bash
firesync pull --all
```

## Commands Overview

### firesync init

Initialize a new FireSync workspace. Creates `config.yaml` to manage multiple environments.

```bash
# Initialize in current directory
firesync init

# Initialize in custom directory
firesync init --path ./my-project
```

**Options:**
- `--path PATH` - Target directory for workspace (default: current directory)

Creates:
- `config.yaml` - Workspace configuration
- `firestore_schema/` - Default schema directory

### firesync env

Manage environments in your workspace.

**Authentication Options:**

FireSync supports two ways to provide GCP service account credentials:

| Option | Description | Use Case |
|--------|-------------|----------|
| `--key-path` | Direct path to key file | Local development |
| `--key-env` | Environment variable name | CI/CD and shared environments |

The `--key-env` option is smart: it auto-detects whether the environment variable contains:
- **JSON content** (the key itself) - creates a temp file for gcloud
- **File path** (path to key file) - reads the key from that path

**Add environment:**
```bash
# Option 1: Direct path to key file
firesync env add dev --key-path=./secrets/gcp-key-dev.json

# Option 2: Environment variable (auto-detects JSON content or file path)
firesync env add prod --key-env=GCP_PROD_KEY --description="Production environment"
```

**Example environment variable usage:**
```bash
# Store JSON content in env var (for CI/CD secrets)
export GCP_KEY='{"type":"service_account","project_id":"my-project",...}'

# Or store path to key file in env var
export GCP_KEY='/path/to/service-account.json'

# Both work with the same command:
firesync env add prod --key-env=GCP_KEY
```

**List environments:**
```bash
firesync env list
# Shows environment names with key paths (including absolute paths) or key env variables
# Example output:
#   dev
#     key_path: secrets/gcp-key-dev.json - Development environment (/absolute/path/to/secrets/gcp-key-dev.json)
#   prod
#     key_env: GCP_PROD_KEY - Production environment
```

**Show environment details:**
```bash
firesync env show dev
```

**Remove environment:**
```bash
firesync env remove dev
```

### firesync pull

Export Firestore schema from GCP to local JSON files.

**Pull all environments:**
```bash
firesync pull --all
```

**Pull single environment:**
```bash
firesync pull --env=dev
```

Creates three JSON files in schema directory:
- `composite-indexes.json` - Composite indexes
- `field-indexes.json` - Single-field indexes
- `ttl-policies.json` - TTL policies

### firesync plan

Compare local schema against remote Firestore and preview changes.

**Compare local vs remote:**
```bash
firesync plan --env=dev
```

**Migration mode - compare two environments (local vs local):**
```bash
firesync plan --env-from=dev --env-to=staging
```

**With custom schema directory:**
```bash
firesync plan --env=dev --schema-dir=custom_schemas
```

Output shows:
- `[+] WILL CREATE` - Resource exists locally but not remotely
- `[-] WILL DELETE` - Resource exists remotely but not locally
- `[~] WILL UPDATE` - Resource differs between local and remote
- `[~] No changes` - Schemas are in sync

### firesync apply

Deploy local schema to Firestore.

**Apply to environment:**
```bash
firesync apply --env=dev
```

**Migration mode - apply source schema to target environment:**
```bash
firesync apply --env-from=dev --env-to=staging
```

**With custom schema directory:**
```bash
firesync apply --env=prod --schema-dir=custom_schemas
```

**Note:** Apply operations are idempotent and skip existing resources. Delete operations are not implemented for safety.

## Workspace Configuration

FireSync uses `config.yaml` to manage multiple environments with separate schemas.

### Workspace Structure

```
your-project/
├── config.yaml                    # Workspace configuration
├── firestore_schema/              # Schema directories per environment
│   ├── dev/
│   │   ├── composite-indexes.json
│   │   ├── field-indexes.json
│   │   └── ttl-policies.json
│   ├── staging/
│   │   ├── composite-indexes.json
│   │   ├── field-indexes.json
│   │   └── ttl-policies.json
│   └── prod/
│       ├── composite-indexes.json
│       ├── field-indexes.json
│       └── ttl-policies.json
└── secrets/                       # GCP service account keys (gitignored)
    ├── gcp-key-dev.json
    ├── gcp-key-staging.json
    └── gcp-key-prod.json
```

### config.yaml Format

```yaml
version: 1
schema_base_dir: firestore_schema

environments:
  dev:
    key_path: secrets/gcp-key-dev.json        # Direct path to key file
    description: "Development environment"
  prod:
    key_env: GCP_PROD_KEY                     # Env var (JSON content OR file path)
    description: "Production environment"
```

**Fields:**
- `version` - Config format version (always 1)
- `schema_base_dir` - Base directory for all schema files
- `environments` - Map of environment configurations (choose ONE per environment):
  - `key_path` - Direct path to GCP service account key file (relative to config.yaml)
  - `key_env` - Environment variable name (auto-detects JSON content or file path)
  - `description` - Optional description of the environment

## Usage Examples

### Basic Workflow

```bash
# 1. Initialize workspace
firesync init

# 2. Add environment
firesync env add dev --key-path=./secrets/gcp-key-dev.json --description="Development environment"

# 3. Pull current schema
firesync pull --env=dev

# 4. Edit schema files (add/modify indexes)
vim firestore_schema/dev/composite-indexes.json

# 5. Preview changes
firesync plan --env=dev

# 6. Apply changes
firesync apply --env=dev

# 7. Commit to git
git add config.yaml firestore_schema/
git commit -m "Add user query index"
```

### Multi-Environment Management

Manage dev, staging, and production environments separately:

```bash
# Set up all environments
firesync init
firesync env add dev --key-path=./secrets/gcp-key-dev.json --description="Development environment"
firesync env add staging --key-path=./secrets/gcp-key-staging.json --description="Staging environment"
firesync env add prod --key-env=GCP_PROD_KEY --description="Production environment"

# Pull schemas from all environments
firesync pull --all

# Work on dev environment
vim firestore_schema/dev/composite-indexes.json
firesync plan --env=dev
firesync apply --env=dev

# Promote dev schema to staging
# --env-from: source environment (reads LOCAL schema files from firestore_schema/dev/)
# --env-to: target environment (applies to REMOTE Firestore in staging project)
firesync plan --env-from=dev --env-to=staging
firesync apply --env-from=dev --env-to=staging

# IMPORTANT: Local files for staging are NOT updated automatically!
# Pull staging schema to update local files after migration:
firesync pull --env=staging

# After testing, promote to production
firesync plan --env-from=dev --env-to=prod
firesync apply --env-from=dev --env-to=prod

# Update production local files
firesync pull --env=prod
```

### Environment Migration

Compare and migrate schemas between environments:

```bash
# Compare dev and staging schemas (local vs local)
firesync plan --env-from=dev --env-to=staging

# Apply dev schema to staging environment
firesync apply --env-from=dev --env-to=staging

# Verify changes
firesync pull --env=staging
git diff firestore_schema/staging/
```

## Configuration

### Custom Schema Directory

Override the schema directory for any command:

```bash
firesync plan --env=dev --schema-dir=custom_schemas
firesync apply --env=staging --schema-dir=backups/schemas_2024
```

## Schema Files

FireSync manages three types of Firestore configurations:

### composite-indexes.json
Composite indexes for complex queries spanning multiple fields. Each index includes metadata like `name`, `state`, and `density` from Firestore.

Example:
```json
[
  {
    "density": "SPARSE_ALL",
    "fields": [
      {
        "fieldPath": "userId",
        "order": "ASCENDING"
      },
      {
        "fieldPath": "status",
        "order": "ASCENDING"
      },
      {
        "fieldPath": "createdAt",
        "order": "DESCENDING"
      },
      {
        "fieldPath": "__name__",
        "order": "DESCENDING"
      }
    ],
    "name": "projects/your-project-id/databases/(default)/collectionGroups/orders/indexes/CICAgICAgICA",
    "queryScope": "COLLECTION",
    "state": "READY"
  }
]
```

**Note**: When creating new indexes manually, you only need to specify `fields` and `queryScope`. The `name`, `state`, and `density` fields are populated by Firestore.

### field-indexes.json
Single-field index configurations including default index settings and exemptions.

Example:
```json
[
  {
    "indexConfig": {
      "indexes": [
        {
          "fields": [
            {
              "fieldPath": "*",
              "order": "ASCENDING"
            }
          ],
          "queryScope": "COLLECTION",
          "state": "READY"
        },
        {
          "fields": [
            {
              "fieldPath": "*",
              "order": "DESCENDING"
            }
          ],
          "queryScope": "COLLECTION",
          "state": "READY"
        },
        {
          "fields": [
            {
              "arrayConfig": "CONTAINS",
              "fieldPath": "*"
            }
          ],
          "queryScope": "COLLECTION",
          "state": "READY"
        }
      ]
    },
    "name": "projects/your-project-id/databases/(default)/collectionGroups/__default__/fields/*"
  }
]
```

**Note**: The `__default__/fields/*` entry controls default indexing behavior for all collections.

### ttl-policies.json
Time-to-live policies for automatic document deletion. Documents are deleted when the TTL field value expires.

Example:
```json
[
  {
    "indexConfig": {
      "ancestorField": "projects/your-project-id/databases/(default)/collectionGroups/__default__/fields/*",
      "indexes": [
        {
          "fields": [
            {
              "fieldPath": "expiresAt",
              "order": "ASCENDING"
            }
          ],
          "queryScope": "COLLECTION",
          "state": "READY"
        },
        {
          "fields": [
            {
              "fieldPath": "expiresAt",
              "order": "DESCENDING"
            }
          ],
          "queryScope": "COLLECTION",
          "state": "READY"
        },
        {
          "fields": [
            {
              "arrayConfig": "CONTAINS",
              "fieldPath": "expiresAt"
            }
          ],
          "queryScope": "COLLECTION",
          "state": "READY"
        }
      ],
      "usesAncestorConfig": true
    },
    "name": "projects/your-project-id/databases/(default)/collectionGroups/sessions/fields/expiresAt",
    "ttlConfig": {
      "state": "ACTIVE"
    }
  }
]
```

**Note**: TTL policies automatically create necessary indexes for the TTL field (ASCENDING, DESCENDING, and CONTAINS). The `ttlConfig.state` can be `ACTIVE` or `INACTIVE`.

## Project Structure

**Your workspace (after `firesync init`):**

```
your-project/
├── config.yaml                # Workspace configuration
├── firestore_schema/          # Schema directories (per environment)
│   ├── dev/
│   │   ├── composite-indexes.json
│   │   ├── field-indexes.json
│   │   └── ttl-policies.json
│   ├── staging/
│   │   └── ...
│   └── prod/
│       └── ...
└── secrets/                   # GCP service account keys (gitignored)
    ├── gcp-key-dev.json
    ├── gcp-key-staging.json
    └── gcp-key-prod.json
```

**Source code structure (for contributors):**

```
firesync/
├── src/firesync/              # Main Python package
│   ├── __init__.py
│   ├── __main__.py            # python -m firesync support
│   ├── main.py                # CLI entry point
│   ├── cli.py                 # CLI argument parsing
│   ├── config.py              # Configuration management
│   ├── gcloud.py              # GCloud CLI wrapper
│   ├── normalizers.py         # Data normalization
│   ├── operations.py          # Resource operations
│   ├── schema.py              # Schema file handling
│   ├── workspace.py           # Workspace configuration
│   └── commands/              # Command implementations
│       ├── __init__.py
│       ├── init.py
│       ├── env.py
│       ├── pull.py
│       ├── plan.py
│       └── apply.py
├── tests/                     # Unit tests
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_gcloud.py
│   ├── test_normalizers.py
│   ├── test_operations.py
│   ├── test_schema.py
│   └── test_workspace.py
├── pyproject.toml             # Package configuration
├── LICENSE
└── README.md
```

## CI/CD Integration

### GitHub Actions - Single Environment

```yaml
name: Deploy Firestore Schema

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install firesync
        run: pip install firestore-schema-migration

      - name: Install gcloud CLI
        uses: google-github-actions/setup-gcloud@v1

      - name: Create config.yaml
        run: |
          echo "version: 1" > config.yaml
          echo "schema_base_dir: firestore_schema" >> config.yaml
          echo "environments:" >> config.yaml
          echo "  prod:" >> config.yaml
          echo "    key_env: GCP_KEY" >> config.yaml
          echo "    schema_dir: prod" >> config.yaml

      - name: Plan schema changes
        env:
          GCP_KEY: ${{ secrets.GCP_SERVICE_ACCOUNT_KEY }}
        run: firesync plan --env=prod

      - name: Apply schema changes
        env:
          GCP_KEY: ${{ secrets.GCP_SERVICE_ACCOUNT_KEY }}
        run: firesync apply --env=prod
```

### GitHub Actions - Multi-Environment Pipeline

```yaml
name: Deploy to All Environments

on:
  push:
    branches: [main]

jobs:
  deploy-dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install firestore-schema-migration
      - uses: google-github-actions/setup-gcloud@v1

      - name: Deploy to dev
        env:
          GCP_DEV_KEY: ${{ secrets.GCP_DEV_KEY }}
        run: |
          firesync plan --env=dev
          firesync apply --env=dev

  deploy-staging:
    needs: deploy-dev
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install firestore-schema-migration
      - uses: google-github-actions/setup-gcloud@v1

      - name: Deploy to staging
        env:
          GCP_STAGING_KEY: ${{ secrets.GCP_STAGING_KEY }}
        run: |
          firesync plan --env=staging
          firesync apply --env=staging

  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install firestore-schema-migration
      - uses: google-github-actions/setup-gcloud@v1

      - name: Deploy to production
        env:
          GCP_PROD_KEY: ${{ secrets.GCP_PROD_KEY }}
        run: |
          firesync plan --env=prod
          firesync apply --env=prod
```

## Limitations

- **Delete operations**: Plan shows deletions but Apply doesn't implement them (safety feature)
- **Manual schema editing**: Schema files must be edited manually or pulled from existing Firestore
- **Single region**: Assumes single Firestore region per project

## Troubleshooting

### Authentication Issues

```bash
# Verify gcloud is installed
gcloud --version

# Check active account
gcloud auth list

# Re-authenticate if needed
gcloud auth login
```

### Permission Denied

Ensure your service account has these IAM roles:
- `roles/datastore.indexAdmin` or
- `roles/datastore.owner`

### Schema Files Not Found

```bash
# Pull schema first if firestore_schema/ is empty
firesync pull --env=dev
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see [LICENSE](https://github.com/PavelRavvich/firesync/blob/main/LICENSE) for details.

## Author

Pavel Ravvich

---

**Note**: Always test schema changes in development/staging environments before applying to production.
