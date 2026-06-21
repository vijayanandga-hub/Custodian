package io.custodian.core.audit;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Append-only audit store. In production this is a write-once persistence layer
 * (e.g. immutable table / WORM store). Append-only here too: no update, no delete.
 */
public final class AuditLog {

    private final List<AuditEvent> events = new CopyOnWriteArrayList<>();

    public void append(AuditEvent event) {
        events.add(event);
    }

    public List<AuditEvent> forCorrelation(String correlationId) {
        return events.stream().filter(e -> e.correlationId().equals(correlationId)).toList();
    }

    public List<AuditEvent> all() {
        return List.copyOf(events);
    }
}
