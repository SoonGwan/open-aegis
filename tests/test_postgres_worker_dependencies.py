"""Run the owned dependency HTTP/Engine contract on native PostgreSQL too."""
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_http import configured,client
from tests.test_validation import lab
from tests.test_runtime import peer
from tests.test_worker_dependencies import (
    test_owned_dependency_order_handoff_and_no_requests_before_approval as test_native_dependency_handoff,
    test_failed_predecessor_blocks_child_and_descendant_without_requests as test_native_failed_dependency,
    test_invalid_dependencies_refused_before_work as test_native_invalid_dependency,
    test_changed_dependency_contract_before_worker_run_is_not_executed as test_native_changed_contract,
    test_corrupt_completed_source_coverage_blocks_handoff as test_native_corrupt_coverage,
    test_join_waits_for_all_predecessors_and_independent_worker_runs as test_native_join_parallel_workers,
    test_stop_held_parent_cancels_pending_dependency_without_child_request as test_native_stop_dependency,
    test_replan_preserves_dependencies_but_requires_new_approval as test_native_replan_dependency,
)
