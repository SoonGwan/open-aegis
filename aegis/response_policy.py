"""Bounded JSON response contracts. No reference retrieval or response-value evidence."""
import itertools
import json
import math
import re
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

KEYWORDS = {'type', 'properties', 'required', 'additionalProperties', 'items',
            'enum', 'const', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
            'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties'}


def bounded_json(value, nodes, depth):
    stack = [(value, 0)]
    count = 0
    while stack:
        item, level = stack.pop()
        count += 1
        if count > nodes or level > depth:
            raise ValueError('JSON 구조의 크기 또는 깊이 제한을 초과했습니다.')
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('JSON의 숫자는 유한해야 합니다.')
        if isinstance(item, dict):
            stack.extend((child, level + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, level + 1) for child in item)


def validate_schema(schema):
    bounded_json(schema, 512, 16)
    if len(json.dumps(schema, ensure_ascii=False, allow_nan=False).encode()) > 16384:
        raise ValueError('응답 스키마는 16 KiB 이하여야 합니다.')
    stack = [(schema, 0)]
    while stack:
        current, depth = stack.pop()
        if not isinstance(current, dict) or depth > 8 or not set(current) <= KEYWORDS:
            raise ValueError('지원하지 않는 응답 스키마 키워드 또는 깊이입니다.')
        if 'additionalProperties' in current and type(current['additionalProperties']) is not bool:
            raise ValueError('additionalProperties는 true 또는 false만 허용합니다.')
        properties = current.get('properties', {})
        if not isinstance(properties, dict) or len(properties) > 64:
            raise ValueError('스키마 속성은 최대 64개입니다.')
        stack.extend((child, depth + 1) for child in properties.values())
        if 'items' in current:
            stack.append((current['items'], depth + 1))
        constants = current.get('enum', [])
        if not isinstance(constants, list) or len(constants) > 32:
            raise ValueError('enum은 최대 32개입니다.')
        if 'const' in current:
            constants = [*constants, current['const']]
        if any(isinstance(item, (dict, list)) for item in constants):
            raise ValueError('enum과 const는 JSON 스칼라만 허용합니다.')
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError('응답 스키마 형식이 올바르지 않습니다.') from exc
    return schema


def validate_pointer(pointer):
    if not pointer.startswith('/') or len(pointer) > 256 or len(pointer.split('/')) > 17 or re.search(r'~(?![01])', pointer):
        raise ValueError('소유권 경로는 최대 16단계의 JSON Pointer여야 합니다.')
    return pointer


def parse_response(result):
    media = result['headers'].get('content-type', '').split(';', 1)[0].strip().lower()
    if result.get('truncated') or not (media == 'application/json' or media.startswith('application/') and media.endswith('+json')):
        raise ValueError('완전한 JSON 응답이 아니어서 API 응답 정책을 판정할 수 없습니다.')
    if len(result['body']) > 131072:
        raise ValueError('API 응답 정책의 본문 크기 제한을 초과했습니다.')

    def pairs(entries):
        output = {}
        for key, value in entries:
            if key in output:
                raise ValueError('중복 JSON 속성')
            output[key] = value
        return output

    def reject_constant(_):
        raise ValueError('비유한 JSON 상수')

    try:
        body = json.loads(result['body'].decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=reject_constant)
        bounded_json(body, 10000, 32)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('JSON 응답 형식 또는 구조 제한 때문에 API 정책을 판정할 수 없습니다.') from exc
    return body


def evaluate_response(rule, result):
    schema, ownership = rule.get('response_schema'), rule.get('ownership')
    if schema is None and ownership is None:
        return {'schema_errors': [], 'ownership_matches': None}
    body = parse_response(result)
    errors = []
    if schema is not None:
        validate_schema(schema)
        errors = sorted({error.validator for error in itertools.islice(Draft202012Validator(schema).iter_errors(body), 16)})
    if errors or ownership is None:
        return {'schema_errors': errors, 'ownership_matches': None}
    value = body
    try:
        for part in validate_pointer(ownership['pointer']).split('/')[1:]:
            key = part.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not re.fullmatch(r'0|[1-9][0-9]*', key):
                    raise KeyError()
                value = value[int(key)]
            elif isinstance(value, dict):
                value = value[key]
            else:
                raise KeyError()
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError('소유권 필드를 확인하지 못해 API 정책을 판정할 수 없습니다.') from exc
    return {'schema_errors': [], 'ownership_matches': isinstance(value, str) and value == ownership['expected']}
