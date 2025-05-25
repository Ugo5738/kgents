from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Schema for user registration input."""

    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Schema for user login input."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user data returned in responses."""

    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"
