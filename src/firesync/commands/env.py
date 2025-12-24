#!/usr/bin/env python3
"""Manage FireSync workspace environments."""

import sys
import logging
import argparse

from firesync.workspace import (
    load_config,
    add_environment,
    remove_environment,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_list(args):
    """List all environments."""
    try:
        config = load_config()

        if not config.environments:
            print("No environments configured.")
            print(f"\nRun 'firesync env add <name> --key-path=<path>' to add an environment.")
            return

        print(f"\nEnvironments in {config.config_path}:\n")
        for env_name, env_config in config.environments.items():
            desc = f" - {env_config.description}" if env_config.description else ""
            print(f"  * {env_name}")

            if env_config.key_path:
                # Show relative path and absolute path in parentheses
                abs_path = config.config_dir / env_config.key_path
                print(f"    key_path: {env_config.key_path}{desc} ({abs_path})")
            else:
                print(f"    key_env: {env_config.key_env}{desc}")

        print()

    except FileNotFoundError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"[!] Failed to list environments: {e}")
        logger.exception("Failed to list environments")
        sys.exit(1)


def cmd_show(args):
    """Show details of a specific environment."""
    try:
        config = load_config()
        env_config = config.get_env(args.name)

        print(f"\nEnvironment: {args.name}\n")

        if env_config.key_path:
            print(f"  Authentication: key_path")
            print(f"  Key file:       {env_config.key_path}")
            # Show absolute path
            abs_path = config.config_dir / env_config.key_path
            print(f"  Absolute path:  {abs_path}")
        else:
            print(f"  Authentication: key_env")
            print(f"  Environment variable: {env_config.key_env}")
            print(f"  (Auto-detects JSON content or file path)")

        if env_config.description:
            print(f"  Description:    {env_config.description}")

        # Show schema directory
        schema_dir = config.get_schema_dir(args.name)
        print(f"  Schema directory: {schema_dir}")
        print(f"  Schema exists:    {schema_dir.exists()}")

        print()

    except FileNotFoundError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except ValueError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"[!] Failed to show environment: {e}")
        logger.exception("Failed to show environment")
        sys.exit(1)


def cmd_add(args):
    """Add a new environment."""
    try:
        # Validation is handled by argparse mutually exclusive group

        add_environment(
            env_name=args.name,
            key_path=args.key_path,
            key_env=args.key_env,
            description=args.description
        )

        print(f"\n[+] Environment '{args.name}' added successfully")

        # Show what was added
        config = load_config()
        env_config = config.get_env(args.name)

        if env_config.key_path:
            print(f"   Key path: {env_config.key_path}")
        else:
            print(f"   Key env:  {env_config.key_env}")

        if env_config.description:
            print(f"   Description: {env_config.description}")

        print()

    except FileNotFoundError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except ValueError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"[!] Failed to add environment: {e}")
        logger.exception("Failed to add environment")
        sys.exit(1)


def cmd_remove(args):
    """Remove an environment."""
    try:
        # Confirm removal unless --force is used
        if not args.force:
            config = load_config()
            env_config = config.get_env(args.name)

            print(f"\nAre you sure you want to remove environment '{args.name}'?")
            if env_config.key_path:
                print(f"  Key path: {env_config.key_path}")
            else:
                print(f"  Key env:  {env_config.key_env}")

            response = input("\nType 'yes' to confirm: ")
            if response.lower() != 'yes':
                print("Cancelled.")
                return

        remove_environment(args.name)
        print(f"\n[+] Environment '{args.name}' removed successfully\n")

    except FileNotFoundError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except ValueError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"[!] Failed to remove environment: {e}")
        logger.exception("Failed to remove environment")
        sys.exit(1)


def main():
    """Main entry point for firesync env command."""
    parser = argparse.ArgumentParser(
        description='Manage FireSync workspace environments'
    )

    subparsers = parser.add_subparsers(dest='subcommand', help='Environment management commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List all environments')
    list_parser.set_defaults(func=cmd_list)

    # Show command
    show_parser = subparsers.add_parser('show', help='Show environment details')
    show_parser.add_argument('name', help='Environment name')
    show_parser.set_defaults(func=cmd_show)

    # Add command
    add_parser = subparsers.add_parser('add', help='Add new environment')
    add_parser.add_argument('name', help='Environment name')
    add_key_group = add_parser.add_mutually_exclusive_group(required=True)
    add_key_group.add_argument('--key-path', help='Path to GCP service account key file')
    add_key_group.add_argument('--key-env', help='Environment variable (auto-detects JSON content or file path)')
    add_parser.add_argument('--description', help='Environment description')
    add_parser.set_defaults(func=cmd_add)

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove environment')
    remove_parser.add_argument('name', help='Environment name')
    remove_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    remove_parser.set_defaults(func=cmd_remove)

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    # Call the appropriate command function
    args.func(args)


if __name__ == "__main__":
    main()
