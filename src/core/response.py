from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, AnyHttpUrl

from src.core.request import (
    JSONRPC_VERSION,
    RequestId,
    Role,
    Cursor,
    BaseMetadata,
    Implementation,
    Annotations,
    SamplingMessage,
    Content, # Re-used from request for CreateMessageResult
    TextContent,
    ImageContent,
    AudioContent
)


class ResultMeta(BaseModel):
    # Allows arbitrary keys
    model_config = {"extra": "allow"}


class BaseResult(BaseModel):
    _meta: Optional[ResultMeta] = None
    # Allows arbitrary keys
    model_config = {"extra": "allow"}


class JSONRPCResponse(BaseModel):
    jsonrpc: str = Field(default=JSONRPC_VERSION, frozen=True)
    id: RequestId
    result: BaseResult


class JSONRPCErrorResponse(BaseModel):
    jsonrpc: str = Field(default=JSONRPC_VERSION, frozen=True)
    id: RequestId
    error: Dict[str, Any]  # TODO: Define ErrorObject more strictly


class EmptyResult(BaseResult):
    pass


class ServerCapabilities(BaseModel):
    experimental: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    completions: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, bool]] = None
    resources: Optional[Dict[str, bool]] = None
    tools: Optional[Dict[str, bool]] = None


class InitializeResult(BaseResult):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: Optional[str] = None


class PaginatedResult(BaseResult):
    nextCursor: Optional[Cursor] = None


class Resource(BaseMetadata):
    uri: AnyHttpUrl
    description: Optional[str] = None
    mimeType: Optional[str] = None
    annotations: Optional[Annotations] = None
    size: Optional[int] = None
    _meta: Optional[Dict[str, Any]] = None


class ListResourcesResult(PaginatedResult):
    resources: List[Resource]


class ResourceTemplate(BaseMetadata):
    uriTemplate: str # uri-template
    description: Optional[str] = None
    mimeType: Optional[str] = None
    annotations: Optional[Annotations] = None
    _meta: Optional[Dict[str, Any]] = None


class ListResourceTemplatesResult(PaginatedResult):
    resourceTemplates: List[ResourceTemplate]


class ResourceContents(BaseModel):
    uri: AnyHttpUrl
    mimeType: Optional[str] = None
    _meta: Optional[Dict[str, Any]] = None


class TextResourceContents(ResourceContents):
    text: str


class BlobResourceContents(ResourceContents):
    blob: str  # Base64 encoded


class ReadResourceResult(BaseResult):
    contents: List[Union[TextResourceContents, BlobResourceContents]]


class PromptArgument(BaseMetadata):
    description: Optional[str] = None
    required: Optional[bool] = None


class Prompt(BaseMetadata):
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None
    _meta: Optional[Dict[str, Any]] = None


class ListPromptsResult(PaginatedResult):
    prompts: List[Prompt]


class ResourceLink(Resource):
    type: Literal["resource_link"] = "resource_link"


class EmbeddedResource(BaseModel):
    type: Literal["resource"] = "resource"
    resource: Union[TextResourceContents, BlobResourceContents]
    annotations: Optional[Annotations] = None
    _meta: Optional[Dict[str, Any]] = None


ContentBlock = Union[
    TextContent, ImageContent, AudioContent, ResourceLink, EmbeddedResource
]


class PromptMessage(BaseModel):
    role: Role
    content: ContentBlock


class GetPromptResult(BaseResult):
    description: Optional[str] = None
    messages: List[PromptMessage]


class ToolAnnotations(BaseModel):
    title: Optional[str] = None
    readOnlyHint: Optional[bool] = None
    destructiveHint: Optional[bool] = None
    idempotentHint: Optional[bool] = None
    openWorldHint: Optional[bool] = None


class ToolInputOutputSchema(BaseModel):
    type: Literal["object"] = "object"
    properties: Optional[Dict[str, Any]] = None # Could be more specific JSONSchema type
    required: Optional[List[str]] = None


class Tool(BaseMetadata):
    description: Optional[str] = None
    inputSchema: ToolInputOutputSchema
    outputSchema: Optional[ToolInputOutputSchema] = None
    annotations: Optional[ToolAnnotations] = None
    _meta: Optional[Dict[str, Any]] = None


class ListToolsResult(PaginatedResult):
    tools: List[Tool]


class CallToolResult(BaseResult):
    content: List[ContentBlock]
    structuredContent: Optional[Dict[str, Any]] = None
    isError: Optional[bool] = None


class CreateMessageResult(BaseResult, SamplingMessage): # Inherits role and content
    model: str
    stopReason: Optional[Literal["endTurn", "stopSequence", "maxTokens", "string"]] = None # string for custom reasons


class Root(BaseModel):
    uri: AnyHttpUrl # Must start with file:// for now
    name: Optional[str] = None
    _meta: Optional[Dict[str, Any]] = None


class ListRootsResult(BaseResult):
    roots: List[Root]


class ElicitResult(BaseResult):
    action: Literal["accept", "decline", "cancel"]
    content: Optional[Dict[str, Union[str, int, float, bool]]] = None # Updated to allow numbers


class CompleteResultData(BaseModel):
    values: List[str]
    total: Optional[int] = None
    hasMore: Optional[bool] = None


class CompleteResult(BaseResult):
    completion: CompleteResultData


ClientResult = Union[
    EmptyResult,
    CreateMessageResult,
    ListRootsResult,
    ElicitResult,
]

ServerResult = Union[
    EmptyResult,
    InitializeResult,
    CompleteResult,
    GetPromptResult,
    ListPromptsResult,
    ListResourceTemplatesResult,
    ListResourcesResult,
    ReadResourceResult,
    CallToolResult,
    ListToolsResult,
]

# For results from server to client
MCPResponse = ServerResult
# For results from client to server (not commonly used directly by this name)
# MCPClientResponse = ClientResult


# Helper function (optional, depending on usage)
def create_jsonrpc_response(
    result_model: Union[ClientResult, ServerResult], request_id: RequestId
) -> JSONRPCResponse:
    return JSONRPCResponse(id=request_id, result=result_model)

def create_jsonrpc_error_response(
    code: int, message: str, request_id: RequestId, data: Optional[Any] = None
) -> JSONRPCErrorResponse:
    error_obj = {"code": code, "message": message}
    if data is not None:
        error_obj["data"] = data
    return JSONRPCErrorResponse(id=request_id, error=error_obj)


# For partial/streaming responses, MCP doesn't define a specific JSON-RPC structure.
# Streaming is usually handled by a series of `notifications/progress` or
# custom notifications. The existing MCPPartialResponse might need to be
# re-evaluated in the context of JSON-RPC notifications.
# For now, we'll keep it, but it might not be directly used with JSONRPCResponse.
class MCPPartialResponse(BaseModel):
    """
    Represents a piece of a streaming response.
    This is NOT a standard JSON-RPC message type but retained from previous structure.
    It would typically be part of a `notifications/progress` `params` or a custom notification.
    """
    partial_text: Optional[str] = None # Made optional as not all streams are text
    data_chunk: Optional[Any] = None # For more generic streaming data
    is_final_chunk: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None # If a stream encounters an error

    # Example of how it might be used in a progress notification's params
    # class StreamingProgressParams(ProgressNotificationParams):
    #     chunk: 'MCPPartialResponse' # Forward reference
