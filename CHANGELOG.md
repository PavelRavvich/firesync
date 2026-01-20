# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2025-01-20

### Fixed
- Field index apply now correctly handles raw GCP format from `firesync pull`
- Added support for `indexConfig.indexes` nested structure
- System default entries (`__default__`, wildcard `*`) are now properly skipped
- `validate_field_index` now accepts both normalized and raw GCP formats

### Added
- New tests for raw GCP format handling in field indexes

## [0.1.2] - 2025-01-11

### Added
- `--path` option for `firesync init` command

## [0.1.1] - 2025-01-10

### Added
- Smart `key_env` auto-detection for JSON content vs file path

## [0.1.0] - 2024-12-17

### Added
- Initial release
- CLI commands: `firesync init`, `firesync pull`, `firesync plan`, `firesync apply`
- Support for composite indexes, field indexes, and TTL policies
- Multi-environment support (dev, staging, production)
- Workspace configuration with `firesync.yaml`
