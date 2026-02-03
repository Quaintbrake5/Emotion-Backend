import json
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enums import Emotion, ModelType

Base = declarative_base()

# Constants for foreign keys
USER_ID_FOREIGN_KEY = "users.id"
PREDICTION_ID_FOREIGN_KEY = "predictions.id"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    otp_secret = Column(String(32), nullable=True)  # For TOTP
    otp_enabled = Column(Boolean, default=False)
    otp_backup_codes = Column(Text, nullable=True)  # JSON array of backup codes
    temp_otp_secret = Column(String(32), nullable=True)  # Temporary secret during setup
    reset_token = Column(String(64), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    verification_token = Column(String(64), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    predictions = relationship("Prediction", back_populates="user")
    activities = relationship("UserActivity", back_populates="user")
    statistics = relationship("UserStatistics", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(USER_ID_FOREIGN_KEY), nullable=False)
    filename = Column(String(255), nullable=False)
    emotion = Column(Text, nullable=False)  # JSON string of emotion probabilities
    confidence = Column(Float, nullable=True)
    model_type = Column(String(50), default=ModelType.HYBRID.value)
    audio_duration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="predictions")

    @property
    def emotion_dict(self) -> dict:
        """Get emotion as dictionary."""
        return json.loads(self.emotion)

    @emotion_dict.setter
    def emotion_dict(self, value: dict):
        """Set emotion from dictionary."""
        self.emotion = json.dumps(value)

    def __repr__(self):
        return f"<Prediction(id={self.id}, emotion={self.emotion}, confidence={self.confidence})>"

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(USER_ID_FOREIGN_KEY), nullable=False)
    filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    duration = Column(Float, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.now(datetime.timezone.utc))

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<AudioFile(id={self.id}, filename={self.filename})>"

class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(USER_ID_FOREIGN_KEY), nullable=False)
    action = Column(String(100), nullable=False)  # login, prediction, upload, etc.
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 support
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="activities")

    def __repr__(self):
        return f"<UserActivity(id={self.id}, user_id={self.user_id}, action={self.action})>"

class UserStatistics(Base):
    __tablename__ = "user_statistics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(USER_ID_FOREIGN_KEY), nullable=False, unique=True)
    total_predictions = Column(Integer, default=0)
    total_uploads = Column(Integer, default=0)
    total_logins = Column(Integer, default=0)
    average_confidence = Column(Float, nullable=True)
    most_common_emotion = Column(String(50), nullable=True)
    last_activity = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="statistics")

    def __repr__(self):
        return f"<UserStatistics(user_id={self.user_id}, total_predictions={self.total_predictions})>"

class PredictionAnalytics(Base):
    __tablename__ = "prediction_analytics"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey(PREDICTION_ID_FOREIGN_KEY), nullable=False)
    model_version = Column(String(50), nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds
    feature_extraction_time = Column(Float, nullable=True)
    model_inference_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    prediction = relationship("Prediction")

    def __repr__(self):
        return f"<PredictionAnalytics(id={self.id}, prediction_id={self.prediction_id})>"

class SystemMetrics(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String(50), nullable=False)  # cpu, memory, disk, requests
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)  # percentage, bytes, count, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SystemMetrics(id={self.id}, type={self.metric_type}, value={self.value})>"
