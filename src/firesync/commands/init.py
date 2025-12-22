#!/usr/bin/env python3
"""Initialize FireSync workspace with config.yaml template."""

import logging
import sys
from pathlib import Path

from ..workspace import CONFIG_DIR_NAME, init_workspace

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Main entry point for firestore_init command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize FireSync workspace. Creates config.yaml for managing multiple environments."
    )
    parser.parse_args()

    try:
        config_path = init_workspace()
        print(f"\n[+] FireSync workspace initialized at: {config_path.parent}")
        print(f"\nNext steps:")
        print(f"1. Edit {config_path} to add your environments")
        print(f"2. Add service account keys to your project")
        print(f"3. Run 'firesync pull --env=<environment-name>' to export schemas")

    except FileExistsError as e:
        print(f"[!] {e}")
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"[!] Failed to initialize workspace: {e}")
        logger.exception("Workspace initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
