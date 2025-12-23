#!/usr/bin/env python3
"""Tests for environment management functions."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from firesync.workspace import (CONFIG_DIR_NAME, CONFIG_FILE_NAME,
                                EnvironmentConfig, WorkspaceConfig,
                                add_environment, load_config,
                                remove_environment, save_config)


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
        env1 = EnvironmentConfig(name="prod", key_file="keys/prod.json")
        env2 = EnvironmentConfig(name="dev", key_env="DEV_KEY")

        config = WorkspaceConfig(
            version=1,
            environments={"prod": env1, "dev": env2},
            schema_dir="schemas",
            config_path=self.config_path,
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

    def test_save_config_with_description(self):
        """Test saving configuration with descriptions."""
        env1 = EnvironmentConfig(
            name="prod", key_file="keys/prod.json", description="Production environment"
        )

        config = WorkspaceConfig(
            version=1,
            environments={"prod": env1},
            schema_dir="schemas",
            config_path=self.config_path,
        )

        save_config(config)

        # Load and verify
        loaded_config = load_config(self.config_path)
        prod_env = loaded_config.environments["prod"]
        self.assertEqual(prod_env.description, "Production environment")


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
            config_path=self.config_path,
        )
        save_config(initial_config)

        # Create a keys directory for testing relative paths
        self.keys_dir = Path(self.temp_dir) / "keys"
        self.keys_dir.mkdir()

    def test_add_environment_with_key_file(self):
        """Test adding environment with key_file."""
        # Change to temp_dir so relative paths work
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        try:
            add_environment(
                env_name="production",
                key_file="keys/prod.json",
                description="Production environment",
                config_path=self.config_path,
            )

            # Verify environment was added
            config = load_config(self.config_path)
            self.assertIn("production", config.environments)

            prod_env = config.environments["production"]
            self.assertEqual(prod_env.name, "production")
            # Path should be relative to config.yaml (normalize for cross-platform)
            self.assertEqual(Path(prod_env.key_file), Path("../keys/prod.json"))
            self.assertEqual(prod_env.description, "Production environment")
        finally:
            os.chdir(original_cwd)

    def test_add_environment_with_key_env(self):
        """Test adding environment with key_env."""
        add_environment(
            env_name="staging",
            key_env="GCP_STAGING_KEY",
            description="Staging environment",
            config_path=self.config_path,
        )

        # Verify environment was added
        config = load_config(self.config_path)
        self.assertIn("staging", config.environments)

        staging_env = config.environments["staging"]
        self.assertEqual(staging_env.key_env, "GCP_STAGING_KEY")
        self.assertIsNone(staging_env.key_file)

    def test_add_environment_without_description(self):
        """Test adding environment without description."""
        add_environment(env_name="dev", key_env="DEV_KEY", config_path=self.config_path)

        config = load_config(self.config_path)
        dev_env = config.environments["dev"]
        self.assertIsNone(dev_env.description)

    def test_add_environment_already_exists(self):
        """Test that adding existing environment raises ValueError."""
        add_environment(
            env_name="prod", key_file="keys/prod.json", config_path=self.config_path
        )

        # Try to add again
        with self.assertRaises(ValueError) as ctx:
            add_environment(
                env_name="prod",
                key_file="keys/prod2.json",
                config_path=self.config_path,
            )
        self.assertIn("already exists", str(ctx.exception))

    def test_add_environment_config_not_found(self):
        """Test that FileNotFoundError is raised when config doesn't exist."""
        non_existent = Path(self.temp_dir) / "nonexistent" / CONFIG_FILE_NAME
        with self.assertRaises(FileNotFoundError):
            add_environment(
                env_name="test", key_file="test.json", config_path=non_existent
            )


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
        env1 = EnvironmentConfig(name="prod", key_file="keys/prod.json")
        env2 = EnvironmentConfig(name="staging", key_env="STAGING_KEY")
        env3 = EnvironmentConfig(name="dev", key_env="DEV_KEY")

        initial_config = WorkspaceConfig(
            version=1,
            environments={"prod": env1, "staging": env2, "dev": env3},
            schema_dir="schemas",
            config_path=self.config_path,
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

    def test_remove_environment_config_not_found(self):
        """Test that FileNotFoundError is raised when config doesn't exist."""
        non_existent = Path(self.temp_dir) / "nonexistent" / CONFIG_FILE_NAME
        with self.assertRaises(FileNotFoundError):
            remove_environment("test", non_existent)

    def test_remove_all_environments(self):
        """Test removing all environments leaves empty dict."""
        remove_environment("prod", self.config_path)
        remove_environment("staging", self.config_path)
        remove_environment("dev", self.config_path)

        config = load_config(self.config_path)
        self.assertEqual(len(config.environments), 0)


class TestPathRecalculation(unittest.TestCase):
    """Tests for path recalculation when adding environments."""

    def setUp(self):
        """Create complex directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

        # Create directory structure:
        # temp_dir/
        #   project/
        #     firestore-migration/config.yaml
        #     src/
        #   keys/
        #     prod.json
        self.project_dir = Path(self.temp_dir) / "project"
        self.project_dir.mkdir()

        self.workspace_dir = self.project_dir / CONFIG_DIR_NAME
        self.workspace_dir.mkdir()
        self.config_path = self.workspace_dir / CONFIG_FILE_NAME

        self.keys_dir = Path(self.temp_dir) / "keys"
        self.keys_dir.mkdir()
        (self.keys_dir / "prod.json").touch()

        # Create initial config
        initial_config = WorkspaceConfig(
            version=1,
            environments={},
            schema_dir="schemas",
            config_path=self.config_path,
        )
        save_config(initial_config)

    def test_path_recalculation_sibling_directory(self):
        """Test path recalculation for key in sibling directory."""
        original_cwd = os.getcwd()
        os.chdir(self.project_dir)
        try:
            # Add environment with path relative to project_dir
            add_environment(
                env_name="prod",
                key_file="../keys/prod.json",
                config_path=self.config_path,
            )

            config = load_config(self.config_path)
            prod_env = config.environments["prod"]

            # Path should be relative to config.yaml location (normalize for cross-platform)
            # config.yaml is at: temp_dir/project/firestore-migration/config.yaml
            # key is at: temp_dir/keys/prod.json
            # relative path: ../../keys/prod.json
            self.assertEqual(Path(prod_env.key_file), Path("../../keys/prod.json"))

            # Verify absolute path is correct
            abs_key_file = config.config_dir / prod_env.key_file
            expected_abs_path = self.keys_dir / "prod.json"
            self.assertEqual(abs_key_file.resolve(), expected_abs_path.resolve())

        finally:
            os.chdir(original_cwd)

    def test_path_recalculation_from_subdirectory(self):
        """Test path recalculation when running from subdirectory."""
        # Create src directory
        src_dir = self.project_dir / "src"
        src_dir.mkdir()

        original_cwd = os.getcwd()
        os.chdir(src_dir)
        try:
            # Add environment with path relative to src_dir
            add_environment(
                env_name="prod",
                key_file="../../keys/prod.json",
                config_path=self.config_path,
            )

            config = load_config(self.config_path)
            prod_env = config.environments["prod"]

            # Verify absolute path is correct
            abs_key_file = config.config_dir / prod_env.key_file
            expected_abs_path = self.keys_dir / "prod.json"
            self.assertEqual(abs_key_file.resolve(), expected_abs_path.resolve())

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
