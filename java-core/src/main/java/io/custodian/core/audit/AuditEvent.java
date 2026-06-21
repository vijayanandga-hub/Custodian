package io.custodian.core.audit;

import java.time.Instant;

/** Immutable audit record. One emitted per agent step and per state transition. */
public record AuditEvent(
        String correlationId,
        String tenantId,
        String action,
        String detail,
        String provider,
        String model,
        double costUsd,
        Instant timestamp) {

    public static AuditEvent of(String correlationId, String tenantId, String action,
                                String detail, String provider, String model, double costUsd) {
        return new AuditEvent(correlationId, tenantId, action, detail, provider, model,
                costUsd, Instant.now());
    }
}
