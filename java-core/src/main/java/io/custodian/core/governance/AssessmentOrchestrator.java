package io.custodian.core.governance;

import io.custodian.core.approval.ApprovalStateMachine;
import io.custodian.core.audit.AuditEvent;
import io.custodian.core.audit.AuditLog;
import io.custodian.core.cost.CostMeter;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Orchestrates one assessment: call the AI plane, meter cost, write the audit
 * trail, and drive the approval state machine. The governance the project is
 * actually demonstrating lives here.
 */
@Service
public class AssessmentOrchestrator {

    private final AiPlaneClient aiPlane;
    private final AuditLog auditLog = new AuditLog();
    private final CostMeter costMeter = new CostMeter();
    private final Map<String, ApprovalStateMachine> machines = new ConcurrentHashMap<>();
    private final Map<String, String> recommendations = new ConcurrentHashMap<>();
    private final Map<String, String> tenants = new ConcurrentHashMap<>();

    public AssessmentOrchestrator(AiPlaneClient aiPlane) {
        this.aiPlane = aiPlane;
    }

    @SuppressWarnings("unchecked")
    public AssessmentResponse assess(String tenantId, String componentDescription) {
        String correlationId = UUID.randomUUID().toString();
        Map<String, Object> ai = aiPlane.assess(componentDescription);

        double cost = ((Number) ai.getOrDefault("total_cost_usd", 0.0)).doubleValue();
        boolean needsApproval = Boolean.TRUE.equals(ai.get("needs_human_approval"));
        costMeter.record(tenantId, cost);

        // Audit every step the agent reported.
        for (Map<String, Object> step : (java.util.List<Map<String, Object>>)
                ai.getOrDefault("steps", java.util.List.of())) {
            Map<String, Object> routing = (Map<String, Object>) step.getOrDefault("routing", Map.of());
            auditLog.append(AuditEvent.of(correlationId, tenantId,
                    "agent_step:" + step.get("step"), "",
                    String.valueOf(routing.get("provider")),
                    String.valueOf(routing.get("model")),
                    ((Number) step.getOrDefault("cost_usd", 0.0)).doubleValue()));
        }

        ApprovalStateMachine sm = new ApprovalStateMachine();
        sm.onAssessmentComplete(needsApproval);
        machines.put(correlationId, sm);
        recommendations.put(correlationId, String.valueOf(ai.get("recommendation")));
        tenants.put(correlationId, tenantId);

        auditLog.append(AuditEvent.of(correlationId, tenantId, "state:" + sm.current(),
                "needsApproval=" + needsApproval, "-", "-", 0.0));

        return new AssessmentResponse(correlationId, sm.current().name(), needsApproval,
                costMeter.spend(tenantId), recommendations.get(correlationId));
    }

    public AssessmentResponse approve(String correlationId, String approverId) {
        ApprovalStateMachine sm = machines.get(correlationId);
        if (sm == null) throw new IllegalArgumentException("Unknown correlationId");
        sm.approve(approverId);
        String tenantId = tenants.get(correlationId);
        auditLog.append(AuditEvent.of(correlationId, tenantId, "human_approval",
                "approver=" + approverId, "-", "-", 0.0));
        sm.commit();
        auditLog.append(AuditEvent.of(correlationId, tenantId, "state:COMMITTED",
                "", "-", "-", 0.0));
        return new AssessmentResponse(correlationId, sm.current().name(), false,
                costMeter.spend(tenantId), recommendations.get(correlationId));
    }
}
