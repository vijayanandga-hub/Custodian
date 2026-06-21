package io.custodian.core.approval;

/**
 * Governs the lifecycle of a modernization recommendation. Nothing reaches
 * COMMITTED without passing through APPROVED, and when the AI plane flags
 * needsHumanApproval, APPROVED is only reachable by an explicit human action.
 * This is the control that makes the agent safe to run in a regulated institution.
 */
public final class ApprovalStateMachine {

    public enum State { DRAFTED, PENDING_APPROVAL, APPROVED, REJECTED, COMMITTED }

    private State state = State.DRAFTED;

    /** Called after the AI plane returns. High-risk -> requires a human. */
    public void onAssessmentComplete(boolean needsHumanApproval) {
        require(State.DRAFTED);
        state = needsHumanApproval ? State.PENDING_APPROVAL : State.APPROVED;
    }

    /** Human approver action. Only valid from PENDING_APPROVAL. */
    public void approve(String approverId) {
        require(State.PENDING_APPROVAL);
        if (approverId == null || approverId.isBlank()) {
            throw new IllegalArgumentException("approverId required for audit");
        }
        state = State.APPROVED;
    }

    public void reject(String approverId, String reason) {
        require(State.PENDING_APPROVAL);
        state = State.REJECTED;
    }

    /** Commit is the only side-effecting transition and demands APPROVED. */
    public void commit() {
        require(State.APPROVED);
        state = State.COMMITTED;
    }

    public State current() {
        return state;
    }

    private void require(State expected) {
        if (state != expected) {
            throw new IllegalStateException(
                "Illegal transition from " + state + "; expected " + expected);
        }
    }
}
