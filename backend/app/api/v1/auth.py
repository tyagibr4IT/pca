from fastapi import APIRouter, Depends, HTTPException
from app.auth.jwt import create_access_token, decode_token
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginIn(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(payload: LoginIn):
    # Demo: in real life verify username/password, or OIDC via Azure AD
    if payload.username == "admin" and payload.password == "password":
        token = create_access_token(subject=payload.username, scopes=["admin"])
        return {"access_token": token, "token_type":"bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/me")
async def me():
    # simplified demo endpoint — in production extract and validate a token
    return {"user": "demo"}