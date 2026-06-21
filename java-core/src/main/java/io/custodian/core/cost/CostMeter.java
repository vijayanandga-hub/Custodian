package io.custodian.core.cost;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.DoubleAdder;

/**
 * Per-tenant token-cost accounting. Every assessment carries a cost record from
 * the AI plane; this aggregates spend so FinOps governance has a live view and
 * budget ceilings can be enforced.
 */
public final class CostMeter {

    private final ConcurrentHashMap<String, DoubleAdder> spendByTenant = new ConcurrentHashMap<>();

    public void record(String tenantId, double costUsd) {
        spendByTenant.computeIfAbsent(tenantId, k -> new DoubleAdder()).add(costUsd);
    }

    public double spend(String tenantId) {
        DoubleAdder a = spendByTenant.get(tenantId);
        return a == null ? 0.0 : a.sum();
    }

    public boolean withinBudget(String tenantId, double ceilingUsd) {
        return spend(tenantId) <= ceilingUsd;
    }
}
