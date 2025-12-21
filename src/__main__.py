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


def main():
    """Main CLI entry point."""
    import os
    from pathlib import Path

    # Ensure PYTHONPATH includes src directory
    # Get the src directory (parent of this __main__.py file)
    src_dir = Path(__file__).parent.resolve()

    # Special handling for 'env' command - pass through directly
    if len(sys.argv) > 1 and sys.argv[1] == 'env':
        # Set up environment variables for global flags
        env = os.environ.copy()
        if '--verbose' in sys.argv or '-v' in sys.argv:
            env['FIRESYNC_VERBOSE'] = '1'
        if '--quiet' in sys.argv or '-q' in sys.argv:
            env['FIRESYNC_QUIET'] = '1'

        # Set PYTHONPATH to ONLY our src directory (replace, don't append)
        # This prevents conflicts with other projects' modules
        env['PYTHONPATH'] = str(src_dir)

        # Remove current directory from being added to sys.path
        # by unsetting PYTHONSAFEPATH (Python 3.11+) or using empty string for cwd
        env['PYTHONDONTWRITEBYTECODE'] = '1'

        # Remove global flags from argv before passing to subcommand
        filtered_args = [arg for arg in sys.argv[2:] if arg not in ('--verbose', '-v', '--quiet', '-q')]

        # Run the command from a neutral directory to avoid current dir in sys.path
        import tempfile
        cmd = ['python3', '-m', 'commands.env'] + filtered_args
        result = subprocess.run(cmd, env=env, cwd=str(src_dir.parent))
        sys.exit(result.returncode)

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Set up environment variables for global flags
    env = os.environ.copy()
    if args.verbose:
        env['FIRESYNC_VERBOSE'] = '1'
    if args.quiet:
        env['FIRESYNC_QUIET'] = '1'

    # Set PYTHONPATH to ONLY our src directory (replace, don't append)
    # This prevents conflicts with other projects' modules
    env['PYTHONPATH'] = str(src_dir)
    env['PYTHONDONTWRITEBYTECODE'] = '1'

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
        if hasattr(args, 'from_env') and args.from_env and hasattr(args, 'to_env') and args.to_env:
            cmd.extend(['--from', args.from_env, '--to', args.to_env])
        elif hasattr(args, 'env') and args.env:
            cmd.extend(['--env', args.env])
        if hasattr(args, 'schema_dir') and args.schema_dir:
            cmd.extend(['--schema-dir', args.schema_dir])

    elif args.command == 'apply':
        cmd.append('commands.apply')
        if hasattr(args, 'from_env') and args.from_env and hasattr(args, 'to_env') and args.to_env:
            cmd.extend(['--from', args.from_env, '--to', args.to_env])
        elif hasattr(args, 'env') and args.env:
            cmd.extend(['--env', args.env])
        if hasattr(args, 'schema_dir') and args.schema_dir:
            cmd.extend(['--schema-dir', args.schema_dir])
        if hasattr(args, 'auto_approve') and args.auto_approve:
            cmd.append('--auto-approve')
        if hasattr(args, 'dry_run') and args.dry_run:
            cmd.append('--dry-run')

    # Execute the command with environment variables
    # Run from project root directory to avoid current dir in sys.path
    result = subprocess.run(cmd, env=env, cwd=str(src_dir.parent))
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
