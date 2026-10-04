"""The same shared decisions over the owned native HTTP backend."""
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_http import configured,client
from tests.test_todos import (
    test_shared_http_todos_survive_real_retry_replan_and_duplicate_creation as test_native_todo_family,
    test_todo_http_validation_roles_foreign_families_and_no_execution as test_native_todo_permissions,
    test_todo_change_and_audit_rollback_together_on_event_failure as test_native_todo_rollback,
)
