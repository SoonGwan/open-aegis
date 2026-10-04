"""Durable event planner contracts over actual native PostgreSQL."""
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_http import configured,client
from tests.test_validation import lab
from tests.test_event_planner import (
    test_automatic_terminal_and_human_events_prepare_without_query_or_execution as test_native_automatic_events,
    test_stale_saved_review_cannot_authorize_and_drain_refreshes_it as test_native_stale_review,
    test_proposal_and_event_position_roll_back_together_then_replay as test_native_atomic_cursor,
    test_asset_fanout_is_paged_and_resumes_in_new_processor as test_native_paged_resume,
    test_corrupt_family_is_blocked_without_poisoning_later_events as test_native_bad_lineage,
    test_policy_change_replays_committed_events_without_execution as test_native_policy_replay,
    test_root_todo_event_reaches_current_terminal_followup as test_native_root_event,
    test_missing_and_corrupt_cache_do_not_fabricate_a_proposal as test_native_bad_cache,
)
from tests.test_event_planner import test_actual_server_restart_consumes_unprocessed_human_event as actual_restart

def test_native_actual_restart(configured,tmp_path,lab):
    actual_restart(tmp_path,lab)
