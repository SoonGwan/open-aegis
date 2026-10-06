"""Explicit text-only wire formats for reviewed fixed model destinations."""

PROTOCOLS=('openai','anthropic')
MAX_OUTPUT_TOKENS=4096


def headers(protocol,key):
    if protocol=='openai':return {'Authorization':'Bearer '+key}
    if protocol=='anthropic':return {'x-api-key':key,'anthropic-version':'2023-06-01'}
    raise ValueError('Unsupported provider protocol')


def inference_request(protocol,key,payload):
    authentication=headers(protocol,key)
    if protocol=='openai':return '/chat/completions',authentication,payload
    if (type(payload) is not dict or set(payload)-{'model','messages','temperature','max_tokens','stream'}
            or type(payload.get('model')) is not str or not payload['model']):
        raise ValueError('Invalid provider request')
    messages=payload.get('messages')
    if type(messages) is not list or not 1<=len(messages)<=32:raise ValueError('Invalid provider messages')
    system=[];conversation=[]
    for message in messages:
        if (type(message) is not dict or set(message)!={'role','content'} or
                message['role'] not in ('system','user','assistant') or type(message['content']) is not str):
            raise ValueError('Invalid provider messages')
        if message['role']=='system':system.append(message['content'])
        else:conversation.append(message)
    maximum=payload.get('max_tokens',MAX_OUTPUT_TOKENS)
    if type(maximum) is not int or not 1<=maximum<=MAX_OUTPUT_TOKENS or payload.get('stream',False) is not False or not conversation:
        raise ValueError('Invalid provider output budget')
    body={'model':payload['model'],'messages':conversation,'max_tokens':maximum,'stream':False}
    if system:body['system']='\n\n'.join(system)
    return '/messages',authentication,body


def inference_response(protocol,body):
    if protocol=='openai':return body
    if protocol!='anthropic':raise ValueError('Unsupported provider protocol')
    if (type(body) is not dict or body.get('type')!='message' or body.get('role')!='assistant'
            or body.get('stop_reason')!='end_turn' or body.get('stop_details') is not None):
        raise ValueError('Invalid provider response')
    blocks=body.get('content')
    if type(blocks) is not list or not 1<=len(blocks)<=32:raise ValueError('Invalid provider text')
    parts=[]
    for block in blocks:
        if type(block) is not dict or block.get('type')!='text' or type(block.get('text')) is not str:
            raise ValueError('Invalid provider text')
        parts.append(block['text'])
    usage=body.get('usage')
    if type(usage) is dict:
        usage={target:usage[source] for source,target in (('input_tokens','prompt_tokens'),('output_tokens','completion_tokens')) if source in usage}
    return {'choices':[{'message':{'role':'assistant','content':''.join(parts)}}],'usage':usage}


def catalog_request(protocol,key):
    authentication=headers(protocol,key)
    return ('/models?limit=256' if protocol=='anthropic' else '/models'),authentication


def catalog_response(protocol,body):
    if protocol not in PROTOCOLS:raise ValueError('Unsupported provider protocol')
    if protocol=='anthropic' and (type(body) is not dict or body.get('has_more') is not False):
        raise ValueError('Provider catalog is incomplete')
    return body
