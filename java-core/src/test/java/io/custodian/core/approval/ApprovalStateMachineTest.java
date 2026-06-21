package io.custodian.core.approval;

import io.custodian.core.approval.ApprovalStateMachine.State;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The governance guarantee in executable form: a high-risk recommendation can
 * NEVER reach COMMITTED without an explicit, named human approval. These tests
 * are the proof an interviewer can run.
 */
class ApprovalStateMachineTest {

    @Test
    void highRisk_cannotCommit_withoutHumanApproval() {
        ApprovalStateMachine sm = new ApprovalStateMachine();
        sm.onAssessmentComplete(true); // high risk -> PENDING_APPROVAL
        assertEquals(State.PENDING_APPROVAL, sm.current());

        // Attempting to commit before approval must fail.
        assertThrows(IllegalStateException.class, sm::commit);
        assertEquals(State.PENDING_APPROVAL, sm.current());
    }

    @Test
    void highRisk_commits_onlyAfterNamedHumanApproves() {
        ApprovalStateMachine sm = new ApprovalStateMachine();
        sm.onAssessmentComplete(true);

        sm.approve("jane.architect");
        assertEquals(State.APPROVED, sm.current());

        sm.commit();
        assertEquals(State.COMMITTED, sm.current());
    }

    @Test
    void approve_requiresNonBlankApproverId_forAudit() {
        ApprovalStateMachine sm = new ApprovalStateMachine();
        sm.onAssessmentComplete(true);

        assertThrows(IllegalArgumentException.class, () -> sm.approve("  "));
        assertEquals(State.PENDING_APPROVAL, sm.current());
    }

    @Test
    void lowRisk_autoApproves_butStillRequiresExplicitCommit() {
        ApprovalStateMachine sm = new ApprovalStateMachine();
        sm.onAssessmentComplete(false); // low risk -> APPROVED, no human needed
        assertEquals(State.APPROVED, sm.current());

        sm.commit();
        assertEquals(State.COMMITTED, sm.current());
    }

    @Test
    void rejectedRecommendation_canNeverCommit() {
        ApprovalStateMachine sm = new ApprovalStateMachine();
        sm.onAssessmentComplete(true);

        sm.reject("jane.architect", "Migration sequence unsafe");
        assertEquals(State.REJECTED, sm.current());
        assertThrows(IllegalStateException.class, sm::commit);
    }
}
