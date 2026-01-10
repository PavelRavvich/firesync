#!/usr/bin/env python3
"""FireSync CLI - Unified command-line interface."""

import argparse
import sys

from firesync import __version__


def create_parser():
    """Create an argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog='firesync',
        description='Infrastructure as Code for Google Cloud Firestore'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'firesync {__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize FireSync workspace')
    init_parser.add_argument('--path', help='Target directory for workspace (default: current directory)')

    # Env command (with sub-subcommands)
    subparsers.add_parser('env', help='Manage workspace environments')

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
        # Remove 'env' from argv and call env command directly
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from firesync.commands.env import main as env_main
        env_main()
        return

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'init':
        from firesync.commands.init import main as init_main
        init_main(getattr(args, 'path', None))

    elif args.command == 'pull':
        # Reconstruct args for pull command
        pull_args = [sys.argv[0]]
        if hasattr(args, 'all') and args.all:
            pull_args.append('--all')
        elif hasattr(args, 'env') and args.env:
            pull_args.extend(['--env', args.env])
        sys.argv = pull_args
        from firesync.commands.pull import main as pull_main
        pull_main()

    elif args.command == 'plan':
        # Reconstruct args for plan command
        plan_args = [sys.argv[0]]
        if hasattr(args, 'env_from') and args.env_from and hasattr(args, 'env_to') and args.env_to:
            plan_args.extend(['--env-from', args.env_from, '--env-to', args.env_to])
        elif hasattr(args, 'env') and args.env:
            plan_args.extend(['--env', args.env])
        if hasattr(args, 'schema_dir') and args.schema_dir:
            plan_args.extend(['--schema-dir', args.schema_dir])
        sys.argv = plan_args
        from firesync.commands.plan import main as plan_main
        plan_main()

    elif args.command == 'apply':
        # Reconstruct args for apply command
        apply_args = [sys.argv[0]]
        if hasattr(args, 'env_from') and args.env_from and hasattr(args, 'env_to') and args.env_to:
            apply_args.extend(['--env-from', args.env_from, '--env-to', args.env_to])
        elif hasattr(args, 'env') and args.env:
            apply_args.extend(['--env', args.env])
        if hasattr(args, 'schema_dir') and args.schema_dir:
            apply_args.extend(['--schema-dir', args.schema_dir])
        sys.argv = apply_args
        from firesync.commands.apply import main as apply_main
        apply_main()


if __name__ == '__main__':
    main()
