from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_http import configured,client
from tests.test_validation import lab
from tests.test_goal_retests import (
    test_goal_retest_origin_is_pending_idempotent_replanned_and_persisted_with_result as test_native_goal_retest_origin,
    test_goal_retest_requires_matching_source_proof_and_operator as test_native_goal_retest_proof,
    test_goal_retest_final_write_checks_origin_and_rolls_back as test_native_goal_retest_atomic,
    test_goal_retest_origin_tampering_refuses_approval as test_native_goal_retest_tamper,
)


def test_native_goal_retest_application_restart(configured,lab,monkeypatch):
    from tests.test_goal_retests import restart_goal_retest
    restart_goal_retest(configured[1],lab,monkeypatch)
