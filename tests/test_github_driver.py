#!/usr/bin/env python3
"""
Tests for the GitHub driver integration.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.drivers.github_driver import GitHubDriver
from src.core.request import MCPRequest


class TestGitHubDriver(unittest.TestCase):
    """Test cases for GitHub driver functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_config = {
            "api_key": "test-key",
            "test_mode": True
        }
        self.driver = GitHubDriver(self.test_config)
        
    def test_initialization(self):
        """Test GitHub driver initialization."""
        self.assertEqual(self.driver.api_key, "test-key")
        self.assertEqual(self.driver.base_url, "https://api.github.com")
        self.assertTrue(self.driver.test_mode)
        
    def test_list_repositories(self):
        """Test list repositories functionality."""
        request = MCPRequest(
            model="github",
            parameters={"visibility": "public"},
            metadata={
                "action": "list_repositories",
                "service_type": "non_llm"
            }
        )
        
        response = self.driver.send_request(request)
        
        # Verify response structure
        self.assertIn("github_data", response.plugin_data)
        self.assertEqual(response.metadata["provider"], "github")
        self.assertEqual(response.metadata["action"], "list_repositories")
        
        # Verify data content (test mode should return mock data)
        repos = response.plugin_data["github_data"]
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["name"], "example-repo")
        
    def test_get_repository(self):
        """Test get repository functionality."""
        request = MCPRequest(
            model="github",
            parameters={"repo": "test-user/test-repo"},
            metadata={
                "action": "get_repository",
                "service_type": "non_llm"
            }
        )
        
        response = self.driver.send_request(request)
        
        # Verify response data
        repo_data = response.plugin_data["github_data"]
        self.assertEqual(repo_data["name"], "test-repo")
        self.assertEqual(repo_data["full_name"], "test-user/test-repo")
        
    def test_search_code(self):
        """Test search code functionality."""
        request = MCPRequest(
            model="github",
            parameters={"query": "test-query"},
            metadata={
                "action": "search_code",
                "service_type": "non_llm"
            }
        )
        
        response = self.driver.send_request(request)
        
        # Verify search results
        search_data = response.plugin_data["github_data"]
        self.assertEqual(search_data["total_count"], 2)
        self.assertEqual(len(search_data["items"]), 2)
        
    def test_create_issue(self):
        """Test create issue functionality."""
        request = MCPRequest(
            model="github",
            parameters={
                "repo": "test-user/test-repo",
                "title": "Test Issue",
                "body": "This is a test issue"
            },
            metadata={
                "action": "create_issue",
                "service_type": "non_llm"
            }
        )
        
        response = self.driver.send_request(request)
        
        # Verify issue creation
        issue_data = response.plugin_data["github_data"]
        self.assertEqual(issue_data["title"], "Test Issue")
        self.assertEqual(issue_data["body"], "This is a test issue")
        self.assertEqual(issue_data["state"], "open")
        
    def test_invalid_action(self):
        """Test handling of invalid actions."""
        request = MCPRequest(
            model="github",
            parameters={},
            metadata={
                "action": "invalid_action",
                "service_type": "non_llm"
            }
        )
        
        with self.assertRaises(ValueError):
            self.driver.send_request(request)
    
    def test_stream_tokens(self):
        """Test stream tokens functionality."""
        request = MCPRequest(
            model="github",
            parameters={"repo": "test-user/test-repo"},
            metadata={
                "action": "get_repository",
                "service_type": "non_llm"
            }
        )
        
        # Get the generator
        stream_gen = self.driver.stream_tokens(request)
        
        # Get the first (and only) item
        response = next(stream_gen)
        
        # Verify it's a final response
        self.assertTrue(response.is_final)
        
        # Verify no more items
        with self.assertRaises(StopIteration):
            next(stream_gen)


if __name__ == "__main__":
    unittest.main()
