"""
FireSync - Infrastructure as Code for Firestore

A Python tool for managing Firestore database schemas as code.
"""

__version__ = "0.1.3"
__author__ = "Pavel Ravvich"
__license__ = "MIT"

from firesync.config import FiresyncConfig
from firesync.gcloud import GCloudClient

__all__ = ["FiresyncConfig", "GCloudClient", "__version__"]
