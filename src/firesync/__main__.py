#!/usr/bin/env python3
"""FireSync CLI - Unified command-line interface."""

import argparse
import sys
import os


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

    # Global flags
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output (show debug logs and gcloud commands)'
    )

    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='Minimize output (show only errors and final results)'
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
    pull_key_group.add_argument('--all', '-a', action='store_true', help='Export schemas from all environments defined in config.yaml')
    pull_key_group.add_argument('--env', '-e', metavar='NAME', help='Export schema from specific environment (e.g., dev, staging, prod)')

    # Plan command
    plan_parser = subparsers.add_parser(
        'plan',
        help='Compare local vs remote schema',
        description='Compare local Firestore schema against remote state or between environments'
    )
    plan_parser.add_argument('--from', metavar='SOURCE', dest='from_env', help='Source environment (migration mode: compare SOURCE local schema)')
    plan_parser.add_argument('--to', metavar='TARGET', dest='to_env', help='Target environment (migration mode: compare against TARGET local schema)')
    plan_parser.add_argument('--env', '-e', metavar='NAME', help='Compare local schema against remote Firestore (e.g., dev, staging, prod)')
    plan_parser.add_argument('--schema-dir', '-d', metavar='PATH', help='Custom schema directory path (overrides workspace config)')

    # Apply command
    apply_parser = subparsers.add_parser(
        'apply',
        help='Apply local schema to Firestore',
        description='Apply local Firestore schema to remote GCP project or migrate between environments'
    )
    apply_parser.add_argument('--from', metavar='SOURCE', dest='from_env', help='Source environment (migration mode: read SOURCE local schema, apply to TARGET remote)')
    apply_parser.add_argument('--to', metavar='TARGET', dest='to_env', help='Target environment (migration mode: apply SOURCE schema to TARGET Firestore)')
    apply_parser.add_argument('--env', '-e', metavar='NAME', help='Apply local schema to remote Firestore (e.g., dev, staging, prod)')
    apply_parser.add_argument('--schema-dir', '-d', metavar='PATH', help='Custom schema directory path (overrides workspace config)')
    apply_parser.add_argument('--auto-approve', '-y', action='store_true', help='Skip confirmation prompt (useful for CI/CD)')
    apply_parser.add_argument('--dry-run', action='store_true', help='Show gcloud commands that would be executed without running them')

    return parser


def run_init():
    """Run init command."""
    original_argv = sys.argv
    try:
        sys.argv = ['firesync-init']
        from firesync.commands.init import main as init_main
        init_main()
    finally:
        sys.argv = original_argv


def run_env(argv):
    """Run env command."""
    # Save original argv
    original_argv = sys.argv
    try:
        # Set argv for env command (remove 'env' subcommand)
        sys.argv = [sys.argv[0]] + argv
        from firesync.commands.env import main as env_main
        env_main()
    finally:
        # Restore original argv
        sys.argv = original_argv


def run_pull(args):
    """Run pull command."""
    # Save original argv
    original_argv = sys.argv
    try:
        # Build argv for pull command
        sys.argv = ['firesync-pull']
        if args.all:
            sys.argv.append('--all')
        elif args.env:
            sys.argv.extend(['--env', args.env])

        from firesync.commands.pull import main as pull_main
        pull_main()
    finally:
        sys.argv = original_argv


def run_plan(args):
    """Run plan command."""
    original_argv = sys.argv
    try:
        sys.argv = ['firesync-plan']
        if args.from_env and args.to_env:
            sys.argv.extend(['--from', args.from_env, '--to', args.to_env])
        elif args.env:
            sys.argv.extend(['--env', args.env])
        if args.schema_dir:
            sys.argv.extend(['--schema-dir', args.schema_dir])

        from firesync.commands.plan import main as plan_main
        plan_main()
    finally:
        sys.argv = original_argv


def run_apply(args):
    """Run apply command."""
    original_argv = sys.argv
    try:
        sys.argv = ['firesync-apply']
        if args.from_env and args.to_env:
            sys.argv.extend(['--from', args.from_env, '--to', args.to_env])
        elif args.env:
            sys.argv.extend(['--env', args.env])
        if args.schema_dir:
            sys.argv.extend(['--schema-dir', args.schema_dir])
        if args.auto_approve:
            sys.argv.append('--auto-approve')
        if args.dry_run:
            sys.argv.append('--dry-run')

        from firesync.commands.apply import main as apply_main
        apply_main()
    finally:
        sys.argv = original_argv


def main():
    """Main CLI entry point."""
    # Set up environment variables for global flags before parsing
    if '--verbose' in sys.argv or '-v' in sys.argv:
        os.environ['FIRESYNC_VERBOSE'] = '1'
    if '--quiet' in sys.argv or '-q' in sys.argv:
        os.environ['FIRESYNC_QUIET'] = '1'

    parser = create_parser()

    # Special handling for 'env' command - it has sub-subcommands
    if len(sys.argv) > 1 and sys.argv[1] == 'env':
        # Remove global flags and pass the rest to env command
        env_args = [arg for arg in sys.argv[2:] if arg not in ('--verbose', '-v', '--quiet', '-q')]
        run_env(env_args)
        return

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate command handler
    if args.command == 'init':
        run_init()
    elif args.command == 'pull':
        run_pull(args)
    elif args.command == 'plan':
        run_plan(args)
    elif args.command == 'apply':
        run_apply(args)


if __name__ == '__main__':
    main()
