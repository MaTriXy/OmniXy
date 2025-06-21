# Security & Privacy

This document outlines the security measures and best practices for the OmniXy project.

## Credentials & Authentication

### Provider Credentials

- Store provider API keys in a secure vault (e.g., HashiCorp Vault, AWS Secrets Manager)
- Support environment variables with proper encryption
- Rotate credentials regularly
- Use separate credentials for development/staging/production

### Plugin Authentication

- Implement plugin signature verification
- Use secure token-based authentication for plugin communication
- Validate plugin sources and maintainers

## Data Protection

### Request/Response Security

- Use HTTPS/TLS 1.3+ for all remote calls
- Implement request signing for integrity
- Enable response verification

### PII Handling

- Implement PII detection and anonymization
- Support data masking plugins
- Provide audit trails for PII access

### Data Storage

- Encrypt data at rest
- Implement proper data retention policies
- Support secure data deletion

## Workflow Security

### Access Control

- Implement role-based access control (RBAC) for workflows
- Support workflow-level permissions
- Enable audit logging for workflow access

### State Management

- Secure storage of workflow state
- Encrypt sensitive workflow data
- Implement state validation

### Resource Protection

- Set resource usage limits per workflow
- Implement timeout mechanisms
- Monitor resource consumption

## Plugin Security

### Sandbox Execution

- Run plugins in isolated environments
- Implement resource quotas
- Monitor plugin behavior

### Code Security

- Verify plugin code integrity
- Scan for vulnerabilities
- Enforce secure coding practices

### Plugin Updates

- Implement secure update mechanisms
- Verify plugin signatures
- Support rollback capabilities

## Rate Limiting & Quotas

### Provider Limits

- Enforce per-provider rate limits
- Implement token usage quotas
- Monitor API usage patterns

### User Limits

- Set per-user request limits
- Implement cost control measures
- Support usage notifications

## Audit & Monitoring

### Logging

- Log all security-relevant events
- Implement secure log storage
- Support log analysis tools

### Metrics

- Track security-related metrics
- Monitor for anomalies
- Generate security reports

### Alerts

- Set up security alert thresholds
- Implement incident response
- Support automated remediation

## CI/CD Security

### Build Security

- Scan dependencies for vulnerabilities
- Verify build artifacts
- Implement secure build processes

### Deployment Security

- Use secure deployment practices
- Implement deployment verification
- Support rollback procedures

### Testing

- Run security tests in CI/CD
- Perform regular security scans
- Validate security controls

## Compliance

### Standards

- Follow security best practices
- Implement compliance requirements
- Support audit processes

### Documentation

- Maintain security documentation
- Document incident responses
- Keep compliance records

## Model Context Protocol (MCP) Alignment (v2025-06-18)

The Model Context Protocol specification includes important Security and Trust & Safety guidelines that implementors MUST consider. This system, when acting as an MCP host (e.g., receiving requests to its `MCPLayer`) or as an MCP client (e.g., using `MCPConnection` to talk to an external MCP server), relies on the integrating application to manage and enforce several key principles at the user interface and application logic level.

### Key MCP Security Principles & Responsibilities

1.  **User Consent and Control**:
    *   **Responsibility**: The integrating application (Host) is responsible for obtaining explicit user consent before:
        *   Accessing any user data or resources (e.g., via `resources/read` initiated by an external server, or before providing local data to a driver).
        *   Performing any action or operation (e.g., calling a tool via `tools/call`, whether the tool is local like GitHubDriver or on an external MCP server).
        *   Initiating LLM sampling if requested by an external server (`sampling/createMessage`).
    *   The backend (this library) provides the mechanisms for these operations but does not implement the UI/UX for consent. Placeholders (`logger.info` calls with `MCP_LAYER_SECURITY_CHECK` or `MCP_CONNECTION_SECURITY_CHECK`) are included in the code to indicate where such checks are critical.

2.  **Data Privacy**:
    *   **Responsibility**: The Host application must manage user consent for data exposure.
    *   This library aims to pass data to the intended drivers or external MCP servers as directed by the Host, assuming consent has been handled.
    *   Care should be taken by the Host not to inadvertently log or expose sensitive data that might be part of MCP requests/responses.

3.  **Tool Safety**:
    *   **Responsibility**: The Host application MUST obtain explicit user consent before invoking any tool, whether it's a local capability exposed via a driver (e.g., `GitHubDriver` actions) or a tool on an external MCP server.
    *   Descriptions and annotations for tools coming from *untrusted external MCP servers* SHOULD NOT be trusted implicitly by the Host application when presenting them to the user.

4.  **LLM Sampling Controls** (Client-side LLM calls requested by a server):
    *   **Responsibility**: If this system were to act as an MCP client that exposes an LLM to an external MCP server (via `sampling/createMessage` *requests from the server*), the Host application would be responsible for:
        *   Obtaining user approval before sampling.
        *   Allowing user control over the actual prompt sent to the LLM.
        *   Allowing user control over what results are shared back with the requesting MCP server.
    *   Currently, the `MCPLayer` primarily initiates requests *to* LLM drivers, not typically handling incoming `sampling/createMessage` requests from an external server. If this changes, these controls become critical.

### Implementation Notes in This Library

*   **API Keys & Credentials**: Provider API keys (OpenAI, Cohere, GitHub, etc.) are managed via configuration passed to drivers. The security of these keys (e.g., using environment variables, secure vault integration) is the responsibility of the deploying application.
*   **Logging**: While some security-related logging placeholders have been added, the overall logging strategy (e.g., log levels, redaction of sensitive data in logs) should be configured by the deploying application.
*   **Input Validation**: Pydantic models provide data validation at the MCP message structure level. However, the *content* of fields (e.g., prompts, tool arguments) should be sanitized or validated by the Host application as appropriate, especially if it originates from untrusted sources.

The integrating application (OmniXy or any other system using this MCP library) MUST prioritize these security principles and implement the necessary user-facing controls and application-level logic to comply with the MCP specification's trust and safety guidelines.
