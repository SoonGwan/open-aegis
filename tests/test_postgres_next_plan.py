"""Same follow-up HTTP/approval contract on owned native PostgreSQL."""
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_http import configured,client
from tests.test_validation import lab
from tests.test_next_plan import (
    test_real_results_offer_unattempted_checks_and_chain_finishes_without_oscillation as test_native_followup_chain,
    test_failed_cells_are_selected_and_completed_repetitions_disclosed_with_dependencies as test_native_followup_dependencies,
    test_stale_proposal_cannot_create_a_plan as test_native_stale_followup,
    test_roles_and_pending_archived_missing_corrupt_lineage_are_refused as test_native_followup_roles,
    test_no_remaining_checks_produces_no_plan_and_read_never_executes as test_native_followup_finished,
    test_old_round_completion_becomes_stale_on_asset_revision_change as test_native_historical_revision,
    test_eight_round_limit_prevents_endless_failed_check_loop as test_native_round_limit,
    test_followup_refuses_invalid_execution_approval_without_changing_proof as test_native_followup_approval,
)


def test_native_followup_transaction_rolls_back_source_and_child(client, lab, postgres, configured):
    import psycopg
    from psycopg import sql
    from tests.test_next_plan import completed
    original,path=completed(client,lab)
    store=client.app.state.store
    before=store.get('tasks',original['id'])
    proposal=client.get(path).json()
    name=sql.Identifier(configured[0])
    with psycopg.connect(postgres['dsn']) as db:
        db.execute(sql.SQL('CREATE SEQUENCE {}.followup_failure_probe').format(name))
        db.execute(sql.SQL("CREATE FUNCTION {}.reject_followup() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.kind='tasks' AND NEW.data::jsonb ? 'next_plan_id' THEN PERFORM nextval((TG_TABLE_SCHEMA || '.followup_failure_probe')::regclass); RAISE EXCEPTION 'followup rollback'; END IF; RETURN NEW; END $$").format(name))
        db.execute(sql.SQL('CREATE TRIGGER reject_followup BEFORE INSERT OR UPDATE ON {}.records FOR EACH ROW EXECUTE FUNCTION {}.reject_followup()').format(name,name))
    # Native DB errors are deliberately translated to503 by the app middleware.
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==503
    with psycopg.connect(postgres['dsn']) as db:
        assert db.execute(sql.SQL('SELECT last_value,is_called FROM {}.followup_failure_probe').format(name)).fetchone()==(1,True)
    assert store.get('tasks',original['id'])==before
    assert store.count('tasks')==1

from tests.test_next_plan import test_changed_source_tool_contract_does_not_reuse_completion as test_native_source_contract_change
