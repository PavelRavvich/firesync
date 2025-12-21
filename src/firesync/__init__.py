"""
FireSync - Infrastructure as Code for Firestore

A Python tool for managing Firestore database schemas as code.
"""

__version__ = "0.1.0"
__author__ = "Pavel Ravvich"
__license__ = "MIT"

from .config import FiresyncConfig
from .gcloud import GCloudClient

__all__ = ["FiresyncConfig", "GCloudClient"]
