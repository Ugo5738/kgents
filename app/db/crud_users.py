"""
CRUD operations for users table in Supabase.
"""

from passlib.context import CryptContext
from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.models.user import UserCreate, UserLogin, UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password for storing.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed one.
    """
    return pwd_context.verify(plain_password, hashed_password)


async def create_user(user_create: UserCreate) -> UserResponse:
    """
    Create a new user in the database.
    """
    client: Client = await get_supabase_client()
    user_data = {
        "email": user_create.email,
        "hashed_password": hash_password(user_create.password),
    }
    response = client.table("users").insert(user_data).execute()
    created = response.data[0]
    return UserResponse(**created)


async def authenticate_user(user_login: UserLogin) -> UserResponse | None:
    """
    Authenticate user and return user info if successful.
    """
    client: Client = await get_supabase_client()
    response = client.table("users").select("*").eq("email", user_login.email).execute()
    data = response.data or []
    if not data:
        return None
    user_record = data[0]
    if not verify_password(user_login.password, user_record["hashed_password"]):
        return None
    return UserResponse(**user_record)


async def get_user_by_id(user_id: int) -> UserResponse | None:
    """
    Retrieve a user by their ID from the database.
    """
    client: Client = await get_supabase_client()
    response = client.table("users").select("*").eq("id", user_id).execute()
    data = response.data or []
    if not data:
        return None
    return UserResponse(**data[0])
