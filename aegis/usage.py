"""Snapshot aggregate of recorded, single-call task planner usage; no inference."""
import time


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
    until = time.time()
    since = until-days*86400 if days else 0
    fields = ('prompt_tokens', 'completion_tokens', 'total_tokens')
    projections = ', '.join(f"json_extract(data,'$.llm_usage.tokens.{key}') AS {key}" for key in fields)
    numeric = ' AND '.join(
        f"json_type(data,'$.llm_usage.tokens.{key}')='integer' AND "
        f"json_extract(data,'$.llm_usage.tokens.{key}') BETWEEN 0 AND 9007199254740991"
        for key in fields)
    query = f"""
      WITH calls AS (
        SELECT {projections}, json_extract(data,'$.llm_usage.outcome') AS outcome,
          CASE WHEN json_extract(data,'$.llm_usage.tokens.status')='reported'
            AND {numeric}
            AND json_extract(data,'$.llm_usage.tokens.total_tokens')=
                json_extract(data,'$.llm_usage.tokens.prompt_tokens')+json_extract(data,'$.llm_usage.tokens.completion_tokens')
          THEN 'reported'
          WHEN json_extract(data,'$.llm_usage.tokens.status') IN ('partial','missing','invalid')
          THEN json_extract(data,'$.llm_usage.tokens.status') ELSE 'invalid' END AS status
        FROM records WHERE kind='tasks' AND json_type(data,'$.llm_usage')='object'
          AND json_type(data,'$.llm_usage.observed_at') IN ('integer','real')
          AND json_extract(data,'$.llm_usage.observed_at') BETWEEN ? AND ?
      ) SELECT count(*) AS calls,
        count(*) FILTER (WHERE status='reported') AS reported,
        count(*) FILTER (WHERE status='partial') AS partial,
        count(*) FILTER (WHERE status='missing') AS missing,
        count(*) FILTER (WHERE status='invalid') AS invalid,
        count(*) FILTER (WHERE outcome='accepted') AS accepted,
        count(*) FILTER (WHERE outcome='invalid_plan') AS invalid_plan,
        count(*) FILTER (WHERE outcome='request_failed') AS request_failed,
        count(*) FILTER (WHERE outcome IS NULL OR outcome NOT IN ('accepted','invalid_plan','request_failed')) AS unknown_outcome,
        {', '.join(f"exact_sum({key}) FILTER (WHERE status='reported') AS {key}" for key in fields)}
      FROM calls
    """
    with store.connect() as db:
        db.create_aggregate('exact_sum', 1, ExactSum)
        db.execute('BEGIN')
        row = dict(db.execute(query, (max(0, since), until)).fetchone())
    return {
        'scope':'latest_planner_call_per_task', 'days':days, 'since':max(0, since), 'until':until,
        'calls':row['calls'],
        'usage_states':{key:row[key] for key in ('reported','partial','missing','invalid')},
        'outcomes':{key:row[key] for key in ('accepted','invalid_plan','request_failed','unknown_outcome')},
        'reported_tokens':{key:row[key] if row['reported'] else None for key in fields},
    }
