import pyotp
import qrcode
import io
import base64
import secrets
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self):
        self.issuer_name = "Emotion Recognition API"

    def generate_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()

    def generate_qr_code(self, secret: str, username: str, issuer: str = None) -> str:
        """Generate QR code for TOTP setup"""
        if issuer is None:
            issuer = self.issuer_name

        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name=issuer)

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)

        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{qr_code_base64}"

    def verify_otp(self, secret: str, otp_code: str) -> bool:
        """Verify TOTP code"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(otp_code)
        except Exception as e:
            logger.error(f"OTP verification failed: {str(e)}")
            return False

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for OTP"""
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8-character hex codes
            codes.append(code)
        return codes

    def hash_backup_codes(self, codes: List[str]) -> str:
        """Hash backup codes for storage"""
        # In production, use proper hashing with salt
        # For now, we'll store them as JSON (not secure, but for demo)
        return json.dumps(codes)

    def verify_backup_code(self, stored_codes_json: str, code: str) -> tuple[bool, str]:
        """Verify backup code and return updated codes"""
        try:
            codes = json.loads(stored_codes_json)
            if code in codes:
                codes.remove(code)  # Remove used code
                return True, json.dumps(codes)
            return False, stored_codes_json
        except Exception as e:
            logger.error(f"Backup code verification failed: {str(e)}")
            return False, stored_codes_json

    def setup_otp(self, username: str) -> dict:
        """Set up OTP for a user"""
        secret = self.generate_secret()
        qr_code_url = self.generate_qr_code(secret, username)
        backup_codes = self.generate_backup_codes()

        return {
            "secret": secret,
            "qr_code_url": qr_code_url,
            "backup_codes": backup_codes
        }

    def validate_otp_setup(self, secret: str, otp_code: str) -> bool:
        """Validate OTP setup by verifying the first code"""
        return self.verify_otp(secret, otp_code)
