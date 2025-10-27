"""Tests for AI Test Runner CLI."""

import pytest
from unittest.mock import patch, MagicMock
from ai_test_runner.cli import main, AITestRunner


class TestAITestRunner:
    """Test the AITestRunner class."""

    @patch('ai_test_runner.cli.subprocess.run')
    @patch('ai_test_runner.cli.shutil.copytree')
    @patch('ai_test_runner.cli.shutil.copy2')
    @patch('ai_test_runner.cli.Path')
    def test_find_compilable_tests(self, mock_path, mock_copy2, mock_copytree, mock_subprocess):
        """Test finding compilable tests."""
        # Mock the Path and file discovery
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.glob.return_value = [
            MagicMock(name='test1_compiles_yes.txt'),
            MagicMock(name='test2_compiles_yes.txt'),
        ]

        runner = AITestRunner(repo_path='/fake/path')
        tests = runner.find_compilable_tests()

        assert len(tests) == 2
        assert 'test1' in tests
        assert 'test2' in tests

    @patch('ai_test_runner.cli.subprocess.run')
    def test_build_tests_success(self, mock_subprocess):
        """Test successful build."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Build successful', stderr='')

        runner = AITestRunner(repo_path='/fake/path')
        result = runner.build_tests()

        assert result is True
        mock_subprocess.assert_called()

    @patch('ai_test_runner.cli.subprocess.run')
    def test_build_tests_failure(self, mock_subprocess):
        """Test build failure."""
        mock_subprocess.return_value = MagicMock(returncode=1, stdout='', stderr='Build failed')

        runner = AITestRunner(repo_path='/fake/path')
        result = runner.build_tests()

        assert result is False

    @patch('ai_test_runner.cli.subprocess.run')
    def test_run_tests_success(self, mock_subprocess):
        """Test successful test execution."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout='All tests passed', stderr='')

        runner = AITestRunner(repo_path='/fake/path')
        results = runner.run_tests(['test1', 'test2'])

        assert len(results) == 2
        assert all(result['passed'] for result in results)

    @patch('ai_test_runner.cli.subprocess.run')
    def test_run_tests_failure(self, mock_subprocess):
        """Test test execution with failures."""
        mock_subprocess.return_value = MagicMock(returncode=1, stdout='', stderr='Test failed')

        runner = AITestRunner(repo_path='/fake/path')
        results = runner.run_tests(['test1'])

        assert len(results) == 1
        assert not results[0]['passed']


class TestCLI:
    """Test the CLI interface."""

    @patch('ai_test_runner.cli.AITestRunner')
    def test_main_success(self, mock_runner_class):
        """Test successful main execution."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        mock_runner.find_compilable_tests.return_value = ['test1']
        mock_runner.copy_unity_framework.return_value = True
        mock_runner.create_cmake_lists.return_value = True
        mock_runner.build_tests.return_value = True
        mock_runner.run_tests.return_value = [{'name': 'test1', 'passed': True, 'output': ''}]
        mock_runner.generate_coverage.return_value = True

        with patch('sys.argv', ['ai-test-runner']):
            main()

        mock_runner.find_compilable_tests.assert_called_once()

    @patch('ai_test_runner.cli.AITestRunner')
    def test_main_no_tests_found(self, mock_runner_class):
        """Test when no compilable tests are found."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        mock_runner.find_compilable_tests.return_value = []

        with patch('sys.argv', ['ai-test-runner']):
            with pytest.raises(SystemExit):
                main()

    def test_version(self):
        """Test version display."""
        with patch('sys.argv', ['ai-test-runner', '--version']):
            with pytest.raises(SystemExit):
                main()