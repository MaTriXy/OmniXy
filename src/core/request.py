from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, AnyHttpUrl

JSONRPC_VERSION = "2.0"
LATEST_PROTOCOL_VERSION = "2025-06-18"

ProgressToken = Union[str, int]
Cursor = str
RequestId = Union[str, int]
Role = Literal["user", "assistant"]


class BaseMetadata(BaseModel):
    name: str = Field(
        ...,
        description="Intended for programmatic or logical use, but used as a display name in past specs or fallback (if title isn't present).",
    )
    title: Optional[str] = Field(
        None,
        description="Intended for UI and end-user contexts — optimized to be human-readable and easily understood, even by those unfamiliar with domain-specific terminology.",
    )


class Implementation(BaseMetadata):
    version: str


class RequestMeta(BaseModel):
    progressToken: Optional[ProgressToken] = Field(
        None,
        description="If specified, the caller is requesting out-of-band progress notifications for this request.",
    )
    # Allows arbitrary keys
    model_config = {"extra": "allow"}


class RequestParams(BaseModel):
    _meta: Optional[RequestMeta] = None
    # Allows arbitrary keys
    model_config = {"extra": "allow"}


class BaseRequest(BaseModel):
    method: str
    params: Optional[RequestParams] = None


class JSONRPCRequest(BaseRequest):
    jsonrpc: str = Field(default=JSONRPC_VERSION, frozen=True)
    id: RequestId


class ClientCapabilities(BaseModel):
    experimental: Optional[Dict[str, Any]] = None
    roots: Optional[Dict[str, bool]] = None
    sampling: Optional[Dict[str, Any]] = None
    elicitation: Optional[Dict[str, Any]] = None


class InitializeRequestParams(RequestParams):
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation


class InitializeRequest(BaseRequest):
    method: Literal["initialize"] = "initialize"
    params: InitializeRequestParams


class PingRequest(BaseRequest):
    method: Literal["ping"] = "ping"


class PaginatedRequestParams(RequestParams):
    cursor: Optional[Cursor] = None


class PaginatedRequest(BaseRequest):
    params: Optional[PaginatedRequestParams] = None


class ListResourcesRequest(PaginatedRequest):
    method: Literal["resources/list"] = "resources/list"


class ListResourceTemplatesRequest(PaginatedRequest):
    method: Literal["resources/templates/list"] = "resources/templates/list"


class ReadResourceRequestParams(RequestParams):
    uri: AnyHttpUrl


class ReadResourceRequest(BaseRequest):
    method: Literal["resources/read"] = "resources/read"
    params: ReadResourceRequestParams


class SubscribeRequestParams(RequestParams):
    uri: AnyHttpUrl


class SubscribeRequest(BaseRequest):
    method: Literal["resources/subscribe"] = "resources/subscribe"
    params: SubscribeRequestParams


class UnsubscribeRequestParams(RequestParams):
    uri: AnyHttpUrl


class UnsubscribeRequest(BaseRequest):
    method: Literal["resources/unsubscribe"] = "resources/unsubscribe"
    params: UnsubscribeRequestParams


class ListPromptsRequest(PaginatedRequest):
    method: Literal["prompts/list"] = "prompts/list"


class GetPromptRequestParams(RequestParams):
    name: str
    arguments: Optional[Dict[str, str]] = None


class GetPromptRequest(BaseRequest):
    method: Literal["prompts/get"] = "prompts/get"
    params: GetPromptRequestParams


class ListToolsRequest(PaginatedRequest):
    method: Literal["tools/list"] = "tools/list"


class CallToolRequestParams(RequestParams):
    name: str
    arguments: Optional[Dict[str, Any]] = None


class CallToolRequest(BaseRequest):
    method: Literal["tools/call"] = "tools/call"
    params: CallToolRequestParams


class SetLevelRequestParams(RequestParams):
    level: Literal[
        "debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"
    ]


class SetLevelRequest(BaseRequest):
    method: Literal["logging/setLevel"] = "logging/setLevel"
    params: SetLevelRequestParams


class Annotations(BaseModel):
    audience: Optional[List[Role]] = None
    priority: Optional[float] = Field(None, ge=0, le=1)
    lastModified: Optional[str] = None # Ideally, this would be datetime, but schema uses string


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str
    annotations: Optional[Annotations] = None
    _meta: Optional[Dict[str, Any]] = None


class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    data: str  # Base64 encoded
    mimeType: str
    annotations: Optional[Annotations] = None
    _meta: Optional[Dict[str, Any]] = None


class AudioContent(BaseModel):
    type: Literal["audio"] = "audio"
    data: str  # Base64 encoded
    mimeType: str
    annotations: Optional[Annotations] = None
    _meta: Optional[Dict[str, Any]] = None


Content = Union[TextContent, ImageContent, AudioContent]


class SamplingMessage(BaseModel):
    role: Role
    content: Content


class ModelHint(BaseModel):
    name: Optional[str] = None


class ModelPreferences(BaseModel):
    hints: Optional[List[ModelHint]] = None
    costPriority: Optional[float] = Field(None, ge=0, le=1)
    speedPriority: Optional[float] = Field(None, ge=0, le=1)
    intelligencePriority: Optional[float] = Field(None, ge=0, le=1)


class CreateMessageRequestParams(RequestParams):
    messages: List[SamplingMessage]
    modelPreferences: Optional[ModelPreferences] = None
    systemPrompt: Optional[str] = None
    includeContext: Optional[Literal["none", "thisServer", "allServers"]] = None
    temperature: Optional[float] = None
    maxTokens: int
    stopSequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateMessageRequest(BaseRequest):
    method: Literal["sampling/createMessage"] = "sampling/createMessage"
    params: CreateMessageRequestParams


class ListRootsRequest(BaseRequest):
    method: Literal["roots/list"] = "roots/list"


class PrimitiveSchemaDefinition(BaseModel):
    type: Literal["string", "number", "integer", "boolean"]
    title: Optional[str] = None
    description: Optional[str] = None
    minLength: Optional[int] = None
    maxLength: Optional[int] = None
    format: Optional[Literal["email", "uri", "date", "date-time"]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    default: Optional[bool] = None
    enum: Optional[List[str]] = None
    enumNames: Optional[List[str]] = None


class ElicitRequestParams(RequestParams):
    message: str
    requestedSchema: Dict[str, PrimitiveSchemaDefinition] = Field(
        ..., alias="requestedSchema"
    )

    class Config:
        populate_by_name = True


class ElicitRequest(BaseRequest):
    method: Literal["elicitation/create"] = "elicitation/create"
    params: ElicitRequestParams


class PromptReference(BaseMetadata):
    type: Literal["ref/prompt"] = "ref/prompt"


class ResourceTemplateReference(BaseModel):
    type: Literal["ref/resource"] = "ref/resource"
    uri: str # uri-template


class CompleteRequestParams(RequestParams):
    ref: Union[PromptReference, ResourceTemplateReference]
    argument: Dict[str, str] # name and value
    context: Optional[Dict[str, Any]] = None


class CompleteRequest(BaseRequest):
    method: Literal["completion/complete"] = "completion/complete"
    params: CompleteRequestParams


ClientRequest = Union[
    PingRequest,
    InitializeRequest,
    CompleteRequest,
    SetLevelRequest,
    GetPromptRequest,
    ListPromptsRequest,
    ListResourcesRequest,
    ListResourceTemplatesRequest,
    ReadResourceRequest,
    SubscribeRequest,
    UnsubscribeRequest,
    CallToolRequest,
    ListToolsRequest,
]

ServerRequest = Union[
    PingRequest,
    CreateMessageRequest,
    ListRootsRequest,
    ElicitRequest,
]

# For requests that are sent from client to server
MCPRequest = ClientRequest
# For requests that are sent from server to client (not commonly used directly by this name)
# MCPClientOriginatedRequest = ServerRequest


# Notification specific models
class BaseNotification(BaseModel):
    method: str
    params: Optional[Dict[str, Any]] = None # Simplified for now, can be more specific


class JSONRPCNotification(BaseNotification):
    jsonrpc: str = Field(default=JSONRPC_VERSION, frozen=True)


class CancelledNotificationParams(BaseModel):
    requestId: RequestId
    reason: Optional[str] = None


class CancelledNotification(BaseNotification):
    method: Literal["notifications/cancelled"] = "notifications/cancelled"
    params: CancelledNotificationParams


class InitializedNotification(BaseNotification):
    method: Literal["notifications/initialized"] = "notifications/initialized"
    # No params for InitializedNotification


class ProgressNotificationParams(BaseModel):
    progressToken: ProgressToken
    progress: float # Using float to accommodate number type in schema
    total: Optional[float] = None
    message: Optional[str] = None


class ProgressNotification(BaseNotification):
    method: Literal["notifications/progress"] = "notifications/progress"
    params: ProgressNotificationParams


class ResourceListChangedNotification(BaseNotification):
    method: Literal["notifications/resources/list_changed"] = (
        "notifications/resources/list_changed"
    )


class ResourceUpdatedNotificationParams(BaseModel):
    uri: AnyHttpUrl


class ResourceUpdatedNotification(BaseNotification):
    method: Literal["notifications/resources/updated"] = "notifications/resources/updated"
    params: ResourceUpdatedNotificationParams


class PromptListChangedNotification(BaseNotification):
    method: Literal["notifications/prompts/list_changed"] = (
        "notifications/prompts/list_changed"
    )


class ToolListChangedNotification(BaseNotification):
    method: Literal["notifications/tools/list_changed"] = "notifications/tools/list_changed"


class LoggingMessageNotificationParams(BaseModel):
    level: Literal[
        "debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"
    ]
    logger: Optional[str] = None
    data: Any


class LoggingMessageNotification(BaseNotification):
    method: Literal["notifications/message"] = "notifications/message"
    params: LoggingMessageNotificationParams


class RootsListChangedNotification(BaseNotification):
    method: Literal["notifications/roots/list_changed"] = (
        "notifications/roots/list_changed"
    )


ClientNotification = Union[
    CancelledNotification,
    ProgressNotification,
    InitializedNotification,
    RootsListChangedNotification,
]

ServerNotification = Union[
    CancelledNotification,
    ProgressNotification,
    LoggingMessageNotification,
    ResourceUpdatedNotification,
    ResourceListChangedNotification,
    ToolListChangedNotification,
    PromptListChangedNotification,
]

# Generic MCP Notification for use in the application layer
MCPNotification = Union[ClientNotification, ServerNotification]


# Helper functions (optional, depending on usage)
def create_jsonrpc_request(
    request_model: Union[ClientRequest, ServerRequest], request_id: RequestId
) -> JSONRPCRequest:
    return JSONRPCRequest(
        id=request_id, method=request_model.method, params=request_model.params
    )


def create_jsonrpc_notification(
    notification_model: MCPNotification,
) -> JSONRPCNotification:
    return JSONRPCNotification(
        method=notification_model.method, params=notification_model.params
    )
