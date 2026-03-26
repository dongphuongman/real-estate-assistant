# Risk Assessment Matrix Template

## Risk Matrix Visualization

```
                    IMPACT
              LOW    MED    HIGH   CRIT
         ┌────────┬────────┬────────┬────────┐
    LOW  │   ✓    │   ⚡   │   ⚡   │   ⚡   │
         ├────────┼────────┼────────┼────────┤
P   MED  │   ✓    │   ⚡   │   ⚠️   │   ⚠️   │
R        ├────────┼────────┼────────┼────────┤
O   HIGH │   ⚡    │   ⚠️   │   🚨  │   🚨  │
B        ├────────┼────────┼────────┼────────┤
    CRIT │   ⚡    │   ⚠️   │   🚨  │   🚨  │
         └────────┴────────┴────────┴────────┘

Legend:
  ✓ = Low risk (acceptable)
  ⚡ = Medium risk (monitor)
  ⚠️ = High risk (mitigate)
  🚨 = Critical risk (block)
```

## Risk Register

| ID | Description | Category | Probability | Impact | Risk Level | Mitigation | Contingency | Owner | Status |
|----|-------------|----------|-------------|--------|------------|------------|-------------|-------|--------|
| R001 | [Risk description] | Technical | Medium | High | High | [How to prevent] | [Plan B if it happens] | [Owner] | Identified |
| R002 | [Risk description] | Security | Low | Critical | High | [How to prevent] | [Plan B if it happens] | [Owner] | Mitigating |
| R003 | [Risk description] | Performance | High | Medium | High | [How to prevent] | [Plan B if it happens] | [Owner] | Monitoring |

## Risk Categories

- **Technical:** Architecture, dependencies, integration issues
- **Security:** Vulnerabilities, data breaches, authentication failures
- **Performance:** Scalability, response times, resource limits
- **Business:** Requirements changes, stakeholder alignment, timeline
- **Operational:** Deployment, monitoring, incident response
- **Compliance:** Regulatory, privacy, licensing
- **Third-Party:** External APIs, vendor reliability, service changes
- **Resource:** Team availability, skill gaps, budget constraints

## Risk Status Definitions

- **Identified:** Risk has been documented but not yet analyzed
- **Analyzing:** Risk is being assessed for probability and impact
- **Mitigating:** Actions are being taken to reduce the risk
- **Monitoring:** Risk is being tracked, mitigation in place
- **Resolved:** Risk has been eliminated or reduced to acceptable level
- **Accepted:** Risk is acknowledged and accepted without mitigation

## Risk Scoring Guide

### Probability Levels
| Level | Score | Description |
|-------|-------|-------------|
| Low | 1 | Unlikely to occur (< 10% chance) |
| Medium | 2 | May occur (10-50% chance) |
| High | 3 | Likely to occur (50-80% chance) |
| Critical | 4 | Almost certain (> 80% chance) |

### Impact Levels
| Level | Score | Description |
|-------|-------|-------------|
| Low | 1 | Minor inconvenience, easy workaround |
| Medium | 2 | Moderate impact, some functionality affected |
| High | 3 | Major impact, significant functionality blocked |
| Critical | 4 | Severe impact, system unusable or data loss |

### Risk Score Calculation
```
Risk Score = Probability Score × Impact Score

Score 1-3:   Low Risk (✓)
Score 4-6:   Medium Risk (⚡)
Score 8-9:   High Risk (⚠️)
Score 12-16: Critical Risk (🚨)
```

## Mitigation Strategies

### For Each Risk, Document:
1. **Avoidance:** Can we eliminate the risk entirely?
2. **Reduction:** How can we reduce probability or impact?
3. **Transfer:** Can we transfer the risk (insurance, vendor)?
4. **Acceptance:** Is the risk acceptable without action?

### Mitigation Plan Template
```markdown
## Risk: [R001] - [Short Title]

**Description:** [Detailed description]

**Probability:** [Low/Medium/High/Critical]
**Impact:** [Low/Medium/High/Critical]
**Risk Level:** [Low/Medium/High/Critical]

**Trigger:** [What conditions would cause this risk to materialize]

**Mitigation Plan:**
1. [Action 1]
2. [Action 2]
3. [Action 3]

**Contingency Plan:**
If this risk materializes:
1. [Immediate action 1]
2. [Immediate action 2]

**Owner:** [Name/Team]
**Review Date:** [Date]
**Status:** [Status]

**Notes:**
- [Note 1]
- [Note 2]
```

---

*Template Version: 1.0.0*
