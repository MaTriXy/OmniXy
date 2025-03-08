#!/usr/bin/env python3
"""
GitHub Integration Example for OmniXy

This example demonstrates how to use OmniXy as a universal MCP client
to interact with GitHub as an MCP server, showcasing integration with
non-LLM services using the same protocol interface.
"""

import os
import sys
import json
from typing import Dict, Any

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import MCPClient
from src.core.request import MCPRequest


def print_response_data(data: Any) -> None:
    """Pretty print the response data."""
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def github_list_repositories_example(client: MCPClient) -> None:
    """Example of listing GitHub repositories."""
    print("\n=== Example: List GitHub Repositories ===")
    
    # Create a request to list repositories
    request = MCPRequest(
        model="github",  # Non-LLM model identifier
        messages=[],     # Not used for GitHub but required by the interface
        parameters={"visibility": "public", "per_page": 10},
        metadata={"action": "list_repositories"}
    )
    
    # Send the request to the GitHub driver
    response = client.send_request("github", request)
    
    # Extract and display the response data
    github_data = response.plugin_data.get("github_data", {})
    print(f"Found {len(github_data)} repositories:")
    print_response_data(github_data)


def github_get_repository_example(client: MCPClient, repo_name: str) -> None:
    """Example of getting details for a specific repository."""
    print(f"\n=== Example: Get Repository Details for {repo_name} ===")
    
    # Create a request to get repository details
    request = MCPRequest(
        model="github",
        messages=[],
        parameters={"repo": repo_name},
        metadata={"action": "get_repository"}
    )
    
    # Send the request to the GitHub driver
    response = client.send_request("github", request)
    
    # Extract and display the response data
    github_data = response.plugin_data.get("github_data", {})
    print("Repository details:")
    print_response_data(github_data)


def github_search_code_example(client: MCPClient, query: str) -> None:
    """Example of searching code on GitHub."""
    print(f"\n=== Example: Search Code for '{query}' ===")
    
    # Create a request to search code
    request = MCPRequest(
        model="github",
        messages=[],
        parameters={"query": query},
        metadata={"action": "search_code"}
    )
    
    # Send the request to the GitHub driver
    response = client.send_request("github", request)
    
    # Extract and display the response data
    github_data = response.plugin_data.get("github_data", {})
    print(f"Found {github_data.get('total_count', 0)} code matches:")
    print_response_data(github_data)


def main() -> None:
    """Run the GitHub integration examples."""
    print("OmniXy GitHub Integration Example")
    print("=================================")
    
    # Initialize the client
    client = MCPClient()
    
    # GitHub configuration - in production, you'd use a real API token
    github_config = {
        "api_key": os.environ.get("GITHUB_API_KEY", ""),
        "test_mode": True  # Use test mode to return mock responses
    }
    
    # Register the GitHub provider
    print("\nRegistering GitHub provider with OmniXy client...")
    client.register_provider("github", github_config)
    print("GitHub provider registered successfully.")
    
    # Run the examples
    github_list_repositories_example(client)
    github_get_repository_example(client, "octocat/hello-world")
    github_search_code_example(client, "language:python requests")
    
    print("\nExamples completed successfully!")


if __name__ == "__main__":
    main()
