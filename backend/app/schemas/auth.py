from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    role: str
    invite_code: str = Field(min_length=1, max_length=128)

    @field_validator("username", "display_name", "role", "invite_code")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in {"visitor", "counselor"}:
            raise ValueError("role must be visitor or counselor")
        return value


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: AuthUserResponse


class AccountListItem(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    active_for_human_letters: bool = False
    created_at: str


class AccountListResponse(BaseModel):
    items: list[AccountListItem]
    total: int
    visitor_count: int
    counselor_count: int
    active_counselor_count: int
