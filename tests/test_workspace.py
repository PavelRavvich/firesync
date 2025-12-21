#!/usr/bin/env python3
"""Tests for core.workspace module."""

import sys
from pathlib import Path

import unittest
import tempfile
import shutil
from unittest.mock import patch, mock_open

from firesync.workspace import (
    EnvironmentConfig,
    WorkspaceConfig,
    find_config,
    load_config,
    init_workspace,
    CONFIG_DIR_NAME,
    CONFIG_FILE_NAME,
)


class TestEnvironmentConfig(unittest.TestCase):
    """Tests for EnvironmentConfig dataclass."""

    def test_valid_with_key_file(self):
        """Test creating environment config with key_file."""
        env = EnvironmentConfig(
            name="production",
            key_file="keys/prod.json",
            description="Production environment"
        )
        self.assertEqual(env.name, "production")
        self.assertEqual(env.key_file, "keys/prod.json")
        self.assertIsNone(env.key_env)
        self.assertEqual(env.description, "Production environment")

    def test_valid_with_key_env(self):
        """Test creating environment config with key_env."""
        env = EnvironmentConfig(
            name="staging",
            key_env="GCP_STAGING_KEY"
        )
        self.assertEqual(env.name, "staging")
        self.assertIsNone(env.key_file)
        self.assertEqual(env.key_env, "GCP_STAGING_KEY")

    def test_both_key_file_and_key_env_raises_error(self):
        """Test that specifying both key_file and key_env raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            EnvironmentConfig(
                name="invalid",
                key_file="keys/prod.json",
                key_env="GCP_KEY"
            )
        self.assertIn("cannot specify both", str(ctx.exception))
        self.assertIn("invalid", str(ctx.exception))

    def test_neither_key_file_nor_key_env_raises_error(self):
        """Test that omitting both key_file and key_env raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            EnvironmentConfig(name="invalid")
        self.assertIn("must specify either", str(ctx.exception))
        self.assertIn("invalid", str(ctx.exception))


class TestWorkspaceConfig(unittest.TestCase):
    """Tests for WorkspaceConfig dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        self.env1 = EnvironmentConfig(name="prod", key_file="keys/prod.json")
        self.env2 = EnvironmentConfig(name="staging", key_env="GCP_STAGING_KEY")
        self.config = WorkspaceConfig(
            version=1,
            environments={"prod": self.env1, "staging": self.env2},
            schema_dir="schemas",
            config_path=Path("/project/firestore-migration/config.yaml")
        )

    def test_config_dir_property(self):
        """Test that config_dir returns parent of config_path."""
        self.assertEqual(
            self.config.config_dir,
            Path("/project/firestore-migration")
        )

    def test_get_env_success(self):
        """Test getting existing environment."""
        env = self.config.get_env("prod")
        self.assertEqual(env, self.env1)

    def test_get_env_not_found(self):
        """Test getting non-existent environment raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.config.get_env("nonexistent")
        self.assertIn("Environment 'nonexistent' not found", str(ctx.exception))
        self.assertIn("prod, staging", str(ctx.exception))

    def test_get_schema_dir(self):
        """Test getting schema directory for environment."""
        schema_dir = self.config.get_schema_dir("prod")
        self.assertEqual(
            schema_dir,
            Path("/project/firestore-migration/schemas/prod")
        )


class TestFindConfig(unittest.TestCase):
    """Tests for find_config function."""

    def setUp(self):
        """Create temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

    def test_find_config_in_current_dir(self):
        """Test finding config in current directory."""
        # Create config in temp_dir
        config_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        config_dir.mkdir()
        config_path = config_dir / CONFIG_FILE_NAME
        config_path.touch()

        # Search from temp_dir
        found = find_config(Path(self.temp_dir))
        # Resolve both paths to handle symlinks (e.g., /var vs /private/var on macOS)
        self.assertEqual(found.resolve(), config_path.resolve())

    def test_find_config_in_parent_dir(self):
        """Test finding config in parent directory."""
        # Create config in temp_dir
        config_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        config_dir.mkdir()
        config_path = config_dir / CONFIG_FILE_NAME
        config_path.touch()

        # Create subdirectory
        subdir = Path(self.temp_dir) / "project" / "src"
        subdir.mkdir(parents=True)

        # Search from subdirectory
        found = find_config(subdir)
        # Resolve both paths to handle symlinks (e.g., /var vs /private/var on macOS)
        self.assertEqual(found.resolve(), config_path.resolve())

    def test_find_config_not_found(self):
        """Test that None is returned when config is not found."""
        # Search from temp_dir (no config created)
        found = find_config(Path(self.temp_dir))
        self.assertIsNone(found)

    def test_find_config_stops_at_root(self):
        """Test that search stops at filesystem root."""
        # This should not crash even if we search from root
        found = find_config(Path("/"))
        # Result depends on whether config exists on system, but should not crash
        self.assertIsInstance(found, (Path, type(None)))

    @patch('firesync.workspace.Path.cwd')
    def test_find_config_uses_cwd_by_default(self, mock_cwd):
        """Test that find_config uses current directory by default."""
        mock_cwd.return_value = Path(self.temp_dir)

        # Create config in temp_dir
        config_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        config_dir.mkdir()
        config_path = config_dir / CONFIG_FILE_NAME
        config_path.touch()

        # Call without arguments
        found = find_config()
        self.assertEqual(found, config_path)


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config function."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

        # Create workspace directory
        self.config_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        self.config_dir.mkdir()
        self.config_path = self.config_dir / CONFIG_FILE_NAME

    def write_config(self, content: str):
        """Helper to write config file."""
        with open(self.config_path, 'w') as f:
            f.write(content)

    def test_load_valid_config(self):
        """Test loading valid configuration."""
        self.write_config("""
version: 1
environments:
  production:
    key_file: keys/prod.json
    description: "Production environment"
  staging:
    key_env: GCP_STAGING_KEY
settings:
  schema_dir: schemas
""")
        config = load_config(self.config_path)

        self.assertEqual(config.version, 1)
        self.assertEqual(len(config.environments), 2)
        self.assertIn("production", config.environments)
        self.assertIn("staging", config.environments)
        self.assertEqual(config.schema_dir, "schemas")
        self.assertEqual(config.config_path, self.config_path)

        # Check production environment
        prod = config.environments["production"]
        self.assertEqual(prod.key_file, "keys/prod.json")
        self.assertIsNone(prod.key_env)
        self.assertEqual(prod.description, "Production environment")

        # Check staging environment
        staging = config.environments["staging"]
        self.assertIsNone(staging.key_file)
        self.assertEqual(staging.key_env, "GCP_STAGING_KEY")

    def test_load_config_minimal(self):
        """Test loading minimal valid configuration."""
        self.write_config("""
version: 1
environments:
  dev:
    key_file: dev.json
settings:
  schema_dir: my_schemas
""")
        config = load_config(self.config_path)

        self.assertEqual(config.version, 1)
        self.assertEqual(len(config.environments), 1)
        self.assertEqual(config.schema_dir, "my_schemas")

    def test_load_config_default_schema_dir(self):
        """Test that schema_dir defaults to 'schemas' if not specified."""
        self.write_config("""
version: 1
environments:
  dev:
    key_file: dev.json
settings: {}
""")
        config = load_config(self.config_path)
        self.assertEqual(config.schema_dir, "schemas")

    def test_load_config_missing_file(self):
        """Test that FileNotFoundError is raised when config doesn't exist."""
        non_existent = Path(self.temp_dir) / "nonexistent.yaml"
        with self.assertRaises(FileNotFoundError):
            load_config(non_existent)

    def test_load_config_invalid_yaml(self):
        """Test that ValueError is raised for invalid YAML."""
        self.write_config("invalid: yaml: content: [")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("Invalid YAML", str(ctx.exception))

    def test_load_config_not_dict(self):
        """Test that ValueError is raised if config is not a dictionary."""
        self.write_config("- list\n- of\n- items")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("must be a YAML dictionary", str(ctx.exception))

    def test_load_config_wrong_version(self):
        """Test that ValueError is raised for unsupported version."""
        self.write_config("""
version: 2
environments: {}
settings:
  schema_dir: schemas
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("Unsupported config version: 2", str(ctx.exception))

    def test_load_config_missing_version(self):
        """Test that ValueError is raised when version is missing."""
        self.write_config("""
environments: {}
settings:
  schema_dir: schemas
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("Unsupported config version: None", str(ctx.exception))

    def test_load_config_environments_not_dict(self):
        """Test that ValueError is raised if environments is not a dict."""
        self.write_config("""
version: 1
environments: []
settings:
  schema_dir: schemas
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("'environments' must be a dictionary", str(ctx.exception))

    def test_load_config_environment_not_dict(self):
        """Test that ValueError is raised if individual environment is not a dict."""
        self.write_config("""
version: 1
environments:
  prod: "string value"
settings:
  schema_dir: schemas
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("Environment 'prod' must be a dictionary", str(ctx.exception))

    def test_load_config_environment_both_keys(self):
        """Test that ValueError is raised if environment has both key_file and key_env."""
        self.write_config("""
version: 1
environments:
  prod:
    key_file: keys/prod.json
    key_env: GCP_PROD_KEY
settings:
  schema_dir: schemas
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("cannot specify both key_file and key_env", str(ctx.exception))

    def test_load_config_environment_no_keys(self):
        """Test that ValueError is raised if environment has neither key_file nor key_env."""
        self.write_config("""
version: 1
environments:
  prod:
    description: "No keys specified"
settings:
  schema_dir: schemas
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("must specify either key_file or key_env", str(ctx.exception))

    def test_load_config_settings_not_dict(self):
        """Test that ValueError is raised if settings is not a dict."""
        self.write_config("""
version: 1
environments:
  dev:
    key_file: dev.json
settings: "string value"
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("'settings' must be a dictionary", str(ctx.exception))

    def test_load_config_schema_dir_not_string(self):
        """Test that ValueError is raised if schema_dir is not a string."""
        self.write_config("""
version: 1
environments:
  dev:
    key_file: dev.json
settings:
  schema_dir: 123
""")
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("'settings.schema_dir' must be a string", str(ctx.exception))

    @patch('firesync.workspace.find_config')
    def test_load_config_searches_when_path_not_provided(self, mock_find):
        """Test that load_config searches for config when path is not provided."""
        mock_find.return_value = self.config_path

        self.write_config("""
version: 1
environments:
  dev:
    key_file: dev.json
settings:
  schema_dir: schemas
""")

        config = load_config()
        mock_find.assert_called_once()
        self.assertEqual(config.config_path, self.config_path)

    @patch('firesync.workspace.find_config')
    def test_load_config_not_found_when_searching(self, mock_find):
        """Test that FileNotFoundError is raised when config is not found during search."""
        mock_find.return_value = None

        with self.assertRaises(FileNotFoundError) as ctx:
            load_config()
        self.assertIn("Could not find", str(ctx.exception))
        self.assertIn("firesync init", str(ctx.exception))


class TestInitWorkspace(unittest.TestCase):
    """Tests for init_workspace function."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

    def test_init_workspace_success(self):
        """Test successful workspace initialization."""
        config_path = init_workspace(Path(self.temp_dir))

        # Check that directories were created
        workspace_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        self.assertTrue(workspace_dir.exists())
        self.assertTrue(workspace_dir.is_dir())

        schemas_dir = workspace_dir / "schemas"
        self.assertTrue(schemas_dir.exists())
        self.assertTrue(schemas_dir.is_dir())

        # Check that config.yaml was created
        expected_config_path = workspace_dir / CONFIG_FILE_NAME
        self.assertEqual(config_path, expected_config_path)
        self.assertTrue(config_path.exists())
        self.assertTrue(config_path.is_file())

        # Check config content
        with open(config_path, 'r') as f:
            content = f.read()

        self.assertIn("version: 1", content)
        self.assertIn("environments:", content)
        self.assertIn("settings:", content)
        self.assertIn("schema_dir: schemas", content)
        # Check that examples are commented
        self.assertIn("# production:", content)
        self.assertIn("# staging:", content)

    def test_init_workspace_already_exists(self):
        """Test that FileExistsError is raised if workspace already exists."""
        # Create workspace
        workspace_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        workspace_dir.mkdir()

        # Try to init again
        with self.assertRaises(FileExistsError) as ctx:
            init_workspace(Path(self.temp_dir))
        self.assertIn("already exists", str(ctx.exception))

    @patch('firesync.workspace.Path.cwd')
    def test_init_workspace_uses_cwd_by_default(self, mock_cwd):
        """Test that init_workspace uses current directory by default."""
        mock_cwd.return_value = Path(self.temp_dir)

        config_path = init_workspace()

        # Check that workspace was created in temp_dir
        expected_path = Path(self.temp_dir) / CONFIG_DIR_NAME / CONFIG_FILE_NAME
        self.assertEqual(config_path, expected_path)
        self.assertTrue(config_path.exists())

    def test_init_workspace_config_is_loadable(self):
        """Test that generated config can be loaded successfully."""
        config_path = init_workspace(Path(self.temp_dir))

        # Try to load the config (should not raise)
        # Note: This will fail because environments is empty, but we can check
        # that the YAML is valid
        import yaml
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        self.assertIsInstance(data, dict)
        self.assertEqual(data['version'], 1)
        self.assertIn('environments', data)
        self.assertIn('settings', data)


if __name__ == "__main__":
    unittest.main()
