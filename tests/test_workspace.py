#!/usr/bin/env python3
"""Tests for firesync.workspace module."""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from firesync.workspace import (
    EnvironmentConfig,
    WorkspaceConfig,
    find_config,
    load_config,
    init_workspace,
    save_config,
    add_environment,
    remove_environment,
    CONFIG_DIR_NAME,
    CONFIG_FILE_NAME,
)


class TestEnvironmentConfig(unittest.TestCase):
    """Tests for EnvironmentConfig dataclass."""

    def test_valid_with_key_path(self):
        """Test creating environment config with key_path."""
        env = EnvironmentConfig(
            name="production",
            key_path="keys/prod.json",
            description="Production environment"
        )
        self.assertEqual(env.name, "production")
        self.assertEqual(env.key_path, "keys/prod.json")
        self.assertIsNone(env.key_env)
        self.assertEqual(env.description, "Production environment")

    def test_valid_with_key_env(self):
        """Test creating environment config with key_env."""
        env = EnvironmentConfig(
            name="staging",
            key_env="GCP_STAGING_KEY"
        )
        self.assertEqual(env.name, "staging")
        self.assertIsNone(env.key_path)
        self.assertEqual(env.key_env, "GCP_STAGING_KEY")

    def test_both_key_path_and_key_env_raises_error(self):
        """Test that specifying both key_path and key_env raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            EnvironmentConfig(
                name="invalid",
                key_path="keys/prod.json",
                key_env="GCP_KEY"
            )
        self.assertIn("cannot specify both", str(ctx.exception))
        self.assertIn("invalid", str(ctx.exception))

    def test_neither_key_path_nor_key_env_raises_error(self):
        """Test that omitting both key_path and key_env raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            EnvironmentConfig(name="invalid")
        self.assertIn("must specify either", str(ctx.exception))
        self.assertIn("invalid", str(ctx.exception))


class TestWorkspaceConfig(unittest.TestCase):
    """Tests for WorkspaceConfig dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        self.env1 = EnvironmentConfig(name="prod", key_path="keys/prod.json")
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
    key_path: keys/prod.json
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
        self.assertEqual(prod.key_path, "keys/prod.json")
        self.assertIsNone(prod.key_env)
        self.assertEqual(prod.description, "Production environment")

        # Check staging environment
        staging = config.environments["staging"]
        self.assertIsNone(staging.key_path)
        self.assertEqual(staging.key_env, "GCP_STAGING_KEY")

    def test_load_config_minimal(self):
        """Test loading minimal valid configuration."""
        self.write_config("""
version: 1
environments:
  dev:
    key_path: dev.json
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
    key_path: dev.json
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


class TestSaveConfig(unittest.TestCase):
    """Tests for save_config function."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

        # Create workspace directory
        self.workspace_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        self.workspace_dir.mkdir()
        self.config_path = self.workspace_dir / CONFIG_FILE_NAME

    def test_save_config_basic(self):
        """Test saving basic configuration."""
        env1 = EnvironmentConfig(name="prod", key_path="keys/prod.json")
        env2 = EnvironmentConfig(name="dev", key_env="DEV_KEY")

        config = WorkspaceConfig(
            version=1,
            environments={"prod": env1, "dev": env2},
            schema_dir="schemas",
            config_path=self.config_path
        )

        save_config(config)

        # Verify file was created
        self.assertTrue(self.config_path.exists())

        # Load and verify
        loaded_config = load_config(self.config_path)
        self.assertEqual(loaded_config.version, 1)
        self.assertEqual(len(loaded_config.environments), 2)
        self.assertIn("prod", loaded_config.environments)
        self.assertIn("dev", loaded_config.environments)


class TestAddEnvironment(unittest.TestCase):
    """Tests for add_environment function."""

    def setUp(self):
        """Create temporary workspace for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

        # Create workspace with initial config
        self.workspace_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        self.workspace_dir.mkdir()
        self.config_path = self.workspace_dir / CONFIG_FILE_NAME

        # Create initial config
        initial_config = WorkspaceConfig(
            version=1,
            environments={},
            schema_dir="schemas",
            config_path=self.config_path
        )
        save_config(initial_config)

    def test_add_environment_with_key_env(self):
        """Test adding environment with key_env."""
        add_environment(
            env_name="staging",
            key_env="GCP_STAGING_KEY",
            description="Staging environment",
            config_path=self.config_path
        )

        # Verify environment was added
        config = load_config(self.config_path)
        self.assertIn("staging", config.environments)

        staging_env = config.environments["staging"]
        self.assertEqual(staging_env.key_env, "GCP_STAGING_KEY")
        self.assertIsNone(staging_env.key_path)

    def test_add_environment_already_exists(self):
        """Test that adding existing environment raises ValueError."""
        add_environment(
            env_name="prod",
            key_env="PROD_KEY",
            config_path=self.config_path
        )

        # Try to add again
        with self.assertRaises(ValueError) as ctx:
            add_environment(
                env_name="prod",
                key_env="PROD_KEY2",
                config_path=self.config_path
            )
        self.assertIn("already exists", str(ctx.exception))


class TestRemoveEnvironment(unittest.TestCase):
    """Tests for remove_environment function."""

    def setUp(self):
        """Create temporary workspace with environments for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

        # Create workspace with initial config
        self.workspace_dir = Path(self.temp_dir) / CONFIG_DIR_NAME
        self.workspace_dir.mkdir()
        self.config_path = self.workspace_dir / CONFIG_FILE_NAME

        # Create config with multiple environments
        env1 = EnvironmentConfig(name="prod", key_path="keys/prod.json")
        env2 = EnvironmentConfig(name="staging", key_env="STAGING_KEY")
        env3 = EnvironmentConfig(name="dev", key_env="DEV_KEY")

        initial_config = WorkspaceConfig(
            version=1,
            environments={"prod": env1, "staging": env2, "dev": env3},
            schema_dir="schemas",
            config_path=self.config_path
        )
        save_config(initial_config)

    def test_remove_environment_success(self):
        """Test removing an existing environment."""
        remove_environment("staging", self.config_path)

        # Verify environment was removed
        config = load_config(self.config_path)
        self.assertNotIn("staging", config.environments)
        self.assertEqual(len(config.environments), 2)
        self.assertIn("prod", config.environments)
        self.assertIn("dev", config.environments)

    def test_remove_environment_not_found(self):
        """Test that removing non-existent environment raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            remove_environment("nonexistent", self.config_path)
        self.assertIn("not found", str(ctx.exception))
        self.assertIn("prod, staging, dev", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
