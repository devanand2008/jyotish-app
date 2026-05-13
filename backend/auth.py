from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt

# Google OAuth Client ID — read from environment variable on Render
GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "1055510399803-bv8vphrhlam8cn5uljii5cs8ghubcuvl.apps.googleusercontent.com"
)

# Secret key for JWT — always use env var in production (Render sets this)
SECRET_KEY = os.environ.get("SECRET_KEY", "astro_super_secret_key_3_0")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# ADMIN email — only this email gets Admin role
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "devanand2008@gmail.com")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    token: str
    role_requested: str = "User"  # "User" or "Astrologer"


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/google")
async def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(req.token, requests.Request(), GOOGLE_CLIENT_ID)

        email = idinfo["email"]
        name = idinfo.get("name", "Unknown")
        picture = idinfo.get("picture", "")
        google_id = idinfo["sub"]

        user = db.query(models.User).filter(models.User.email == email).first()

        if not user:
            # Determine role & status for first-time login
            if email == ADMIN_EMAIL:
                # Reserved admin account — always Admin, always Approved
                role = "Admin"
                status_val = "Approved"
            else:
                role = req.role_requested
                status_val = "Pending" if role == "Astrologer" else "Approved"

            user = models.User(
                email=email,
                name=name,
                picture=picture,
                google_id=google_id,
                role=role,
                status=status_val,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Ensure the designated admin keeps Admin role on every login
            if email == ADMIN_EMAIL and user.role != "Admin":
                user.role = "Admin"
                user.status = "Approved"
                db.commit()
                db.refresh(user)

        # Generate JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role, "status": user.status},
            expires_delta=access_token_expires,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "picture": user.picture,
                "role": user.role,
                "status": user.status,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@router.get("/me")
async def get_me(token: str, db: Session = Depends(get_db)):
    """Get current user info (used by pending.html to check approval status).
    Accepts JWT as query param ?token=...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "picture": user.picture,
        "role": user.role,
        "status": user.status,
    }


def get_current_user(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user
