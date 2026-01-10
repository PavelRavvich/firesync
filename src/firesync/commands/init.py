#!/usr/bin/env python3
"""Initialize FireSync workspace with config.yaml template."""

import sys
import logging
from typing import Optional
from pathlib import Path

from firesync.workspace import init_workspace, CONFIG_DIR_NAME

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main(target_path: Optional[str] = None):
    """Main entry point for firesync init command."""
    try:
        target_dir = Path(target_path) if target_path else None
        config_path = init_workspace(target_dir)
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
