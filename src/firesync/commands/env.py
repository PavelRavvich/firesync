#!/usr/bin/env python3
"""Manage FireSync workspace environments."""

import argparse
import sys
from pathlib import Path

from ..logger import setup_logging
from ..workspace import (
    add_environment,
    load_config,
    remove_environment,
)

# Configure logging based on environment variables
logger = setup_logging()


def cmd_list(args):
    """List all environments."""
    try:
        config = load_config()

        if not config.environments:
            print("No environments configured.")
            print(
                f"\nRun 'firesync env add <name> --key-file=<path>' to add an environment."
            )
            return

        print(f"\nEnvironments in {config.config_path}:\n")
        for env_name, env_config in config.environments.items():
            desc = f" - {env_config.description}" if env_config.description else ""
            print(f"  • {env_name}")

            if env_config.key_file:
                # Show relative path and absolute path in parentheses
                abs_path = config.config_dir / env_config.key_file
                print(f"    key_file: {env_config.key_file}{desc} ({abs_path})")
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

        if env_config.key_file:
            print(f"  Authentication: key_file")
            print(f"  Key file:       {env_config.key_file}")
            # Show absolute path
            abs_path = config.config_dir / env_config.key_file
            print(f"  Absolute path:  {abs_path}")
        else:
            print(f"  Authentication: key_env")
            print(f"  Environment variable: {env_config.key_env}")

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
        # Validate that exactly one of key_file or key_env is provided
        if args.key_file and args.key_env:
            print("[!] Cannot specify both --key-file and --key-env")
            sys.exit(1)
        if not args.key_file and not args.key_env:
            print("[!] Must specify either --key-file or --key-env")
            sys.exit(1)

        add_environment(
            env_name=args.name,
            key_file=args.key_file,
            key_env=args.key_env,
            description=args.description,
        )

        print(f"\n[+] Environment '{args.name}' added successfully")

        # Show what was added
        config = load_config()
        env_config = config.get_env(args.name)

        if env_config.key_file:
            print(f"   Key file: {env_config.key_file}")
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
            if env_config.key_file:
                print(f"  Key file: {env_config.key_file}")
            else:
                print(f"  Key env:  {env_config.key_env}")

            response = input("\nType 'yes' to confirm: ")
            if response.lower() != "yes":
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
    """Main entry point for firestore_env command."""
    parser = argparse.ArgumentParser(
        description="Manage FireSync workspace environments"
    )

    subparsers = parser.add_subparsers(
        dest="subcommand", help="Environment management commands"
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all configured environments",
        description="Display all environments from config.yaml with their credentials and descriptions",
    )
    list_parser.set_defaults(func=cmd_list)

    # Show command
    show_parser = subparsers.add_parser(
        "show",
        help="Show details of a specific environment",
        description="Display detailed information about an environment including credentials, schema directory, and status",
    )
    show_parser.add_argument("name", help="Environment name (e.g., dev, staging, prod)")
    show_parser.set_defaults(func=cmd_show)

    # Add command
    add_parser = subparsers.add_parser(
        "add",
        help="Add new environment to workspace",
        description="Add a new environment to config.yaml. Requires either --key-file or --key-env for GCP authentication.",
    )
    add_parser.add_argument("name", help="Environment name (e.g., dev, staging, prod)")
    add_key_group = add_parser.add_mutually_exclusive_group(required=True)
    add_key_group.add_argument(
        "--key-file",
        help="Path to GCP service account key file (relative to config.yaml)",
    )
    add_key_group.add_argument(
        "--key-env",
        help="Environment variable name containing GCP key JSON or path to key file",
    )
    add_parser.add_argument(
        "--description", help="Optional description of the environment"
    )
    add_parser.set_defaults(func=cmd_add)

    # Remove command
    remove_parser = subparsers.add_parser(
        "remove",
        help="Remove environment from workspace",
        description="Remove an environment from config.yaml. Requires confirmation unless --force is used.",
    )
    remove_parser.add_argument("name", help="Environment name to remove")
    remove_parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompt"
    )
    remove_parser.set_defaults(func=cmd_remove)

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    # Call the appropriate command function
    args.func(args)


if __name__ == "__main__":
    main()
