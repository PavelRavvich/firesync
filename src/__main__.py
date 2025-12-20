#!/usr/bin/env python3
"""FireSync CLI - Unified command-line interface."""

import argparse
import sys
import subprocess


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
    subparsers.add_parser(
        'init',
        help='Initialize FireSync workspace',
        description='Initialize FireSync workspace. Creates config.yaml for managing multiple environments.'
    )

    # Env command (with sub-subcommands)
    subparsers.add_parser(
        'env',
        help='Manage workspace environments',
        description='Manage workspace environments. Add, remove, list, or show environment details.'
    )

    # Pull command
    pull_parser = subparsers.add_parser(
        'pull',
        help='Export Firestore schema to local files',
        description='Export Firestore schema from GCP to local JSON files'
    )
    pull_key_group = pull_parser.add_mutually_exclusive_group(required=True)
    pull_key_group.add_argument('--all', action='store_true', help='Export schemas from all environments defined in config.yaml')
    pull_key_group.add_argument('--env', metavar='NAME', help='Export schema from specific environment (e.g., dev, staging, prod)')

    # Plan command
    plan_parser = subparsers.add_parser(
        'plan',
        help='Compare local vs remote schema',
        description='Compare local Firestore schema against remote state or between environments'
    )
    plan_parser.add_argument('--env-from', metavar='SOURCE', help='Source environment (migration mode: compare SOURCE local schema)')
    plan_parser.add_argument('--env-to', metavar='TARGET', help='Target environment (migration mode: compare against TARGET local schema)')
    plan_parser.add_argument('--env', metavar='NAME', help='Compare local schema against remote Firestore (e.g., dev, staging, prod)')
    plan_parser.add_argument('--schema-dir', metavar='PATH', help='Custom schema directory path (overrides workspace config)')

    # Apply command
    apply_parser = subparsers.add_parser(
        'apply',
        help='Apply local schema to Firestore',
        description='Apply local Firestore schema to remote GCP project or migrate between environments'
    )
    apply_parser.add_argument('--env-from', metavar='SOURCE', help='Source environment (migration mode: read SOURCE local schema, apply to TARGET remote)')
    apply_parser.add_argument('--env-to', metavar='TARGET', help='Target environment (migration mode: apply SOURCE schema to TARGET Firestore)')
    apply_parser.add_argument('--env', metavar='NAME', help='Apply local schema to remote Firestore (e.g., dev, staging, prod)')
    apply_parser.add_argument('--schema-dir', metavar='PATH', help='Custom schema directory path (overrides workspace config)')

    return parser


def main():
    """Main CLI entry point."""
    # Special handling for 'env' command - pass through directly
    if len(sys.argv) > 1 and sys.argv[1] == 'env':
        cmd = ['python3', '-m', 'commands.env'] + sys.argv[2:]
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Build command
    cmd = ['python3', '-m']

    if args.command == 'init':
        cmd.append('commands.init')

    elif args.command == 'pull':
        cmd.append('commands.pull')
        if hasattr(args, 'all') and args.all:
            cmd.append('--all')
        elif hasattr(args, 'env') and args.env:
            cmd.extend(['--env', args.env])

    elif args.command == 'plan':
        cmd.append('commands.plan')
        if hasattr(args, 'env_from') and args.env_from and hasattr(args, 'env_to') and args.env_to:
            cmd.extend(['--env-from', args.env_from, '--env-to', args.env_to])
        elif hasattr(args, 'env') and args.env:
            cmd.extend(['--env', args.env])
        if hasattr(args, 'schema_dir') and args.schema_dir:
            cmd.extend(['--schema-dir', args.schema_dir])

    elif args.command == 'apply':
        cmd.append('commands.apply')
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
