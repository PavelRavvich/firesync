#!/usr/bin/env python3
"""FireSync CLI - Unified command-line interface."""

import argparse
import sys
import subprocess
from pathlib import Path


def create_parser():
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog='firesync',
        description='Infrastructure as Code for Google Cloud Firestore'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='firesync 0.1.0'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Pull command
    pull_parser = subparsers.add_parser('pull', help='Export Firestore schema to local files')
    pull_key_group = pull_parser.add_mutually_exclusive_group(required=True)
    pull_key_group.add_argument('--key-path', help='Path to GCP service account key file')
    pull_key_group.add_argument('--key-env', help='Environment variable with key JSON')

    # Plan command
    plan_parser = subparsers.add_parser('plan', help='Compare local vs remote schema')
    plan_key_group = plan_parser.add_mutually_exclusive_group(required=True)
    plan_key_group.add_argument('--key-path', help='Path to GCP service account key file')
    plan_key_group.add_argument('--key-env', help='Environment variable with key JSON')
    plan_parser.add_argument('--schema-dir', default='firestore_schema', help='Schema directory')

    # Apply command
    apply_parser = subparsers.add_parser('apply', help='Apply local schema to Firestore')
    apply_key_group = apply_parser.add_mutually_exclusive_group(required=True)
    apply_key_group.add_argument('--key-path', help='Path to GCP service account key file')
    apply_key_group.add_argument('--key-env', help='Environment variable with key JSON')
    apply_parser.add_argument('--schema-dir', default='firestore_schema', help='Schema directory')

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Find the project root (where firestore_*.py scripts are)
    # src/firesync_cli.py -> src/ -> root
    script_dir = Path(__file__).parent.parent

    # Build command
    cmd = ['python3']

    if args.command == 'pull':
        cmd.append(str(script_dir / 'firestore_pull.py'))
        if hasattr(args, 'key_path') and args.key_path:
            cmd.extend(['--key-path', args.key_path])
        if hasattr(args, 'key_env') and args.key_env:
            cmd.extend(['--key-env', args.key_env])

    elif args.command == 'plan':
        cmd.append(str(script_dir / 'firestore_plan.py'))
        if hasattr(args, 'key_path') and args.key_path:
            cmd.extend(['--key-path', args.key_path])
        if hasattr(args, 'key_env') and args.key_env:
            cmd.extend(['--key-env', args.key_env])
        if args.schema_dir:
            cmd.extend(['--schema-dir', args.schema_dir])

    elif args.command == 'apply':
        cmd.append(str(script_dir / 'firestore_apply.py'))
        if hasattr(args, 'key_path') and args.key_path:
            cmd.extend(['--key-path', args.key_path])
        if hasattr(args, 'key_env') and args.key_env:
            cmd.extend(['--key-env', args.key_env])
        if args.schema_dir:
            cmd.extend(['--schema-dir', args.schema_dir])

    # Execute the command
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
