package io.custodian.core.governance;

/** What the control plane returns to the caller. */
public record AssessmentResponse(
        String correlationId,
        String state,
        boolean needsHumanApproval,
        double totalCostUsd,
        String recommendationJson) {}
