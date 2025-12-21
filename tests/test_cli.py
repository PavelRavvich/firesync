"""Unit tests for core.cli module."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cli import parse_pull_args, parse_plan_args, parse_apply_args, setup_client
from config import FiresyncConfig
from workspace import WorkspaceConfig, EnvironmentConfig


class TestParsePullArgs(unittest.TestCase):
    """Tests for parse_pull_args function."""

    def test_parse_pull_all(self):
        """Test parsing --all flag."""
        with patch.object(sys, 'argv', ['prog', '--all']):
            args = parse_pull_args("Test description")
            self.assertTrue(args.all)
            self.assertIsNone(args.env)

    def test_parse_pull_env(self):
        """Test parsing --env argument."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev']):
            args = parse_pull_args("Test description")
            self.assertFalse(args.all)
            self.assertEqual(args.env, 'dev')

    def test_parse_pull_missing_required(self):
        """Test that error is raised when no required arguments."""
        with patch.object(sys, 'argv', ['prog']):
            with self.assertRaises(SystemExit):
                parse_pull_args("Test description")


class TestParsePlanArgs(unittest.TestCase):
    """Tests for parse_plan_args function."""

    def test_parse_plan_env(self):
        """Test parsing --env argument."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev']):
            args = parse_plan_args("Test description")
            self.assertEqual(args.env, 'dev')
            self.assertIsNone(args.from_env)
            self.assertIsNone(args.to_env)

    def test_parse_plan_migration(self):
        """Test parsing migration mode arguments."""
        with patch.object(sys, 'argv', ['prog', '--from', 'dev', '--to', 'staging']):
            args = parse_plan_args("Test description")
            self.assertEqual(args.from_env, 'dev')
            self.assertEqual(args.to_env, 'staging')
            self.assertIsNone(args.env)

    def test_parse_plan_with_schema_dir(self):
        """Test parsing with schema directory override."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev', '--schema-dir', 'custom']):
            args = parse_plan_args("Test description")
            self.assertEqual(args.env, 'dev')
            self.assertEqual(args.schema_dir, 'custom')

    def test_parse_plan_migration_with_env_error(self):
        """Test that migration mode and env are mutually exclusive."""
        with patch.object(sys, 'argv', ['prog', '--from', 'dev', '--to', 'staging', '--env', 'prod']):
            with self.assertRaises(SystemExit):
                parse_plan_args("Test description")

    def test_parse_plan_incomplete_migration_error(self):
        """Test that both env-from and env-to must be specified."""
        with patch.object(sys, 'argv', ['prog', '--from', 'dev']):
            with self.assertRaises(SystemExit):
                parse_plan_args("Test description")

    def test_parse_plan_missing_arguments_error(self):
        """Test that at least one mode must be specified."""
        with patch.object(sys, 'argv', ['prog']):
            with self.assertRaises(SystemExit):
                parse_plan_args("Test description")


class TestParseApplyArgs(unittest.TestCase):
    """Tests for parse_apply_args function."""

    def test_parse_apply_env(self):
        """Test parsing --env argument."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev']):
            args = parse_apply_args("Test description")
            self.assertEqual(args.env, 'dev')
            self.assertIsNone(args.from_env)
            self.assertIsNone(args.to_env)

    def test_parse_apply_migration(self):
        """Test parsing migration mode arguments."""
        with patch.object(sys, 'argv', ['prog', '--from', 'dev', '--to', 'prod']):
            args = parse_apply_args("Test description")
            self.assertEqual(args.from_env, 'dev')
            self.assertEqual(args.to_env, 'prod')
            self.assertIsNone(args.env)

    def test_parse_apply_with_schema_dir(self):
        """Test parsing with schema directory override."""
        with patch.object(sys, 'argv', ['prog', '--env', 'staging', '--schema-dir', '/custom/path']):
            args = parse_apply_args("Test description")
            self.assertEqual(args.env, 'staging')
            self.assertEqual(args.schema_dir, '/custom/path')


class TestSetupClient(unittest.TestCase):
    """Tests for setup_client function."""

    @patch('cli.GCloudClient')
    @patch('cli.load_config')
    @patch('config.FiresyncConfig.from_args')
    def test_setup_client_with_key_path(self, mock_from_args, mock_load_config, mock_gcloud):
        """Test setup_client with key_path configuration."""
        # Setup mock workspace config
        env_config = EnvironmentConfig(
            name='dev',
            key_path='secrets/key.json',
            key_env=None,
            description=None
        )
        workspace_config = MagicMock(spec=WorkspaceConfig)
        workspace_config.get_env.return_value = env_config
        workspace_config.config_dir = Path('/test')
        workspace_config.get_schema_dir.return_value = Path('/test/firestore_schema/dev')
        mock_load_config.return_value = workspace_config

        # Setup mock config
        mock_config = MagicMock(spec=FiresyncConfig)
        mock_from_args.return_value = mock_config

        # Call setup_client
        config, client = setup_client('dev')

        # Verify
        mock_load_config.assert_called_once()
        workspace_config.get_env.assert_called_once_with('dev')

        # Check call arguments (convert paths to strings for cross-platform compatibility)
        call_args = mock_from_args.call_args[1]
        self.assertEqual(call_args['key_path'], str(Path('/test/secrets/key.json')))
        self.assertIsNone(call_args['key_env'])
        self.assertEqual(call_args['schema_dir'], str(Path('/test/firestore_schema/dev')))

        mock_config.display_info.assert_called_once()
        mock_gcloud.assert_called_once_with(mock_config, dry_run=False)

    @patch('cli.GCloudClient')
    @patch('cli.load_config')
    @patch('config.FiresyncConfig.from_args')
    def test_setup_client_with_key_env(self, mock_from_args, mock_load_config, mock_gcloud):
        """Test setup_client with key_env configuration."""
        # Setup mock workspace config
        env_config = EnvironmentConfig(
            name='staging',
            key_path=None,
            key_env='GCP_KEY',
            description=None
        )
        workspace_config = MagicMock(spec=WorkspaceConfig)
        workspace_config.get_env.return_value = env_config
        workspace_config.config_dir = Path('/project')
        workspace_config.get_schema_dir.return_value = Path('/project/firestore_schema/staging')
        mock_load_config.return_value = workspace_config

        # Setup mock config
        mock_config = MagicMock(spec=FiresyncConfig)
        mock_from_args.return_value = mock_config

        # Call setup_client
        config, client = setup_client('staging')

        # Verify (convert paths to strings for cross-platform compatibility)
        call_args = mock_from_args.call_args[1]
        self.assertIsNone(call_args['key_path'])
        self.assertEqual(call_args['key_env'], 'GCP_KEY')
        self.assertEqual(call_args['schema_dir'], str(Path('/project/firestore_schema/staging')))

    @patch('cli.GCloudClient')
    @patch('cli.load_config')
    @patch('config.FiresyncConfig.from_args')
    def test_setup_client_with_schema_dir_override(self, mock_from_args, mock_load_config, mock_gcloud):
        """Test setup_client with schema_dir override."""
        # Setup mock workspace config
        env_config = EnvironmentConfig(
            name='dev',
            key_path=None,
            key_env='GCP_KEY',
            description=None
        )
        workspace_config = MagicMock(spec=WorkspaceConfig)
        workspace_config.get_env.return_value = env_config
        workspace_config.config_dir = Path('/test')
        mock_load_config.return_value = workspace_config

        # Setup mock config
        mock_config = MagicMock(spec=FiresyncConfig)
        mock_from_args.return_value = mock_config

        # Call setup_client with schema_dir override
        config, client = setup_client('dev', schema_dir='/custom/schemas')

        # Verify schema_dir override is used
        mock_from_args.assert_called_once_with(
            key_path=None,
            key_env='GCP_KEY',
            schema_dir='/custom/schemas'
        )


class TestNewCLIFeatures(unittest.TestCase):
    """Tests for Phase 1 and Phase 2 CLI improvements."""

    def test_parse_pull_short_flag_all(self):
        """Test parsing -a short flag for --all."""
        with patch.object(sys, 'argv', ['prog', '-a']):
            args = parse_pull_args("Test description")
            self.assertTrue(args.all)

    def test_parse_pull_short_flag_env(self):
        """Test parsing -e short flag for --env."""
        with patch.object(sys, 'argv', ['prog', '-e', 'dev']):
            args = parse_pull_args("Test description")
            self.assertEqual(args.env, 'dev')

    def test_parse_plan_short_flag_env(self):
        """Test parsing -e short flag in plan command."""
        with patch.object(sys, 'argv', ['prog', '-e', 'staging']):
            args = parse_plan_args("Test description")
            self.assertEqual(args.env, 'staging')

    def test_parse_plan_short_flag_schema_dir(self):
        """Test parsing -d short flag for --schema-dir."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev', '-d', '/custom']):
            args = parse_plan_args("Test description")
            self.assertEqual(args.schema_dir, '/custom')

    def test_parse_apply_auto_approve(self):
        """Test parsing --auto-approve flag."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev', '--auto-approve']):
            args = parse_apply_args("Test description")
            self.assertTrue(args.auto_approve)

    def test_parse_apply_auto_approve_short(self):
        """Test parsing -y short flag for --auto-approve."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev', '-y']):
            args = parse_apply_args("Test description")
            self.assertTrue(args.auto_approve)

    def test_parse_apply_dry_run(self):
        """Test parsing --dry-run flag."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev', '--dry-run']):
            args = parse_apply_args("Test description")
            self.assertTrue(args.dry_run)

    def test_parse_apply_dry_run_with_auto_approve(self):
        """Test parsing both --dry-run and --auto-approve."""
        with patch.object(sys, 'argv', ['prog', '--env', 'dev', '--dry-run', '-y']):
            args = parse_apply_args("Test description")
            self.assertTrue(args.dry_run)
            self.assertTrue(args.auto_approve)

    def test_parse_apply_migration_with_dry_run(self):
        """Test parsing migration mode with dry-run."""
        with patch.object(sys, 'argv', ['prog', '--from', 'dev', '--to', 'prod', '--dry-run']):
            args = parse_apply_args("Test description")
            self.assertEqual(args.from_env, 'dev')
            self.assertEqual(args.to_env, 'prod')
            self.assertTrue(args.dry_run)

    @patch('cli.GCloudClient')
    @patch('cli.load_config')
    @patch('config.FiresyncConfig.from_args')
    def test_setup_client_with_dry_run(self, mock_from_args, mock_load_config, mock_gcloud):
        """Test setup_client with dry_run parameter."""
        # Setup mocks
        env_config = EnvironmentConfig(
            name='dev',
            key_path='secrets/key.json',
            key_env=None,
            description=None
        )
        workspace_config = MagicMock(spec=WorkspaceConfig)
        workspace_config.get_env.return_value = env_config
        workspace_config.config_dir = Path('/test')
        workspace_config.get_schema_dir.return_value = Path('/test/schemas/dev')
        mock_load_config.return_value = workspace_config

        mock_config = MagicMock(spec=FiresyncConfig)
        mock_from_args.return_value = mock_config

        # Call setup_client with dry_run=True
        config, client = setup_client('dev', dry_run=True)

        # Verify GCloudClient was called with dry_run=True
        mock_gcloud.assert_called_once_with(mock_config, dry_run=True)


if __name__ == '__main__':
    unittest.main()
