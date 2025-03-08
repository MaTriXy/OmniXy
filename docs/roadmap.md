# OmniXy Implementation Roadmap

This document outlines both the current status and planned enhancements to fully align OmniXy with the three-component Model Context Protocol (MCP) architecture: client, server, and protocol.

## Project Status

### Summary of Current State

1. **Core MCP Layer**:
   - Implemented in `mcp_layer.py`, handling protocol logic and provider routing.
2. **Provider Drivers**:
   - Implemented for Gemini, OpenAI, Cohere, and local LLMs in the `drivers` directory.
3. **Orchestration & Reasoning Layer**:
   - Partially implemented in `chain_of_thought.py`, but requires further development for multi-step reasoning.
4. **Front-End Client Interface**:
   - Implemented in `client.py`, providing a simple API for developers.
5. **Documentation**:
   - Comprehensive documentation exists for architecture, protocol, orchestration, provider drivers, and security.

### Suggested Next Steps

1. **Expand Orchestration Layer**:
   - Implement multi-step reasoning workflows in `chain_of_thought.py`.
   - Add support for context management and chaining of `MCPRequests`.
2. **Add More Provider Drivers**:
   - Implement drivers for additional LLM providers (e.g., Gemini, Anthropic).
3. **Enhance Security**:
   - Integrate a secure vault or secrets manager for credential storage.
   - Add rate limiting and quota enforcement.
4. **Improve Developer Experience**:
   - Add comprehensive examples and tutorials in the `docs` directory.
5. **Testing & Validation**:
   - Write unit and integration tests for all components.
   - Validate the system with real-world use cases.

## 1. Create a Clear Interface Layer

### Status: In Progress
✅ Added MCPClientInterface abstract base class to client.py
⬜ Update all provider methods to work with the interface
⬜ Add comprehensive testing of interface implementation

### Implementation Details
- **Core Interface**: The interface defines standard methods:
  - `connect()`: Establish connection to an MCP server
  - `send_request()`: Send a request to an MCP server
  - `stream_response()`: Stream response from an MCP server
  - `list_connected_servers()`: List all connected servers
  - `register_server()`: Register a new server connection
  - `disconnect()`: Disconnect from a server

- **Benefits**: 
  - Clearer separation between client/protocol/server components
  - Consistent behavior across different server implementations
  - Better extensibility for adding new provider types
  - Support for feature discovery and capability negotiation

- **Implementation Path**:
  1. ✅ Define the interface in client.py (completed)
  2. Update MCPClient to fully implement all interface methods
  3. Refactor provider-specific code to generalize for all server types
  4. Add integration tests for interface compliance

## 2. Enhance Multi-Server Support

### Status: Planned
⬜ Create server registry system
⬜ Implement generic server connection manager
⬜ Add server capability discovery mechanism
⬜ Support simultaneous connections to multiple servers

### Implementation Details
- **Server Registry**: A centralized system to manage MCP server connections
  - Server identification and capability discovery 
  - Connection pooling and lifecycle management
  - Dynamic server registration and configuration

- **Unified API**: Treat LLM providers and other services through the same interface
  - Abstract away the differences between service types
  - Common request/response format regardless of server type
  - Stream support for all compatible servers

- **Connection Management**:
  - Health monitoring and automatic reconnection
  - Authentication and credential management
  - Rate limiting and error handling

## 3. Protocol Documentation

### Status: Planned
⬜ Create standalone protocol specification
⬜ Separate implementation from protocol definition
⬜ Document message formats and schemas
⬜ Define extension mechanisms

### Implementation Details
- **Specification Structure**:
  - Message formats and schemas
  - Authentication and security requirements
  - Error handling and status codes
  - Compatibility and versioning guidelines

- **Protocol Invariants**:
  - Core request/response structures
  - Required vs. optional fields
  - Content type handling
  - Status and error codes

- **Extension Mechanisms**:
  - Capability advertisement
  - Versioned protocol extensions
  - Backward compatibility requirements

## 4. Example Integration with Non-LLM Services

### Status: Completed (GitHub Implementation)
✅ Create GitHub driver class
✅ Implement core GitHub API operations
✅ Add GitHub-specific request/response handling
✅ Provide usage examples
✅ Update core classes to support non-LLM services
✅ Implement and test GitHub driver

### GitHub Driver Implementation
```python
# src/drivers/github_driver.py
from typing import Dict, Any, Iterator, Optional, List

from src.core.request import MCPRequest
from src.core.response import MCPResponse, MCPPartialResponse


class GitHubDriver:
    """Driver for GitHub MCP server integration."""

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
```

### Implementation Steps for GitHub Integration
1. ✅ Create the GitHub driver class
2. ✅ Integrate with existing driver factory pattern
3. ✅ Enhanced MCPRequest to support non-LLM services
4. ✅ Updated MCPResponse with plugin_data for structured non-LLM data
5. ✅ Implemented comprehensive test suite for GitHub driver
6. ✅ Fixed validation issues in request handling for non-LLM services
7. ✅ Updated the MCPClient to register and use the GitHub driver
8. ✅ Added tests to verify GitHub driver functionality
9. ✅ Created example code for usage

### Example Usage
```python
from src.client import MCPClient
from src.core.request import MCPRequest
import os

# Initialize the client with GitHub provider
client = MCPClient(provider="github", config={
    "api_key": os.environ.get("GITHUB_API_KEY"),  # Set your GitHub API token
    "base_url": "https://api.github.com",
    "test_mode": True  # For testing without actual API calls
})

# Alternatively, register the provider after initialization
# client = MCPClient()
# client.register_provider("github", {
#     "api_key": os.environ.get("GITHUB_API_KEY"),
#     "test_mode": True
# })

# Create a request to list GitHub repositories
request = MCPRequest(
    model="github",
    parameters={"visibility": "public", "per_page": 10},
    metadata={
        "action": "list_repositories",
        "service_type": "non_llm"
    }
)

# Send the request
response = client.send_request(request)
# Or specify provider explicitly: client.send_request("github", request)

# Process the response
github_data = response.plugin_data["github_data"]
for repo in github_data:
    print(f"Repository: {repo['name']}")

# Create an issue example
issue_request = MCPRequest(
    model="github",
    parameters={
        "repo": "username/repository",
        "title": "Bug: Application crashes on startup",
        "body": "The application crashes immediately when launched on macOS."
    },
    metadata={
        "action": "create_issue",
        "service_type": "non_llm"
    }
)
issue_response = client.send_request(issue_request)
print(f"Issue created: #{issue_response.plugin_data['github_data']['number']}")
```

## Timeline and Milestones

| Phase | Milestone | Status | Estimated Completion | Priority |
|-------|-----------|--------|---------------------|----------|
| 1 | MCPClientInterface implementation | In Progress | Q2 2025 | High |
| 2 | Protocol documentation | Planned | Q2 2025 | High |
| 3 | GitHub driver implementation | Completed ✅ | March 2025 | Medium |
| 4 | Multi-server support | Planned | Q3 2025 | Medium |
| 5 | Slack integration example | Planned | Q4 2025 | Low |
| 6 | File system integration example | Planned | Q4 2025 | Low |

## Next Steps

1. Complete MCPClientInterface implementation in client.py
2. Create unit tests for interface compliance
3. ✅ Implement the GitHub driver as first non-LLM example
4. Add more error handling and edge cases to GitHub driver
5. Begin protocol documentation
6. Implement Slack integration as second non-LLM example
