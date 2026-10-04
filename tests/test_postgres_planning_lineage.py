"""Owned PostgreSQL runs the same real planning continuation contract."""
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_http import configured,client
from tests.test_validation import lab
from tests.test_planning_lineage import (
    test_replan_followup_keeps_round_origin_and_accepted_lookup as test_native_replanned_round,
    test_retry_followup_keeps_round_and_prior_completion as test_native_retried_round,
    test_multiple_replacements_resolve_one_current_pending_attempt as test_native_multiple_replacements,
    test_retry_and_next_plan_race_creates_one_continuation as test_native_continuation_race,
    test_finished_retry_remains_idempotent_and_root_history_is_kept as test_native_finished_retry,
    test_old_root_attempt_adopts_active_preupgrade_retry as test_native_legacy_retry,
    test_history_cap_bounds_unapproved_replacements_without_resetting_round as test_native_history_cap,
    test_corrupt_forward_reference_does_not_redirect_or_create_work as test_native_corrupt_continuation,
)


def test_native_retry_source_pointer_failure_rolls_back_child(client,lab,postgres,configured):
    import psycopg
    from psycopg import sql
    from tests.test_validation import register,task
    store=client.app.state.store
    source=task(client,register(client,lab[0]),['security_headers'])
    store.patch('tasks',source['id'],status='interrupted')
    before=store.get('tasks',source['id'])
    name=sql.Identifier(configured[0])
    with psycopg.connect(postgres['dsn']) as db:
        db.execute(sql.SQL('CREATE SEQUENCE {}.retry_failure_probe').format(name))
        db.execute(sql.SQL("CREATE FUNCTION {}.reject_retry() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.kind='tasks' AND NEW.data::jsonb ? 'retry_successor' THEN PERFORM nextval((TG_TABLE_SCHEMA || '.retry_failure_probe')::regclass); RAISE EXCEPTION 'retry rollback'; END IF; RETURN NEW; END $$").format(name))
        db.execute(sql.SQL('CREATE TRIGGER reject_retry BEFORE INSERT OR UPDATE ON {}.records FOR EACH ROW EXECUTE FUNCTION {}.reject_retry()').format(name,name))
    assert client.post('/api/tasks/'+source['id']+'/retry').status_code==503
    with psycopg.connect(postgres['dsn']) as db:
        assert db.execute(sql.SQL('SELECT last_value,is_called FROM {}.retry_failure_probe').format(name)).fetchone()==(1,True)
    assert store.get('tasks',source['id'])==before and store.count('tasks')==1
    assert store.count('coverage')==1 and lab[1].requests==[]

from tests.test_planning_lineage import test_conflicting_forward_links_are_refused as test_native_conflicting_continuations

from tests.test_planning_lineage import test_replan_refuses_mismatched_storage_key_without_replacing_another_task as test_native_replan_identity
