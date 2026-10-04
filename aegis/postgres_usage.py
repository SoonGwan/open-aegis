"""Stream only usage metadata in one native, read-only PostgreSQL snapshot."""
import json
from .costs import CostSummary

ATTEMPT_STATES=('started','observed','committed','uncommitted','interrupted')
USAGE_STATES=('reported','partial','missing','invalid')
OUTCOMES=('accepted','invalid_plan','invalid_answer','request_failed','unknown_outcome')


def aggregate(store, source, ledger, clock, since, until, fields):
    if clock not in ('observed_at','started_at'):
        raise ValueError('Unknown usage clock')
    records="""
      SELECT 'planner'::text AS source,data::json->'llm_usage' AS metadata FROM records
        WHERE kind='tasks' AND json_typeof(data::json->'llm_usage')='object'
      UNION ALL
      SELECT 'planner'::text AS source,data::json->'llm_usage' AS metadata FROM records
        WHERE kind='goal_plans' AND json_typeof(data::json->'llm_usage')='object'
      UNION ALL
      SELECT 'conversation'::text AS source,data::json->'assistant_generation' AS metadata FROM records
        WHERE kind='messages' AND data::json->>'role'='assistant'
          AND json_typeof(data::json->'assistant_generation')='object'
    """ if ledger=='persisted' else """
      SELECT data::json->>'source' AS source,data::json AS metadata FROM records
        WHERE kind='llm_calls' AND json_typeof(data::json->'started_at')='number'
    """
    query="WITH recorded AS ("+records+") SELECT source,metadata::text AS metadata FROM recorded WHERE (%s='all' OR source=%s) AND CASE WHEN json_typeof(metadata->'"+clock+"')='number' THEN (metadata->>'"+clock+"')::numeric ELSE NULL END BETWEEN %s AND %s"
    row={'calls':0,**dict.fromkeys((*ATTEMPT_STATES,*USAGE_STATES,*OUTCOMES,'planner','conversation'),0)}
    totals=dict.fromkeys(fields,0);costs=CostSummary()
    with store.transaction() as db, db.cursor(name='aegis_usage_metadata') as cursor:
        cursor.itersize=200
        cursor.execute(query,(source,source,since,until))
        for record in cursor:
            data=json.loads(record['metadata']);origin=record['source'];row['calls']+=1
            if origin in ('planner','conversation'):row[origin]+=1
            state=data.get('state')
            if isinstance(state,str) and state in ATTEMPT_STATES:row[state]+=1
            tokens=data.get('tokens');tokens=tokens if isinstance(tokens,dict) else {}
            values=[tokens.get(key) for key in fields]
            valid=all(type(value) is int and 0<=value<=9007199254740991 for value in values)
            status=tokens.get('status')
            if status=='reported' and valid and values[2]==values[0]+values[1]:
                row['reported']+=1
                for key,value in zip(fields,values):totals[key]+=value
            else:
                row[status if isinstance(status,str) and status in ('partial','missing','invalid') else 'invalid']+=1
            outcome=data.get('outcome')
            if outcome in ('accepted','request_failed'):row[outcome]+=1
            elif origin=='planner' and outcome=='invalid_plan':row['invalid_plan']+=1
            elif origin=='conversation' and outcome=='invalid_answer':row['invalid_answer']+=1
            else:row['unknown_outcome']+=1
            # SQLite JSON subobject extraction compacts persisted metadata; attempts
            # use the original record text. CostSummary retains the same size guard.
            metadata=record['metadata'] if ledger=='attempts' else json.dumps(data,ensure_ascii=False,separators=(',',':'))
            costs.step(metadata)
    row.update({key:str(value) for key,value in totals.items()},costs=costs.finalize())
    return row
