import httpx # Using httpx for async requests
import logging
import json
from typing import Dict, Any, AsyncIterator, List, Optional

from src.core.request import MCPRequest, CallToolRequest, RequestId
from src.core.response import (
    MCPPartialResponse,
    CallToolResult,
    BaseResult,
    TextContent, # For simple text content in CallToolResult
    EmbeddedResource, # For structured JSON data
    ResourceContents # For EmbeddedResource
)

logger = logging.getLogger(__name__)

class GitHubDriver:
    """
    Driver for GitHub integration, typically using MCP CallToolRequest/CallToolResult.
    """

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.github.com")
        self.test_mode = config.get("test_mode", False)

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.api_key:
            headers["Authorization"] = f"token {self.api_key}"

        self.http_client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)

    async def execute_mcp_request(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> BaseResult:
        """
        Handles MCP requests, expecting CallToolRequest for GitHub actions.
        """
        if not isinstance(mcp_request_model, CallToolRequest):
            logger.error(f"GitHubDriver received unsupported request type: {type(mcp_request_model).__name__}")
            # Return a CallToolResult indicating an error
            return CallToolResult(
                content=[TextContent(text=f"Unsupported request type for GitHub: {type(mcp_request_model).__name__}")],
                isError=True,
                _meta={"id": f"error-github-resp-{request_id}"}
            )

        request_params = mcp_request_model.params
        action_name = request_params.name # This is the "tool name", e.g., "github_list_repositories"
        arguments = request_params.arguments or {}

        try:
            if action_name == "list_repositories":
                response_data = await self._list_repositories(arguments)
            elif action_name == "create_issue":
                response_data = await self._create_issue(arguments)
            elif action_name == "search_code":
                response_data = await self._search_code(arguments)
            elif action_name == "get_repository":
                response_data = await self._get_repository(arguments)
            else:
                logger.warning(f"Unsupported GitHub action via CallToolRequest: {action_name}")
                return CallToolResult(
                    content=[TextContent(text=f"Unsupported GitHub action: {action_name}")],
                    isError=True,
                     _meta={"id": f"error-github-action-{request_id}"}
                )

            # Structure the response_data into CallToolResult
            # For complex data, EmbeddedResource with JSON is good.
            # For simpler lists or single items, multiple TextContent blocks might work.
            if isinstance(response_data, (dict, list)):
                # Embed the JSON data
                embedded_content = EmbeddedResource(
                    type="resource", # As per MCP spec
                    resource=TextResourceContents( # Using TextResourceContents to wrap JSON string
                        uri=f"github://{action_name}/{request_id}", # Synthetic URI
                        mimeType="application/json",
                        text=json.dumps(response_data, indent=2)
                    ),
                    annotations={"title": f"GitHub Action: {action_name} Result"}
                )
                return CallToolResult(
                    content=[embedded_content],
                    structuredContent=response_data, # Also provide as structured if useful
                    isError=False,
                    _meta={"id": f"github-resp-{request_id}"}
                )
            else: # Should not happen if internal methods return dict/list
                return CallToolResult(
                    content=[TextContent(text=str(response_data))],
                    isError=False, # Or True if this is unexpected
                    _meta={"id": f"github-resp-{request_id}"}
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API HTTP error for action {action_name} ({request_id}): {e.response.status_code} - {e.response.text}")
            error_content = TextContent(text=f"GitHub API Error: {e.response.status_code} - {e.response.text}")
            return CallToolResult(content=[error_content], isError=True, _meta={"id": f"httperror-github-{request_id}"})
        except ValueError as e: # For validation errors within our methods
            logger.warning(f"ValueError for GitHub action {action_name} ({request_id}): {str(e)}")
            return CallToolResult(content=[TextContent(text=str(e))], isError=True, _meta={"id": f"valerror-github-{request_id}"})
        except Exception as e:
            logger.error(f"Unexpected error in GitHubDriver for action {action_name} ({request_id}): {e}", exc_info=True)
            return CallToolResult(content=[TextContent(text=f"Unexpected error: {str(e)}")], isError=True, _meta={"id": f"unexperror-github-{request_id}"})


    async def _list_repositories(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.test_mode:
            logger.info("GitHubDriver: _list_repositories called in test_mode")
            return [{"id": 1, "name": "example-repo", "full_name": "user/example-repo"}]

        # httpx params should be passed to `params` argument of get/post etc.
        api_params = params.get("api_params", {}) # e.g., visibility, affiliation
        response = await self.http_client.get("/user/repos", params=api_params)
        response.raise_for_status()
        return response.json()

    async def _get_repository(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo_full_name = params.get("repo_full_name") # e.g., "owner/repo"
        if not repo_full_name:
            raise ValueError("`repo_full_name` is required for get_repository.")

        if self.test_mode:
            logger.info(f"GitHubDriver: _get_repository called for {repo_full_name} in test_mode")
            return {"id": 123, "name": repo_full_name.split('/')[-1], "full_name": repo_full_name, "description": "Mock repo"}

        response = await self.http_client.get(f"/repos/{repo_full_name}")
        response.raise_for_status()
        return response.json()

    async def _create_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo_full_name = params.get("repo_full_name")
        title = params.get("title")
        body = params.get("body", "") # Optional body

        if not repo_full_name or not title:
            raise ValueError("`repo_full_name` and `title` are required for create_issue.")

        if self.test_mode:
            logger.info(f"GitHubDriver: _create_issue for {repo_full_name} with title '{title}' in test_mode")
            return {"id": 1, "number": 101, "title": title, "body": body, "html_url": "http://example.com/mock/issue/1"}

        payload = {"title": title, "body": body}
        # Add other optional fields like assignees, labels from params if needed

        response = await self.http_client.post(f"/repos/{repo_full_name}/issues", json=payload)
        response.raise_for_status()
        return response.json()

    async def _search_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query:
            raise ValueError("`query` is required for search_code.")

        if self.test_mode:
            logger.info(f"GitHubDriver: _search_code with query '{query}' in test_mode")
            return {"total_count": 1, "items": [{"name": "mock_file.py", "path": "src/mock_file.py", "html_url": "http://example.com/mock_file.py"}]}

        # GitHub API uses 'q' for query parameter
        response = await self.http_client.get("/search/code", params={"q": query})
        response.raise_for_status()
        return response.json()

    async def stream_mcp_responses(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> AsyncIterator[MCPPartialResponse]:
        """GitHub API operations are typically not streaming in the LLM sense."""
        logger.warning(f"GitHubDriver does not support streaming for request: {mcp_request_model.method if hasattr(mcp_request_model, 'method') else 'unknown_method'}")
        yield MCPPartialResponse(
            error={"code": -32601, "message": "Streaming not supported by GitHubDriver"}, # Method not found or not applicable
            is_final_chunk=True,
            metadata={"request_id": request_id}
        ); return # Must include semicolon for empty async generator with yield

    async def handle_mcp_notification(self, mcp_notification_model: MCPRequest, request_id: Optional[RequestId] = None) -> None:
        logger.debug(f"GitHubDriver received notification: {mcp_notification_model.method if hasattr(mcp_notification_model, 'method') else 'unknown_method'} for request_id: {request_id}")
        # GitHub driver typically won't act on notifications from the client in this architecture
        pass

    async def close_session(self):
        """Closes the HTTP client session."""
        await self.http_client.aclose()

    # Optional: Implement __aenter__ and __aexit__ if driver is used as context manager
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
