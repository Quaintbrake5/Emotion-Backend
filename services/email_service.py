import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
import os
from jose import jwt
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply@emotionrecognition.com")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8001")

    def _create_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token for email verification/password reset"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hours default
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm="HS256")
        return encoded_jwt

    def _verify_token(self, token: str) -> Optional[dict]:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError:
            logger.warning("Invalid token")
            return None

    def _send_email(self, recipient: str, subject: str, html_content: str):
        """Send an email using SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient

            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipient, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False

    def send_verification_email(self, email: str, user_id: int, username: str) -> str:
        """Send email verification link"""
        token = self._create_token({"sub": email, "user_id": user_id, "type": "verification"})

        verification_url = f"{self.base_url}/auth/verify-email?token={token}"

        html_content = f"""
        <html>
        <body>
            <h2>Welcome to Emotion Recognition API, {username}!</h2>
            <p>Please verify your email address by clicking the link below:</p>
            <a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a>
            <p>If the button doesn't work, copy and paste this URL into your browser:</p>
            <p>{verification_url}</p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
        </body>
        </html>
        """

        self._send_email(email, "Verify Your Email - Emotion Recognition API", html_content)
        return token

    def send_password_reset_email(self, email: str, user_id: int, username: str) -> str:
        """Send password reset link"""
        token = self._create_token({"sub": email, "user_id": user_id, "type": "password_reset"})

        reset_url = f"{self.base_url}/auth/reset-password?token={token}"

        html_content = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hello {username},</p>
            <p>You requested a password reset for your Emotion Recognition API account.</p>
            <p>Click the link below to reset your password:</p>
            <a href="{reset_url}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a>
            <p>If the button doesn't work, copy and paste this URL into your browser:</p>
            <p>{reset_url}</p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't request this reset, please ignore this email.</p>
        </body>
        </html>
        """

        self._send_email(email, "Reset Your Password - Emotion Recognition API", html_content)
        return token

    def verify_email_token(self, token: str) -> Optional[dict]:
        """Verify email verification token"""
        payload = self._verify_token(token)
        if payload and payload.get("type") == "verification":
            return payload
        return None

    def verify_password_reset_token(self, token: str) -> Optional[dict]:
        """Verify password reset token"""
        payload = self._verify_token(token)
        if payload and payload.get("type") == "password_reset":
            return payload
        return None

    def send_welcome_email(self, email: str, username: str):
        """Send welcome email after successful verification"""
        html_content = f"""
        <html>
        <body>
            <h2>Welcome to Emotion Recognition API!</h2>
            <p>Hello {username},</p>
            <p>Your email has been successfully verified. You can now start using our emotion recognition services!</p>
            <p>Get started by uploading audio files or using our voice recording feature.</p>
            <p>Happy analyzing!</p>
            <br>
            <p>Best regards,<br>The Emotion Recognition Team</p>
        </body>
        </html>
        """

        self._send_email(email, "Welcome to Emotion Recognition API!", html_content)

    def send_admin_notification(self, admin_email: str, subject: str, message: str):
        """Send notification to admin"""
        html_content = f"""
        <html>
        <body>
            <h2>Admin Notification</h2>
            <p>{message}</p>
            <br>
            <p>Emotion Recognition API System</p>
        </body>
        </html>
        """

        self._send_email(admin_email, f"Admin Alert: {subject}", html_content)
