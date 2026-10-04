"""Snapshot aggregate of persisted planner and conversation usage; no inference."""
import time
import json
from .costs import CostSummary, STATES


class ExactSum:
    def __init__(self):
        self.value = 0

    def step(self, value):
        if value is not None:
            self.value += value

    def finalize(self):
        # Decimal strings preserve precision beyond JavaScript/SQLite sum limits.
        return str(self.value)


def planner_summary(store, days=None):
    """Keep the original planner-only API contract."""
    return usage_summary(store, days, source='planner')


def usage_summary(store, days=None, *, source='planner', ledger='persisted'):
    if source not in ('planner', 'conversation', 'all'):
        raise ValueError('Unknown usage source')
    if ledger not in ('persisted','attempts'):
        raise ValueError('Unknown usage ledger')
    until = time.time()
    since = until-days*86400 if days else 0
    fields = ('prompt_tokens', 'completion_tokens', 'total_tokens')
    projections = ', '.join(f"json_extract(metadata,'$.tokens.{key}') AS {key}" for key in fields)
    numeric = ' AND '.join(
        f"json_type(metadata,'$.tokens.{key}')='integer' AND "
        f"json_extract(metadata,'$.tokens.{key}') BETWEEN 0 AND 9007199254740991"
        for key in fields)
    records = """
        SELECT 'planner' AS source, json_extract(data,'$.llm_usage') AS metadata
        FROM records WHERE kind='tasks' AND json_type(data,'$.llm_usage')='object'
        UNION ALL
        SELECT 'conversation' AS source, json_extract(data,'$.assistant_generation') AS metadata
        FROM records WHERE kind='messages' AND json_extract(data,'$.role')='assistant'
          AND json_type(data,'$.assistant_generation')='object'
    """ if ledger == 'persisted' else """
        SELECT json_extract(data,'$.source') AS source, data AS metadata
        FROM records WHERE kind='llm_calls' AND json_type(data,'$.started_at') IN ('integer','real')
    """
    clock='observed_at' if ledger == 'persisted' else 'started_at'
    query = f"""
      WITH recorded AS ({records}), calls AS (
        SELECT source, metadata, {projections}, json_extract(metadata,'$.outcome') AS outcome,
          CASE WHEN json_extract(metadata,'$.tokens.status')='reported'
            AND {numeric}
            AND json_extract(metadata,'$.tokens.total_tokens')=
                json_extract(metadata,'$.tokens.prompt_tokens')+json_extract(metadata,'$.tokens.completion_tokens')
          THEN 'reported'
          WHEN json_extract(metadata,'$.tokens.status') IN ('partial','missing','invalid')
          THEN json_extract(metadata,'$.tokens.status') ELSE 'invalid' END AS status
        FROM recorded WHERE (?='all' OR source=?)
          AND json_type(metadata,'$.{clock}') IN ('integer','real')
          AND json_extract(metadata,'$.{clock}') BETWEEN ? AND ?
      ) SELECT count(*) AS calls, cost_summary(metadata) AS costs,
        {', '.join("count(*) FILTER (WHERE json_extract(metadata,'$.state')='"+state+"') AS "+state
          for state in ('started','observed','committed','uncommitted','interrupted'))},
        count(*) FILTER (WHERE status='reported') AS reported,
        count(*) FILTER (WHERE status='partial') AS partial,
        count(*) FILTER (WHERE status='missing') AS missing,
        count(*) FILTER (WHERE status='invalid') AS invalid,
        count(*) FILTER (WHERE outcome='accepted') AS accepted,
        count(*) FILTER (WHERE source='planner' AND outcome='invalid_plan') AS invalid_plan,
        count(*) FILTER (WHERE source='conversation' AND outcome='invalid_answer') AS invalid_answer,
        count(*) FILTER (WHERE outcome='request_failed') AS request_failed,
        count(*) FILTER (WHERE outcome IS NULL OR NOT (outcome IN ('accepted','request_failed')
          OR (source='planner' AND outcome='invalid_plan')
          OR (source='conversation' AND outcome='invalid_answer'))) AS unknown_outcome,
        count(*) FILTER (WHERE source='planner') AS planner,
        count(*) FILTER (WHERE source='conversation') AS conversation,
        {', '.join(f"exact_sum({key}) FILTER (WHERE status='reported') AS {key}" for key in fields)}
      FROM calls
    """
    with store.connect() as db:
        db.create_aggregate('exact_sum', 1, ExactSum)
        db.create_aggregate('cost_summary', 1, CostSummary)
        db.execute('BEGIN')
        row = dict(db.execute(query, (source, source, max(0, since), until)).fetchone())
    return {
        'scope':'recorded_provider_attempts' if ledger == 'attempts' else {'planner':'latest_planner_call_per_task',
                 'conversation':'persisted_assistant_generation_per_message',
                 'all':'latest_planner_and_persisted_conversation_calls'}[source],
        'ledger':ledger, 'time_basis':clock,
        'attempt_states':{key:row[key] for key in ('started','observed','committed','uncommitted','interrupted')} if ledger == 'attempts' else None,
        'source':source, 'source_counts':{key:row[key] for key in ('planner','conversation')},
        'days':days, 'since':max(0, since), 'until':until,
        'calls':row['calls'],
        'costs':json.loads(row['costs']) if row['costs'] else
            {'states':dict.fromkeys(STATES,0),'totals':[]},
        'usage_states':{key:row[key] for key in ('reported','partial','missing','invalid')},
        'outcomes':{key:row[key] for key in ('accepted','invalid_plan','invalid_answer','request_failed','unknown_outcome')},
        'reported_tokens':{key:row[key] if row['reported'] else None for key in fields},
    }
