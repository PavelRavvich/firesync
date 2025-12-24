#!/usr/bin/env python3
"""Workspace configuration management for FireSync."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml
except ImportError:
    raise ImportError(
        "PyYAML is required for workspace management. "
        "Install it with: pip install PyYAML"
    )


CONFIG_DIR_NAME = "firestore-migration"
CONFIG_FILE_NAME = "config.yaml"


@dataclass
class EnvironmentConfig:
    """Configuration for a single environment."""
    name: str
    key_path: Optional[str] = None
    key_env: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        """Validate that exactly one of key_path or key_env is set."""
        if self.key_path and self.key_env:
            raise ValueError(
                f"Environment '{self.name}': cannot specify both key_path and key_env"
            )
        if not self.key_path and not self.key_env:
            raise ValueError(
                f"Environment '{self.name}': must specify either key_path or key_env"
            )


@dataclass
class WorkspaceConfig:
    """FireSync workspace configuration loaded from config.yaml."""
    version: int
    environments: Dict[str, EnvironmentConfig]
    schema_dir: str
    config_path: Path

    @property
    def config_dir(self) -> Path:
        """Get the directory containing config.yaml."""
        return self.config_path.parent

    def get_env(self, env_name: str) -> EnvironmentConfig:
        """
        Get environment configuration by name.

        Args:
            env_name: Name of the environment

        Returns:
            EnvironmentConfig for the requested environment

        Raises:
            ValueError: If environment doesn't exist
        """
        if env_name not in self.environments:
            raise ValueError(
                f"Environment '{env_name}' not found in config. "
                f"Available: {', '.join(self.environments.keys())}"
            )
        return self.environments[env_name]

    def get_schema_dir(self, env_name: str) -> Path:
        """
        Get the schema directory for a specific environment.

        Args:
            env_name: Name of the environment

        Returns:
            Absolute path to the schema directory for this environment
        """
        # schema_dir is relative to config.yaml location
        base_schema_dir = self.config_dir / self.schema_dir
        return base_schema_dir / env_name


def find_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Search for config.yaml by walking up the directory tree.

    Similar to how git searches for .git directory, this function
    searches upward from the current directory (or start_dir) for
    firestore-migration/config.yaml.

    Args:
        start_dir: Directory to start searching from (default: current directory)

    Returns:
        Path to config.yaml if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir).resolve()

    current = start_dir
    while True:
        config_path = current / CONFIG_DIR_NAME / CONFIG_FILE_NAME
        if config_path.exists():
            return config_path

        # Stop at filesystem root
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_config(config_path: Optional[Path] = None) -> WorkspaceConfig:
    """
    Load and validate workspace configuration from config.yaml.

    Args:
        config_path: Path to config.yaml (default: search upward from cwd)

    Returns:
        Validated WorkspaceConfig object

    Raises:
        FileNotFoundError: If config.yaml is not found
        ValueError: If config.yaml is invalid
    """
    # Find config if not provided
    if config_path is None:
        config_path = find_config()
        if config_path is None:
            raise FileNotFoundError(
                f"Could not find {CONFIG_DIR_NAME}/{CONFIG_FILE_NAME}. "
                f"Run 'firesync init' to create workspace configuration."
            )
    else:
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

    # Parse YAML
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")

    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML dictionary, got {type(data).__name__}")

    # Validate version
    version = data.get('version')
    if version != 1:
        raise ValueError(f"Unsupported config version: {version}. Expected version 1.")

    # Validate environments
    environments_data = data.get('environments')
    if environments_data is None:
        environments_data = {}
    if not isinstance(environments_data, dict):
        raise ValueError(
            f"'environments' must be a dictionary, got {type(environments_data).__name__}"
        )

    environments = {}
    for env_name, env_data in environments_data.items():
        if not isinstance(env_data, dict):
            raise ValueError(
                f"Environment '{env_name}' must be a dictionary, "
                f"got {type(env_data).__name__}"
            )

        env_config = EnvironmentConfig(
            name=env_name,
            key_path=env_data.get('key_path'),
            key_env=env_data.get('key_env'),
            description=env_data.get('description')
        )
        environments[env_name] = env_config

    # Validate settings
    settings = data.get('settings', {})
    if not isinstance(settings, dict):
        raise ValueError(f"'settings' must be a dictionary, got {type(settings).__name__}")

    schema_dir = settings.get('schema_dir', 'schemas')
    if not isinstance(schema_dir, str):
        raise ValueError(
            f"'settings.schema_dir' must be a string, got {type(schema_dir).__name__}"
        )

    return WorkspaceConfig(
        version=version,
        environments=environments,
        schema_dir=schema_dir,
        config_path=config_path
    )


def init_workspace(target_dir: Optional[Path] = None) -> Path:
    """
    Initialize a new FireSync workspace.

    Creates:
    - firestore-migration/ directory
    - firestore-migration/config.yaml with template
    - firestore-migration/schemas/ directory

    Args:
        target_dir: Directory to create workspace in (default: current directory)

    Returns:
        Path to created config.yaml

    Raises:
        FileExistsError: If workspace already exists
    """
    if target_dir is None:
        target_dir = Path.cwd()
    else:
        target_dir = Path(target_dir)

    workspace_dir = target_dir / CONFIG_DIR_NAME
    config_path = workspace_dir / CONFIG_FILE_NAME
    schemas_dir = workspace_dir / "schemas"

    # Check if workspace already exists
    if workspace_dir.exists():
        raise FileExistsError(
            f"Workspace already exists at {workspace_dir}. "
            f"Remove it first if you want to reinitialize."
        )

    # Create directories
    workspace_dir.mkdir(parents=True, exist_ok=False)
    schemas_dir.mkdir(exist_ok=False)

    # Create config.yaml with template
    config_template = """version: 1
environments:
  # Example configurations:
  # production:
  #   key_path: ../keys/prod.json        # Direct path to key file
  #   description: "Production environment"
  # staging:
  #   key_env: GCP_STAGING_KEY           # Env var (JSON content OR path to file)
  #   description: "Staging environment"
settings:
  schema_dir: schemas
"""

    with open(config_path, 'w') as f:
        f.write(config_template)

    return config_path


def save_config(config: WorkspaceConfig) -> None:
    """
    Save workspace configuration to config.yaml.

    Args:
        config: WorkspaceConfig object to save

    Raises:
        IOError: If config file cannot be written
    """
    # Build config dictionary
    data = {
        'version': config.version,
        'environments': {},
        'settings': {
            'schema_dir': config.schema_dir
        }
    }

    # Add environments
    for env_name, env_config in config.environments.items():
        env_data = {}
        if env_config.key_path:
            env_data['key_path'] = env_config.key_path
        if env_config.key_env:
            env_data['key_env'] = env_config.key_env
        if env_config.description:
            env_data['description'] = env_config.description
        data['environments'][env_name] = env_data

    # Write to file
    with open(config.config_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def add_environment(
    env_name: str,
    key_path: Optional[str] = None,
    key_env: Optional[str] = None,
    description: Optional[str] = None,
    config_path: Optional[Path] = None
) -> None:
    """
    Add a new environment to workspace configuration.

    Args:
        env_name: Name of the environment
        key_path: Path to GCP service account key file (relative to cwd)
        key_env: Environment variable name (auto-detects JSON content or file path)
        description: Optional description of the environment
        config_path: Path to config.yaml (default: search from cwd)

    Raises:
        FileNotFoundError: If config.yaml not found
        ValueError: If environment already exists or invalid parameters
    """
    # Load existing config
    config = load_config(config_path)

    # Check if environment already exists
    if env_name in config.environments:
        raise ValueError(f"Environment '{env_name}' already exists")

    # Convert key_path to relative path from config.yaml location
    if key_path:
        key_path_abs = (Path.cwd() / key_path).resolve()
        config_dir_abs = config.config_dir.resolve()
        try:
            # Calculate relative path from config.yaml to key file
            key_path_relative = os.path.relpath(key_path_abs, config_dir_abs)
        except ValueError:
            # On Windows, relpath fails if paths are on different drives
            key_path_relative = str(key_path_abs)
    else:
        key_path_relative = None

    # Create new environment config
    new_env = EnvironmentConfig(
        name=env_name,
        key_path=key_path_relative,
        key_env=key_env,
        description=description
    )

    # Add to config
    config.environments[env_name] = new_env

    # Save config
    save_config(config)


def remove_environment(env_name: str, config_path: Optional[Path] = None) -> None:
    """
    Remove an environment from workspace configuration.

    Args:
        env_name: Name of the environment to remove
        config_path: Path to config.yaml (default: search from cwd)

    Raises:
        FileNotFoundError: If config.yaml not found
        ValueError: If environment doesn't exist
    """
    # Load existing config
    config = load_config(config_path)

    # Check if environment exists
    if env_name not in config.environments:
        raise ValueError(
            f"Environment '{env_name}' not found. "
            f"Available: {', '.join(config.environments.keys())}"
        )

    # Remove environment
    del config.environments[env_name]

    # Save config
    save_config(config)
