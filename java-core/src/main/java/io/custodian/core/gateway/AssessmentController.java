package io.custodian.core.gateway;

import io.custodian.core.governance.AssessmentOrchestrator;
import io.custodian.core.governance.AssessmentResponse;
import org.springframework.web.bind.annotation.*;

/**
 * Control-plane entry point. The Java core owns the request; it calls the Python
 * AI plane, enforces governance, and never lets a recommendation auto-commit.
 */
@RestController
@RequestMapping("/api/assessments")
public class AssessmentController {

    private final AssessmentOrchestrator orchestrator;

    public AssessmentController(AssessmentOrchestrator orchestrator) {
        this.orchestrator = orchestrator;
    }

    @PostMapping
    public AssessmentResponse assess(@RequestHeader("X-Tenant-Id") String tenantId,
                                     @RequestBody AssessmentRequest request) {
        return orchestrator.assess(tenantId, request.componentDescription());
    }

    @PostMapping("/{correlationId}/approve")
    public AssessmentResponse approve(@PathVariable String correlationId,
                                      @RequestHeader("X-Approver-Id") String approverId) {
        return orchestrator.approve(correlationId, approverId);
    }

    public record AssessmentRequest(String componentDescription) {}
}
