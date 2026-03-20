# ADR-0007: MCP Connector Allowlist Governance

## Status

Accepted

## Context

Task #64 implemented the MCP Connector Interface with basic allowlist support via in-memory `set_allowlist()` method. However, the current implementation has several gaps:

1. **No external configuration**: Allowlist is stored in memory only, requiring code changes to update
2. **No validation layer**: No dedicated validator class with structured validation logic
3. **No admin API**: No runtime allowlist management capabilities
4. **No audit logging**: No compliance logging for allowlist violations
5. **No documentation**: No governance policy documentation

This creates operational challenges:
- Difficulty managing CE vs PRO connector access
- No visibility into which connectors are allowed in CE
- No audit trail for compliance
- Requires code deployment to change allowlist

## Decision

We will implement a comprehensive allowlist governance system with:

1. **YAML Configuration File** (`config/mcp_allowlist.yaml`)
   - External, editable configuration
   - Support for allowlist and restricted connectors
   - Metadata for documentation

2. **AllowlistValidator Class** (`mcp/allowlist_validator.py`)
   - Structured validation logic
   - YAML parsing with error handling
   - Environment variable fallback
   - Audit logging for violations

3. **Admin API** (`api/routers/mcp_admin.py`)
   - GET `/api/v1/mcp/allowlist` - List current allowlist
   - POST `/api/v1/mcp/allowlist` - Add connector
   - DELETE `/api/v1/mcp/allowlist/{name}` - Remove connector
   - GET `/api/v1/mcp/allowlist/violations` - Audit log
   - POST `/api/v1/mcp/allowlist/reload` - Reload from YAML
   - GET `/api/v1/mcp/connectors` - List all connectors
   - GET `/api/v1/mcp/health` - Health check

4. **Integration with Registry**
   - Registry uses AllowlistValidator for all checks
   - Violations logged automatically
   - Configuration reloadable at runtime

## Consequences

**Positive:**
- External configuration management (no code changes needed)
- Full audit trail for compliance
- Runtime allowlist management via API
- Better separation of concerns
- Testable validation logic

**Negative:**
- Additional YAML file to maintain
- Slight performance overhead from validator
- More complex startup sequence

## Alternatives Considered

1. **Database-stored allowlist**
   - Rejected: Overkill for static configuration
   - YAML is simpler and version-controllable

2. **Environment variables only**
   - Rejected: Too complex with many connectors
   - No structured metadata support
   - Difficult to manage

3. **Hard-coded allowlist**
   - Rejected: Current approach being improved
   - Requires code changes for every update

## Implementation Details

### YAML Configuration Schema

```yaml
edition: community  # Current edition
allowlist:
  - name: connector_name
    display_name: Human Name
    description: Purpose
    enabled: true
    edition: community
restricted:
  - name: pro_connector
    display_name: Pro Feature
    min_edition: pro
metadata:
  version: "1.0.0"
  last_updated: "2024-03-20"
```

### Validation Flow

```
Request → Registry.get_connector()
         ↓
         AllowlistValidator.validate_connector()
         ↓
         If CE edition and not allowlisted:
           → Log violation
           → Raise MCPNotAllowlistedError
         ↓
         Return connector instance
```

### Audit Log Format

```json
{
  "timestamp": "2024-03-20T10:30:00Z",
  "connector": "stripe",
  "operation": "get_connector",
  "context": {"edition": "community"},
  "config_edition": "community"
}
```

## Security Considerations

1. **Admin API Access**: Requires API key authentication
2. **Audit Trail**: All violations logged with timestamp
3. **No PII**: Only connector names and operation context logged
4. **Runtime Safety**: Changes to in-memory only, YAML requires explicit reload

## Migration Path

Existing `set_allowlist()` calls continue to work but are enhanced:
- Also updates AllowlistValidator
- Violations still logged

No breaking changes - backward compatible.

## References

- ADR-0005: MCP Live Data Layer (foundation)
- Task #64: MCP Connector Interface (implementation)
- Task #68: MCP Allowlist Governance (this task)
