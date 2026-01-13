from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict
from datetime import datetime
from enums import Emotion, ModelType

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AdminUserResponse(UserResponse):
    is_superuser: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Prediction schemas
class PredictionBase(BaseModel):
    filename: str
    emotion: Dict[str, float]
    confidence: Optional[float] = None
    model_type: str = ModelType.HYBRID.value
    audio_duration: Optional[float] = None

class PredictionCreate(PredictionBase):
    pass

class PredictionResponse(PredictionBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @validator('emotion', pre=True, always=True)
    def parse_emotion(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return {}
        elif isinstance(v, dict):
            return v
        return v

# Audio file schemas
class AudioFileBase(BaseModel):
    filename: str
    file_path: str
    duration: Optional[float] = None
    sample_rate: Optional[int] = None

class AudioFileCreate(AudioFileBase):
    pass

class AudioFileResponse(AudioFileBase):
    id: int
    user_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

# Voice recording schemas
class VoiceRecordingRequest(BaseModel):
    duration: Optional[int] = 3  # seconds

class VoiceRecordingResponse(BaseModel):
    emotion: str
    confidence: Optional[float] = None
    audio_duration: float

# User Activity schemas
class UserActivityBase(BaseModel):
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class UserActivityCreate(UserActivityBase):
    pass

class UserActivityResponse(UserActivityBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# User Statistics schemas
class UserStatisticsBase(BaseModel):
    total_predictions: int = 0
    total_uploads: int = 0
    total_logins: int = 0
    average_confidence: Optional[float] = None
    most_common_emotion: Optional[str] = None
    last_activity: Optional[datetime] = None

class UserStatisticsResponse(UserStatisticsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Prediction Analytics schemas
class PredictionAnalyticsBase(BaseModel):
    model_version: Optional[str] = None
    processing_time: Optional[float] = None
    feature_extraction_time: Optional[float] = None
    model_inference_time: Optional[float] = None

class PredictionAnalyticsCreate(PredictionAnalyticsBase):
    prediction_id: int

class PredictionAnalyticsResponse(PredictionAnalyticsBase):
    id: int
    prediction_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# System Metrics schemas
class SystemMetricsBase(BaseModel):
    metric_type: str
    value: float
    unit: Optional[str] = None

class SystemMetricsCreate(SystemMetricsBase):
    pass

class SystemMetricsResponse(SystemMetricsBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Password reset schemas
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# Email verification schemas
class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationConfirm(BaseModel):
    token: str

# Token refresh schemas
class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

# OTP schemas
class OTPSetupRequest(BaseModel):
    password: str

class OTPSetupResponse(BaseModel):
    secret: str
    qr_code_url: str
    backup_codes: list[str]

class OTPVerifyRequest(BaseModel):
    otp_code: str

class OTPDisableRequest(BaseModel):
    password: str

class OTPBackupCodeRequest(BaseModel):
    backup_code: str
