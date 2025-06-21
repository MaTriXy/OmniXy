"""
Tests for the GitHub driver integration using pytest and asyncio.
"""
import pytest
import json
from unittest.mock import patch # For mocking httpx.AsyncClient if not using test_mode extensively

from src.drivers.github_driver import GitHubDriver
from src.core.request import CallToolRequest, CallToolRequestParams
from src.core.response import CallToolResult, TextContent, EmbeddedResource, TextResourceContents, MCPPartialResponse

@pytest.fixture
async def github_driver_test_mode():
    """Fixture for GitHubDriver in test mode."""
    config = {"api_key": "test-key-unused-in-test-mode", "test_mode": True}
    driver = GitHubDriver(config)
    yield driver
    await driver.close_session() # Ensure session is closed

@pytest.mark.asyncio
async def test_initialization(github_driver_test_mode: GitHubDriver):
    """Test GitHub driver initialization."""
    driver = github_driver_test_mode
    assert driver.api_key == "test-key-unused-in-test-mode"
    assert driver.base_url == "https://api.github.com"
    assert driver.test_mode is True

@pytest.mark.asyncio
async def test_list_repositories(github_driver_test_mode: GitHubDriver):
    """Test list repositories functionality using CallToolRequest."""
    driver = github_driver_test_mode
    params = CallToolRequestParams(
        name="list_repositories",
        arguments={"api_params": {"visibility": "public"}} # Example of passing API params
    )
    request_model = CallToolRequest(params=params)
    request_id = "list-repo-test-1"

    response = await driver.execute_mcp_request(request_model, request_id)

    assert isinstance(response, CallToolResult)
    assert response.isError is False
    assert response.structuredContent is not None
    assert len(response.structuredContent) == 1 # Mock returns one repo
    assert response.structuredContent[0]["name"] == "example-repo"

    assert len(response.content) == 1
    assert isinstance(response.content[0], EmbeddedResource)
    assert isinstance(response.content[0].resource, TextResourceContents)
    assert response.content[0].resource.mimeType == "application/json"
    loaded_json_content = json.loads(response.content[0].resource.text)
    assert loaded_json_content[0]["name"] == "example-repo"


@pytest.mark.asyncio
async def test_get_repository(github_driver_test_mode: GitHubDriver):
    """Test get repository functionality."""
    driver = github_driver_test_mode
    params = CallToolRequestParams(
        name="get_repository",
        arguments={"repo_full_name": "test-user/test-repo"}
    )
    request_model = CallToolRequest(params=params)
    request_id = "get-repo-test-1"

    response = await driver.execute_mcp_request(request_model, request_id)

    assert isinstance(response, CallToolResult)
    assert response.isError is False
    assert response.structuredContent is not None
    assert response.structuredContent["name"] == "test-repo"
    assert response.structuredContent["full_name"] == "test-user/test-repo"

@pytest.mark.asyncio
async def test_search_code(github_driver_test_mode: GitHubDriver):
    """Test search code functionality."""
    driver = github_driver_test_mode
    params = CallToolRequestParams(
        name="search_code",
        arguments={"query": "test-query in:file language:python"}
    )
    request_model = CallToolRequest(params=params)
    request_id = "search-code-test-1"

    response = await driver.execute_mcp_request(request_model, request_id)

    assert isinstance(response, CallToolResult)
    assert response.isError is False
    assert response.structuredContent is not None
    assert response.structuredContent["total_count"] == 1
    assert len(response.structuredContent["items"]) == 1
    assert response.structuredContent["items"][0]["name"] == "mock_file.py"


@pytest.mark.asyncio
async def test_create_issue(github_driver_test_mode: GitHubDriver):
    """Test create issue functionality."""
    driver = github_driver_test_mode
    params = CallToolRequestParams(
        name="create_issue",
        arguments={
            "repo_full_name": "test-user/test-repo",
            "title": "Test Issue via MCP",
            "body": "This is a test issue created by the MCP GitHub driver.",
        }
    )
    request_model = CallToolRequest(params=params)
    request_id = "create-issue-test-1"

    response = await driver.execute_mcp_request(request_model, request_id)

    assert isinstance(response, CallToolResult)
    assert response.isError is False
    assert response.structuredContent is not None
    assert response.structuredContent["title"] == "Test Issue via MCP"
    assert response.structuredContent["body"] == "This is a test issue created by the MCP GitHub driver."
    assert response.structuredContent["id"] == 1 # Mock ID


@pytest.mark.asyncio
async def test_invalid_action_call_tool(github_driver_test_mode: GitHubDriver):
    """Test handling of invalid actions via CallToolRequest."""
    driver = github_driver_test_mode
    params = CallToolRequestParams(name="invalid_github_action", arguments={})
    request_model = CallToolRequest(params=params)
    request_id = "invalid-action-test-1"

    response = await driver.execute_mcp_request(request_model, request_id)

    assert isinstance(response, CallToolResult)
    assert response.isError is True
    assert "Unsupported GitHub action: invalid_github_action" in response.content[0].text


@pytest.mark.asyncio
async def test_stream_mcp_responses_github(github_driver_test_mode: GitHubDriver):
    """Test stream_mcp_responses for GitHub (expected to be not supported)."""
    driver = github_driver_test_mode
    # Create a dummy CallToolRequest, as GitHub driver expects this type
    params = CallToolRequestParams(name="list_repositories", arguments={})
    request_model = CallToolRequest(params=params)
    request_id = "stream-gh-test-1"

    results = []
    async for partial_response in driver.stream_mcp_responses(request_model, request_id):
        results.append(partial_response)

    assert len(results) == 1
    assert isinstance(results[0], MCPPartialResponse)
    assert results[0].is_final_chunk is True
    assert results[0].error is not None
    assert "Streaming not supported by GitHubDriver" in results[0].error["message"]


@pytest.mark.asyncio
async def test_github_driver_non_test_mode_mocked_api(event_loop): # event_loop fixture for asyncio with unittest.mock
    """ Test GitHub driver in non-test_mode with mocked httpx calls. """
    config = {"api_key": "fake-api-key", "test_mode": False}
    driver = GitHubDriver(config)

    # Example: Mocking list_repositories successful call
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = httpx.Response(200, json=[{"id": 1, "name": "live-repo"}])
        mock_get.return_value = mock_response # Mock the response object itself

        params = CallToolRequestParams(name="list_repositories", arguments={})
        request_model = CallToolRequest(params=params)
        response = await driver.execute_mcp_request(request_model, "live-list-repo-1")

        assert isinstance(response, CallToolResult)
        assert response.isError is False
        assert response.structuredContent[0]["name"] == "live-repo"
        mock_get.assert_called_once_with("/user/repos", params={}) # Verify API call

    # Example: Mocking create_issue failure (422 Unprocessable Entity)
    with patch('httpx.AsyncClient.post') as mock_post:
        error_json = {"message": "Validation Failed", "errors": [{"resource": "Issue", "code": "missing_field", "field": "title"}]}
        # For HTTPStatusError, the response is part of the exception
        mock_post.side_effect = httpx.HTTPStatusError(
            message="Client error '422 Unprocessable Entity' for url...",
            request=httpx.Request('POST', '/repos/owner/repo/issues'),
            response=httpx.Response(422, json=error_json)
        )

        params = CallToolRequestParams(name="create_issue", arguments={"repo_full_name": "owner/repo"}) # Missing title
        request_model = CallToolRequest(params=params)
        response = await driver.execute_mcp_request(request_model, "live-create-issue-fail-1")

        assert isinstance(response, CallToolResult)
        assert response.isError is True
        assert "GitHub API Error: 422" in response.content[0].text
        assert "Validation Failed" in response.content[0].text

    await driver.close_session()
