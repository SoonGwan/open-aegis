"""Exact flat text-token estimates from operator-supplied, call-time price quotes."""
from datetime import date, datetime, timezone
import json
import os
import re
from urllib.parse import urlsplit

SCALE = 10**15  # Nine rate decimals per million tokens; never round through float.
CURRENCIES = {'USD', 'EUR', 'KRW', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'INR', 'BRL'}
STATES = ('estimated', 'usage_unavailable', 'unconfigured', 'model_unpriced',
          'invalid_configuration', 'unrecorded', 'invalid_record')
QUOTE_FIELDS = {'model', 'provider', 'currency', 'input_per_million',
                'output_per_million', 'source_url', 'as_of', 'basis'}


def rate_units(value):
    if type(value) is not str or not re.fullmatch(r'(0|[1-9][0-9]{0,6})(\.[0-9]{1,9})?', value):
        raise ValueError('Invalid price rate')
    whole, _, fraction = value.partition('.')
    units = int(whole)*10**9 + int(fraction.ljust(9, '0') or '0')
    if units > 10**15:
        raise ValueError('Price rate exceeds limit')
    return units


def amount_text(units):
    whole, fraction = divmod(units, SCALE)
    return str(whole) + ('.' + str(fraction).zfill(15).rstrip('0') if fraction else '')


def safe_url(value, *, provider=False):
    if (type(value) is not str or not 1 <= len(value) <= 2048 or
            any(ord(char) <= 32 or ord(char) == 127 for char in value)):
        raise ValueError('Invalid price URL')
    parsed = urlsplit(value)
    local = provider and parsed.hostname in ('localhost', '127.0.0.1', '::1')
    if (parsed.scheme != 'https' and not (local and parsed.scheme == 'http') or
            not parsed.hostname or parsed.username or parsed.password or
            parsed.query or parsed.fragment):
        raise ValueError('Invalid price URL')
    parsed.port  # Validate port without fetching the URL.
    return value.rstrip('/') if provider else value


def validate_quote(quote, at):
    if type(quote) is not dict or set(quote) != QUOTE_FIELDS:
        raise ValueError('Invalid price fields')
    model = quote['model']
    if (type(model) is not str or not 1 <= len(model) <= 200 or model.strip() != model or
            any(ord(char) < 32 or ord(char) == 127 for char in model)):
        raise ValueError('Invalid price model')
    if quote['currency'] not in CURRENCIES or quote['basis'] != 'flat_text_tokens':
        raise ValueError('Invalid currency or price basis')
    if safe_url(quote['provider'], provider=True) != quote['provider']:
        raise ValueError('Provider must omit trailing slash')
    safe_url(quote['source_url'])
    if type(quote['as_of']) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', quote['as_of']):
        raise ValueError('Invalid price date')
    if date.fromisoformat(quote['as_of']) > datetime.fromtimestamp(at, timezone.utc).date():
        raise ValueError('Future price date')
    return rate_units(quote['input_per_million']), rate_units(quote['output_per_million'])


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate price field')
        result[key] = value
    return result


def price_snapshot(model, provider, at):
    raw = os.environ.get('AEGIS_LLM_PRICES', '[]')
    try:
        if len(raw.encode()) > 65536:
            raise ValueError('Price configuration exceeds budget')
        quotes = json.loads(raw, object_pairs_hook=unique_fields)
        if type(quotes) is not list or len(quotes) > 100:
            raise ValueError('Invalid price configuration')
        seen = set()
        for quote in quotes:
            validate_quote(quote, at)
            identity = (quote['model'], quote['provider'])
            if identity in seen:
                raise ValueError('Duplicate model/provider price')
            seen.add(identity)
        for quote in quotes:
            if (quote['model'], quote['provider']) == (model, provider.rstrip('/')):
                return {'status':'quoted', 'quote':quote}
        return {'status':'model_unpriced' if quotes else 'unconfigured', 'quote':None}
    except (ValueError, TypeError, OverflowError, OSError, RecursionError):
        # Never persist raw configuration or parser messages, which may contain secrets.
        return {'status':'invalid_configuration', 'quote':None}


def estimate_units(tokens, quote, at):
    input_rate, output_rate = validate_quote(quote, at)
    if type(tokens) is not dict or tokens.get('status') != 'reported':
        raise ValueError('Reported usage is unavailable')
    values = [tokens.get(key) for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')]
    if (any(type(value) is not int or not 0 <= value <= 9007199254740991 for value in values)
            or values[2] != values[0] + values[1]):
        raise ValueError('Invalid reported usage')
    return values[0]*input_rate + values[1]*output_rate


def estimate(tokens, snapshot, at):
    if snapshot['status'] != 'quoted':
        return {**snapshot, 'amount':None}
    try:
        amount = amount_text(estimate_units(tokens, snapshot['quote'], at))
        return {'status':'estimated', 'quote':snapshot['quote'], 'amount':amount}
    except (ValueError, TypeError, OverflowError, OSError, RecursionError):
        return {'status':'usage_unavailable', 'quote':snapshot['quote'], 'amount':None}


class CostSummary:
    """SQLite aggregate: recheck persisted estimates and sum each currency exactly."""
    def __init__(self):
        self.states = dict.fromkeys(STATES, 0)
        self.totals = {}

    def step(self, metadata):
        state = 'invalid_record'
        try:
            if type(metadata) is not str or len(metadata.encode()) > 16384:
                raise ValueError('Metadata exceeds budget')
            data = json.loads(metadata)
            cost = data.get('cost')
            if cost is None:
                state = 'unrecorded'
            else:
                if type(cost) is not dict or set(cost) != {'status', 'quote', 'amount'}:
                    raise ValueError('Invalid estimate fields')
                state = cost['status']
                if state not in STATES[:5]:
                    raise ValueError('Invalid estimate state')
                if state in ('estimated', 'usage_unavailable'):
                    validate_quote(cost['quote'], data['observed_at'])
                    if cost['quote']['model'] != data['model']:
                        raise ValueError('Mismatched model')
                elif cost['quote'] is not None:
                    raise ValueError('Unexpected quote')
                if state == 'estimated':
                    units = estimate_units(data['tokens'], cost['quote'], data['observed_at'])
                    if cost['amount'] != amount_text(units):
                        raise ValueError('Mismatched amount')
                    currency = cost['quote']['currency']
                    bucket = self.totals.setdefault(currency, {'units':0, 'calls':0})
                    bucket['units'] += units
                    bucket['calls'] += 1
                elif state == 'usage_unavailable':
                    try:
                        estimate_units(data['tokens'], cost['quote'], data['observed_at'])
                    except (ValueError, TypeError, KeyError):
                        pass
                    else:
                        raise ValueError('Valid usage mislabeled as unavailable')
                    if cost['amount'] is not None:
                        raise ValueError('Unexpected amount')
                elif cost['amount'] is not None:
                    raise ValueError('Unexpected amount')
        except (ValueError, TypeError, KeyError, OverflowError, OSError, RecursionError):
            state = 'invalid_record'
        self.states[state] += 1

    def finalize(self):
        return json.dumps({'states':self.states, 'totals':[
            {'currency':currency, 'amount':amount_text(bucket['units']), 'calls':bucket['calls']}
            for currency, bucket in sorted(self.totals.items())]})
