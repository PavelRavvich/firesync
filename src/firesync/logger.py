"""Logging configuration for FireSync CLI."""

import logging
import os
import sys


def setup_logging():
    """
    Configure logging based on environment variables.

    Reads FIRESYNC_VERBOSE and FIRESYNC_QUIET environment variables
    to set appropriate logging level.
    """
    # Determine logging level from environment
    verbose = os.environ.get("FIRESYNC_VERBOSE") == "1"
    quiet = os.environ.get("FIRESYNC_QUIET") == "1"

    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,  # Override any existing configuration
    )

    return logging.getLogger(__name__)
