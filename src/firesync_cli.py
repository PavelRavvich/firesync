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

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize FireSync workspace')

    # Env command (with sub-subcommands)
    env_parser = subparsers.add_parser('env', help='Manage workspace environments')

    # Pull command
    pull_parser = subparsers.add_parser('pull', help='Export Firestore schema to local files')
    pull_key_group = pull_parser.add_mutually_exclusive_group(required=True)
    pull_key_group.add_argument('--all', action='store_true', help='Pull all environments from workspace')
    pull_key_group.add_argument('--env', help='Environment name from workspace config')

    # Plan command
    plan_parser = subparsers.add_parser('plan', help='Compare local vs remote schema')
    plan_parser.add_argument('--env-from', help='Source environment (migration mode)')
    plan_parser.add_argument('--env-to', help='Target environment (migration mode)')
    plan_parser.add_argument('--env', help='Environment name from workspace config')
    plan_parser.add_argument('--schema-dir', help='Schema directory (overrides workspace config)')

    # Apply command
    apply_parser = subparsers.add_parser('apply', help='Apply local schema to Firestore')
    apply_parser.add_argument('--env-from', help='Source environment (migration mode)')
    apply_parser.add_argument('--env-to', help='Target environment (migration mode)')
    apply_parser.add_argument('--env', help='Environment name from workspace config')
    apply_parser.add_argument('--schema-dir', help='Schema directory (overrides workspace config)')

    return parser


def main():
    """Main CLI entry point."""
    # Special handling for 'env' command - pass through directly
    if len(sys.argv) > 1 and sys.argv[1] == 'env':
        script_dir = Path(__file__).parent.parent
        cmd = ['python3', str(script_dir / 'firestore_env.py')] + sys.argv[2:]
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

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

    if args.command == 'init':
        cmd.append(str(script_dir / 'firestore_init.py'))

    elif args.command == 'pull':
        cmd.append(str(script_dir / 'firestore_pull.py'))
        if hasattr(args, 'all') and args.all:
            cmd.append('--all')
        elif hasattr(args, 'env') and args.env:
            cmd.extend(['--env', args.env])

    elif args.command == 'plan':
        cmd.append(str(script_dir / 'firestore_plan.py'))
        if hasattr(args, 'env_from') and args.env_from and hasattr(args, 'env_to') and args.env_to:
            cmd.extend(['--env-from', args.env_from, '--env-to', args.env_to])
        elif hasattr(args, 'env') and args.env:
            cmd.extend(['--env', args.env])
        if hasattr(args, 'schema_dir') and args.schema_dir:
            cmd.extend(['--schema-dir', args.schema_dir])

    elif args.command == 'apply':
        cmd.append(str(script_dir / 'firestore_apply.py'))
        if hasattr(args, 'env_from') and args.env_from and hasattr(args, 'env_to') and args.env_to:
            cmd.extend(['--env-from', args.env_from, '--env-to', args.env_to])
        elif hasattr(args, 'env') and args.env:
            cmd.extend(['--env', args.env])
        if hasattr(args, 'schema_dir') and args.schema_dir:
            cmd.extend(['--schema-dir', args.schema_dir])

    # Execute the command
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
