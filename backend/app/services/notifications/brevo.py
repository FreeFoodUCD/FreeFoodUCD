import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_verification_email(email: str, code: str) -> bool:
    """Send verification code via Brevo (Sendinblue)."""
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json"
        }
        
        data = {
            "sender": {
                "name": settings.BREVO_FROM_NAME,
                "email": settings.BREVO_FROM_EMAIL
            },
            "to": [
                {
                    "email": email,
                    "name": email.split("@")[0]
                }
            ],
            "subject": "Your FreeFood UCD Verification Code",
            "htmlContent": f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 16px;
                        padding: 40px;
                        text-align: center;
                    }}
                    .code-box {{
                        background: white;
                        border-radius: 12px;
                        padding: 30px;
                        margin: 30px 0;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    .code {{
                        font-size: 48px;
                        font-weight: bold;
                        letter-spacing: 8px;
                        color: #667eea;
                        font-family: 'Courier New', monospace;
                    }}
                    .title {{
                        color: white;
                        font-size: 28px;
                        font-weight: bold;
                        margin-bottom: 10px;
                    }}
                    .subtitle {{
                        color: rgba(255,255,255,0.9);
                        font-size: 16px;
                        margin-bottom: 20px;
                    }}
                    .footer {{
                        color: rgba(255,255,255,0.8);
                        font-size: 14px;
                        margin-top: 30px;
                    }}
                    .emoji {{
                        font-size: 48px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="emoji">🍕</div>
                    <div class="title">Welcome to FreeFood UCD!</div>
                    <div class="subtitle">Your verification code is ready</div>
                    
                    <div class="code-box">
                        <div style="color: #666; font-size: 14px; margin-bottom: 10px;">
                            Enter this code to complete your signup:
                        </div>
                        <div class="code">{code}</div>
                        <div style="color: #999; font-size: 12px; margin-top: 10px;">
                            Code expires in 10 minutes
                        </div>
                    </div>
                    
                    <div class="footer">
                        Never miss free food on campus again! 🎉<br>
                        You'll get notified about free food events from UCD societies.
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=10.0)
            response.raise_for_status()
            
        logger.info(f"Verification code sent via Brevo to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending verification code via Brevo: {str(e)}")
        return False


async def send_welcome_email(email: str) -> bool:
    """Send welcome email after successful verification."""
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json"
        }
        
        data = {
            "sender": {
                "name": settings.BREVO_FROM_NAME,
                "email": settings.BREVO_FROM_EMAIL
            },
            "to": [
                {
                    "email": email,
                    "name": email.split("@")[0]
                }
            ],
            "subject": "🎉 You're All Set - FreeFood UCD",
            "htmlContent": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .container {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 16px;
                        padding: 40px;
                        text-align: center;
                        color: white;
                    }
                    .emoji {
                        font-size: 64px;
                        margin-bottom: 20px;
                    }
                    .title {
                        font-size: 32px;
                        font-weight: bold;
                        margin-bottom: 20px;
                    }
                    .message {
                        font-size: 18px;
                        margin-bottom: 30px;
                        line-height: 1.8;
                    }
                    .features {
                        background: rgba(255,255,255,0.1);
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        text-align: left;
                    }
                    .feature {
                        margin: 15px 0;
                        font-size: 16px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="emoji">🎉</div>
                    <div class="title">Welcome to FreeFood UCD!</div>
                    <div class="message">
                        You're all set! We'll notify you whenever there's free food on campus.
                    </div>
                    
                    <div class="features">
                        <div class="feature">🍕 Get instant notifications about free food events</div>
                        <div class="feature">🎓 From all major UCD societies</div>
                        <div class="feature">⚡ Real-time updates from Instagram</div>
                        <div class="feature">📧 Delivered straight to your inbox</div>
                    </div>
                    
                    <div style="margin-top: 30px; font-size: 14px; opacity: 0.9;">
                        Never miss free food on campus again! 🚀
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=10.0)
            response.raise_for_status()
            
        logger.info(f"Welcome email sent via Brevo to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome email via Brevo: {str(e)}")
        return False

# Made with Bob
