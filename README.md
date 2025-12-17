# FireSync

[![Tests](https://github.com/PavelRavvich/firesync/actions/workflows/test.yml/badge.svg)](https://github.com/PavelRavvich/firesync/actions/workflows/test.yml)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](https://github.com/PavelRavvich/firesync)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Infrastructure as Code for Google Cloud Firestore**

FireSync is a lightweight Python tool that brings version control and deployment automation to your Firestore database schema. Manage composite indexes, single-field indexes, and TTL policies using a familiar pull-plan-apply workflow inspired by Terraform.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Setup](#setup)
- [Usage](#usage)
  - [Pull Schema from Firestore](#pull-schema-from-firestore)
  - [Plan Changes](#plan-changes)
  - [Apply Changes](#apply-changes)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Custom Schema Directory](#custom-schema-directory)
- [Workflow Example](#workflow-example)
  - [Promoting Schema Changes: Dev → Staging → Production](#promoting-schema-changes-dev--staging--production)
  - [Syncing Schema from Production to Lower Environments](#syncing-schema-from-production-to-lower-environments)
- [Schema Files](#schema-files)
  - [composite-indexes.json](#composite-indexesjson)
  - [field-indexes.json](#field-indexesjson)
  - [ttl-policies.json](#ttl-policiesjson)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
  - [Authentication Issues](#authentication-issues)
  - [Permission Denied](#permission-denied)
  - [Schema Files Not Found](#schema-files-not-found)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

## Features

- 🔄 **Version Control** - Track Firestore schema changes in git
- 🌍 **Multi-Environment** - Separate configs for dev, staging, and production
- 🔍 **Plan Before Apply** - Preview changes before deploying
- 🛡️ **Safety First** - Idempotent operations, no accidental deletions
- 🐍 **Zero Dependencies** - Pure Python stdlib, just needs gcloud CLI
- 🪟 **Cross-Platform** - Works on Linux, macOS, and Windows

## Quick Start

### Prerequisites

- Python 3.7+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (gcloud CLI)
- GCP service account with Firestore permissions

### Installation

```bash
git clone https://github.com/yourusername/firesync.git
cd firesync
chmod +x firestore_*.py
```

### Setup

1. Create a GCP service account with Firestore permissions:
   - `datastore.indexes.list`
   - `datastore.indexes.create`
   - `datastore.indexes.update`
   - `firebase.projects.get`

2. Download the service account key and save it:
```bash
mkdir -p secrets/
mv ~/Downloads/your-key.json secrets/gcp-key-dev.json
```

3. Pull your current Firestore schema:
```bash
./firestore_pull.py --env=dev
```

This creates `firestore_schema/` with your current configuration.

## Usage

### Pull Schema from Firestore

Export current Firestore configuration to local JSON files:

```bash
./firestore_pull.py --env=dev
```

### Plan Changes

Compare local schema against remote Firestore and preview what would change:

```bash
./firestore_plan.py --env=staging
```

Output example:
```
🔍 Comparing Composite Indexes
[+] WILL CREATE: users COLLECTION email:ascending | createdAt:descending
[-] WILL DELETE: orders COLLECTION status:ascending

🔍 Comparing Single-Field Indexes
[+] WILL CREATE FIELD INDEX: ('products', 'price') => ascending

✔️ Plan complete.
```

### Apply Changes

Deploy local schema to Firestore:

```bash
./firestore_apply.py --env=staging
```

## Configuration

### Environment Variables

Instead of `--env` flag, you can use the `ENV` environment variable:

```bash
export ENV=dev
./firestore_pull.py
./firestore_plan.py
./firestore_apply.py
```

### Custom Schema Directory

```bash
./firestore_plan.py --env=dev --schema-dir=custom_schemas
./firestore_apply.py --env=dev --schema-dir=custom_schemas
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

```
firesync/
├── firestore_pull.py          # Export schema from Firestore
├── firestore_plan.py          # Compare local vs remote
├── firestore_apply.py         # Apply schema to Firestore
├── firestore_schema/          # Schema JSON files
│   ├── .gitkeep
│   ├── composite-indexes.json
│   ├── field-indexes.json
│   └── ttl-policies.json
├── secrets/                   # GCP service account keys (gitignored)
│   ├── .gitkeep
│   ├── gcp-key-dev.json
│   ├── gcp-key-staging.json
│   └── gcp-key-production.json
├── .gitignore
├── LICENSE
└── README.md
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
./firestore_pull.py --env=dev
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Pavel Ravvich

---

**Note**: Always test schema changes in development/staging environments before applying to production.
