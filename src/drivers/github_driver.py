from typing import Dict, Any, Iterator, Optional, List

from src.core.request import MCPRequest
from src.core.response import MCPResponse, MCPPartialResponse


class GitHubDriver:
    """Driver for GitHub MCP server integration.
    
    This driver demonstrates OmniXy's capability to serve as a universal MCP client
    by integrating with non-LLM services through the same protocol interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the GitHub driver.
        
        Args:
            config: Configuration dictionary containing GitHub API credentials
        """
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.github.com")
        self.test_mode = config.get("test_mode", False)
        self.session = None
        self._initialize_session()
        
    def _initialize_session(self):
        """Initialize the HTTP session with proper authentication."""
        import requests
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"token {self.api_key}",
                "Accept": "application/vnd.github.v3+json"
            })
    
    def send_request(self, request: MCPRequest) -> MCPResponse:
        """Send a request to the GitHub API.
        
        Args:
            request: MCP request object
            
        Returns:
            MCPResponse: Response from GitHub API
        """
        # Extract action and parameters from the request
        action = request.metadata.get("action", "")
        params = request.parameters or {}
        
        # Map MCP actions to GitHub API endpoints
        if action == "list_repositories":
            response_data = self._list_repositories(params)
        elif action == "create_issue":
            response_data = self._create_issue(params)
        elif action == "search_code":
            response_data = self._search_code(params)
        elif action == "get_repository":
            response_data = self._get_repository(params)
        else:
            raise ValueError(f"Unsupported GitHub action: {action}")
            
        # Transform the response into an MCPResponse
        return MCPResponse(
            text=str(response_data),  # Simple string representation
            metadata={
                "provider": "github",
                "action": action,
                "timestamp": "2025-03-08T12:00:00Z"
            },
            plugin_data={"github_data": response_data}
        )
    
    def _list_repositories(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List repositories for the authenticated user."""
        if self.test_mode:
            # Return mock data in test mode
            return [
                {"id": 1, "name": "example-repo", "full_name": "user/example-repo"},
                {"id": 2, "name": "another-repo", "full_name": "user/another-repo"}
            ]
            
        # Real implementation would call the GitHub API
        response = self.session.get(f"{self.base_url}/user/repos", params=params)
        response.raise_for_status()
        return response.json()
    
    def _get_repository(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific repository's details."""
        repo = params.get("repo")
        
        if not repo:
            raise ValueError("Repository name is required")
            
        if self.test_mode:
            # Return mock data in test mode
            return {
                "id": 1, 
                "name": repo.split("/")[-1], 
                "full_name": repo,
                "description": "Example repository",
                "stargazers_count": 42,
                "forks_count": 13,
                "open_issues_count": 5
            }
            
        # Real implementation would call the GitHub API
        response = self.session.get(f"{self.base_url}/repos/{repo}")
        response.raise_for_status()
        return response.json()
    
    def _create_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create an issue in a repository."""
        repo = params.get("repo")
        title = params.get("title")
        body = params.get("body")
        
        if not repo or not title:
            raise ValueError("Repository and title are required for creating an issue")
            
        if self.test_mode:
            # Return mock data in test mode
            return {
                "id": 123,
                "number": 42,
                "title": title,
                "body": body,
                "state": "open"
            }
            
        # Real implementation would call the GitHub API
        payload = {"title": title, "body": body}
        response = self.session.post(f"{self.base_url}/repos/{repo}/issues", json=payload)
        response.raise_for_status()
        return response.json()
    
    def _search_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for code in GitHub repositories."""
        query = params.get("query")
        
        if not query:
            raise ValueError("Query is required for searching code")
            
        if self.test_mode:
            # Return mock data in test mode
            return {
                "total_count": 2,
                "items": [
                    {"path": "file1.py", "repository": {"full_name": "user/repo1"}},
                    {"path": "file2.py", "repository": {"full_name": "user/repo2"}}
                ]
            }
            
        # Real implementation would call the GitHub API
        response = self.session.get(f"{self.base_url}/search/code", params={"q": query})
        response.raise_for_status()
        return response.json()
    
    def stream_tokens(self, request: MCPRequest) -> Iterator[MCPPartialResponse]:
        """GitHub API doesn't support streaming, so this returns a single response.
        
        This is included to maintain compatibility with the driver interface.
        
        Args:
            request: MCP request object
            
        Returns:
            Iterator[MCPPartialResponse]: Iterator with a single response
        """
        response = self.send_request(request)
        yield MCPPartialResponse(
            partial_text=response.text,
            is_final=True,
            metadata=response.metadata
        )
