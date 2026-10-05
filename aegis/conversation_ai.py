"""Optional provider drafts with bounded, reviewed record citations; never tool execution."""
import json
import os
from contextlib import nullcontext
from .llm import completion, token_usage
from .model_profiles import get_profiles, ProfileUnavailable
from .prompt_versions import Prompts
from .costs import price_snapshot, estimate
from .store_util import now
from . import call_ledger


def configured(store=None):
    return (os.environ.get('AEGIS_LLM_CHAT_ENABLED') == '1' and
            (get_profiles(store).configured('conversation') if store is not None else
             bool(os.environ.get('AEGIS_LLM_API_KEY') and os.environ.get('AEGIS_LLM_MODEL'))))


def draft(summary, question, *, store, task_id, actor_id, allow_local=False, control=None):
    with getattr(store,'execution_permit',nullcontext)():
        return _draft(summary,question,store=store,task_id=task_id,actor_id=actor_id,allow_local=allow_local,control=control)


def _draft(summary, question, *, store, task_id, actor_id, allow_local=False, control=None):
    sources={}
    for citation in summary['provenance']['citations']:
        sources[citation['label']]={'title':citation['title'],'fields':citation['snapshot']}
        if citation.get('evidence'):
            proof=citation['evidence']
            sources[proof['label']]={'check':proof['check'],'excerpt':proof['excerpt'],
                                     'truncated':proof['truncated']}
    prompt=json.dumps({'question':question,'sources':sources},ensure_ascii=False)
    if len(prompt.encode())>65536:
        raise ValueError('AI 대화에 전달할 기록이 64 KiB를 초과합니다. 규칙 기반 요약을 사용하세요.')
    profiles=get_profiles(store,allow_local)
    choice=profiles.capture('conversation')
    if choice is None:raise ValueError('모델 설정을 확인하세요.')
    model,base=choice.model,choice.base
    prompts=Prompts(store)
    prompt_snapshot=prompts.capture('conversation')
    started_at=now()
    price=price_snapshot(model,base,started_at)
    metadata={'model':model,'outcome':'request_failed','tokens':token_usage(None),'started_at':started_at,'prompt_snapshot':prompt_snapshot,'model_profile_snapshot':choice.reference}
    call_id=call_ledger.start(store,'conversation',task_id,model,base,started_at,price,actor_id,prompt_snapshot=prompt_snapshot,model_profile_snapshot=choice.reference)
    metadata['call_id']=call_id
    result=summary
    try:
        profiles.guard(choice)
        raw=completion(base,
            choice.key, {'model':model,'temperature':0,'messages':[
                {'role':'system','content':
                 prompts.system(prompt_snapshot, question)},
                {'role':'user','content':prompt}]},allow_local=choice.local,control=control,timeout=8)
        metadata['outcome']='invalid_answer'
        metadata['tokens']=token_usage(raw.get('usage') if type(raw) is dict else None)
        parsed=json.loads(raw['choices'][0]['message']['content'])
        if type(parsed) is not dict or set(parsed)!={'blocks'}:
            raise ValueError('Invalid answer fields')
        blocks=parsed['blocks']
        if type(blocks) is not list or not 1<=len(blocks)<=12:
            raise ValueError('Invalid blocks')
        lines=[]
        for block in blocks:
            if (type(block) is not dict or set(block)!={'text','citations'} or
                    type(block['text']) is not str or not 1<=len(block['text'].strip())<=1500 or
                    choice.key in block['text'] or
                    type(block['citations']) is not list or not 1<=len(block['citations'])<=17 or
                    any(type(label) is not str or label not in sources for label in block['citations'])):
                raise ValueError('Invalid citation or text')
            labels=list(dict.fromkeys(block['citations']))
            lines.append('['+', '.join(labels)+'] '+block['text'].strip())
        result={**summary,'content':'\n\n'.join(lines)+
                '\n\n이 답변은 AI 초안입니다. 인용의 소속과 형식만 검사하며 내용의 사실성은 독립 검증하지 않았습니다. 추가 요청이나 명령을 실행하지 않습니다.',
                'provenance':{**summary['provenance'],'mode':'recorded_ai'}}
        metadata['outcome']='accepted'
    except Exception:
        # Never persist rejected provider text, bodies or exception messages.
        result={**summary,'content':'AI 답변을 확인하지 못해 저장된 기록의 규칙 기반 요약으로 복구했습니다.\n\n'+summary['content']}
    metadata['observed_at']=now()
    metadata['cost']=estimate(metadata['tokens'],price,metadata['observed_at'])
    call_ledger.observe(store,call_id,metadata)
    return {**result,'assistant_generation':metadata}
