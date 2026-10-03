"""Shared API policy input contracts for registration and reproduction artifacts."""
from pydantic import BaseModel, Field, field_validator
from .response_policy import validate_schema, validate_pointer


class OwnershipPolicy(BaseModel):
    model_config = {'extra': 'forbid'}
    pointer: str = Field(min_length=1, max_length=256)
    expected: str = Field(min_length=1, max_length=200)

    @field_validator('pointer')
    @classmethod
    def validate_pointer(cls, value):
        return validate_pointer(value)


class AuthorizationRule(BaseModel):
    model_config = {'extra': 'forbid'}
    path: str = Field(max_length=1000)
    role: str = Field(min_length=1, max_length=80)
    expected_allowed: bool
    credential_env: str = Field(default='', max_length=100, pattern=r'^(|AEGIS_TEST_[A-Z0-9_]+)$')
    response_schema: dict | None = None
    ownership: OwnershipPolicy | None = None

    @field_validator('response_schema')
    @classmethod
    def validate_response_schema(cls, value):
        return validate_schema(value) if value is not None else None

    @field_validator('path')
    @classmethod
    def validate_path(cls, value):
        if not value.startswith('/') or value.startswith('//') or '?' in value or '#' in value:
            raise ValueError('루트 기준 경로만 허용합니다. 쿼리와 fragment는 사용할 수 없습니다.')
        return value


