"""
Notification services for email and webhook notifications
Includes real Resend email service and mock webhook service
"""

import logging
from typing import Dict, Any, Optional
import asyncio
import json
from datetime import datetime

import resend
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# MockEmailService class removed - using only ResendEmailService


class ResendEmailService:
    """Real email service using Resend API"""

    def __init__(self):
        if not settings.resend_api_key:
            raise ValueError("RESEND_API_KEY not configured in environment variables")

        resend.api_key = settings.resend_api_key
        logger.info("ResendEmailService initialized successfully")

    async def send_completion_email(self, recipient: str, job_data: Dict[str, Any]) -> bool:
        """
        Send real email notification for job completion using Resend

        Args:
            recipient: Email address
            job_data: Job information dictionary

        Returns:
            bool: Success status
        """
        try:
            voice_name = job_data.get('voice_name', 'Your Voice')
            job_id = job_data.get('job_id', 'Unknown')

            # Create MyMemori.es branded email content
            html_content = self._generate_completion_email_html(job_data)

            params = {
                "from": f"{settings.from_name} <{settings.from_email}>",
                "to": [recipient],
                "subject": f"Your personal story is ready to listen! 🎙️",
                "html": html_content,
                "tags": [
                    {"name": "job_type", "value": "voice_cloning"},
                    {"name": "job_id", "value": job_id},
                    {"name": "service", "value": "mymemories"}
                ]
            }

            # Send email via Resend
            email_response = resend.Emails.send(params)

            if email_response and email_response.get('id'):
                logger.info(f"Email sent successfully to {recipient} for job {job_id}. Email ID: {email_response['id']}")
                return True
            else:
                logger.error(f"Failed to send email to {recipient}: No email ID returned")
                return False

        except Exception as e:
            logger.error(f"Failed to send completion email to {recipient}: {e}")
            return False

    async def send_error_email(self, recipient: str, job_data: Dict[str, Any], error_message: str) -> bool:
        """Send error notification email via Resend"""
        try:
            voice_name = job_data.get('voice_name', 'Your Voice')
            job_id = job_data.get('job_id', 'Unknown')

            html_content = self._generate_error_email_html(job_data, error_message)

            params = {
                "from": f"{settings.from_name} <{settings.from_email}>",
                "to": [recipient],
                "subject": f"MyMemori.es: We need to try your story again",
                "html": html_content,
                "tags": [
                    {"name": "job_type", "value": "voice_cloning_error"},
                    {"name": "job_id", "value": job_id},
                    {"name": "service", "value": "mymemories"}
                ]
            }

            email_response = resend.Emails.send(params)

            if email_response and email_response.get('id'):
                logger.info(f"Error email sent successfully to {recipient} for job {job_id}")
                return True
            else:
                logger.error(f"Failed to send error email to {recipient}")
                return False

        except Exception as e:
            logger.error(f"Failed to send error email to {recipient}: {e}")
            return False

    def _generate_completion_email_html(self, job_data: Dict[str, Any]) -> str:
        """Generate MyMemori.es branded completion email HTML"""
        voice_name = job_data.get('voice_name', 'Your Voice')
        job_id = job_data.get('job_id', 'Unknown')

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Your MyMemori.es Story is Ready!</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 600;">🎙️ Your Story is Ready!</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">MyMemori.es has created your personal story in your own voice</p>
            </div>

            <div style="background: #f8f9fa; padding: 25px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #5a6c7d; margin-top: 0; font-size: 20px;">Your Story Details</h2>
                <p style="margin: 5px 0;"><strong>Story Name:</strong> {voice_name}</p>
                <p style="margin: 5px 0;"><strong>Reference:</strong> {job_id}</p>
                <p style="margin: 5px 0;"><strong>Completed:</strong> {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://mymemori.es/story/{job_id}" style="display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">
                    🎧 Listen to Your Story
                </a>
            </div>

            <div style="background: #e3f2fd; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h3 style="color: #1976d2; margin-top: 0; font-size: 16px;">What's Next?</h3>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Listen to your complete story online</li>
                    <li>Download the recording for offline listening</li>
                    <li>Share your memory with family and friends</li>
                    <li>Create more stories to preserve your memories</li>
                </ul>
            </div>

            <div style="text-align: center; padding: 20px 0; border-top: 1px solid #eee; margin-top: 30px; color: #666; font-size: 14px;">
                <p>Thank you for using MyMemori.es to preserve your precious memories!</p>
                <p style="margin: 10px 0;">
                    <a href="https://mymemori.es" style="color: #667eea; text-decoration: none;">MyMemori.es</a> |
                    <a href="https://mymemori.es/support" style="color: #667eea; text-decoration: none;">Support</a>
                </p>
                <p style="font-size: 12px; color: #999;">This is an automated message. Please do not reply to this email.</p>
            </div>

        </body>
        </html>
        """

    def _generate_error_email_html(self, job_data: Dict[str, Any], error_message: str) -> str:
        """Generate MyMemori.es branded error email HTML"""
        voice_name = job_data.get('voice_name', 'Your Voice')
        job_id = job_data.get('job_id', 'Unknown')

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MyMemori.es: Issue with Your Story</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 600;">📞 Let's Try Your Story Again</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">We had a small issue processing your story, but we can easily fix this</p>
            </div>

            <div style="background: #f8f9fa; padding: 25px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #5a6c7d; margin-top: 0; font-size: 20px;">Issue Details</h2>
                <p style="margin: 5px 0;"><strong>Voice Name:</strong> {voice_name}</p>
                <p style="margin: 5px 0;"><strong>Job ID:</strong> {job_id}</p>
                <p style="margin: 5px 0;"><strong>Error:</strong> {error_message}</p>
                <p style="margin: 5px 0;"><strong>Time:</strong> {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</p>
            </div>

            <div style="background: #fff3cd; border: 1px solid #ffeeba; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h3 style="color: #856404; margin-top: 0; font-size: 16px;">Don't worry, here's what to do:</h3>
                <ul style="margin: 10px 0; padding-left: 20px; color: #856404;">
                    <li>Please try creating your story again with the same audio recordings</li>
                    <li>Make sure your audio recordings are clear</li>
                    <li>If you still have trouble, our friendly support team is here to help</li>
                </ul>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://mymemori.es/create" style="display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">
                    Try Again
                </a>
            </div>

            <div style="text-align: center; padding: 20px 0; border-top: 1px solid #eee; margin-top: 30px; color: #666; font-size: 14px;">
                <p>Need help? Our support team is here to assist you.</p>
                <p style="margin: 10px 0;">
                    <a href="https://mymemori.es" style="color: #667eea; text-decoration: none;">MyMemori.es</a> |
                    <a href="https://mymemori.es/support" style="color: #667eea; text-decoration: none;">Contact Support</a>
                </p>
            </div>

        </body>
        </html>
        """


class MockWebhookService:
    """Mock webhook service for development and testing"""

    def __init__(self):
        self.sent_webhooks = []  # Store sent webhooks for testing/debugging

    async def send_completion_webhook(self, webhook_url: str, job_data: Dict[str, Any]) -> bool:
        """
        Send mock webhook notification for job completion

        Args:
            webhook_url: Webhook endpoint URL
            job_data: Job information dictionary

        Returns:
            bool: Success status
        """
        try:
            # Simulate HTTP request delay
            await asyncio.sleep(0.2)

            webhook_payload = {
                "event": "voice_cloning_completed",
                "timestamp": datetime.utcnow().isoformat(),
                "job_id": job_data.get("job_id"),
                "voice_id": job_data.get("voice_id"),
                "voice_name": job_data.get("voice_name"),
                "status": job_data.get("status", "completed"),
                "output_file": job_data.get("output_file"),
                "file_size": job_data.get("file_size"),
                "duration": job_data.get("duration"),
                "created_at": job_data.get("created_at"),
                "completed_at": job_data.get("completed_at")
            }

            webhook_record = {
                "url": webhook_url,
                "payload": webhook_payload,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent"
            }

            # Store for debugging (in production, this would make HTTP POST request)
            self.sent_webhooks.append(webhook_record)

            logger.info(f"Mock webhook sent to {webhook_url} for job {job_data.get('job_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send mock webhook to {webhook_url}: {e}")
            return False

    async def send_error_webhook(self, webhook_url: str, job_data: Dict[str, Any], error_message: str) -> bool:
        """Send error notification webhook"""
        try:
            await asyncio.sleep(0.2)

            webhook_payload = {
                "event": "voice_cloning_failed",
                "timestamp": datetime.utcnow().isoformat(),
                "job_id": job_data.get("job_id"),
                "voice_name": job_data.get("voice_name"),
                "status": "failed",
                "error_message": error_message,
                "created_at": job_data.get("created_at"),
                "failed_at": datetime.utcnow().isoformat()
            }

            webhook_record = {
                "url": webhook_url,
                "payload": webhook_payload,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent"
            }

            self.sent_webhooks.append(webhook_record)
            logger.info(f"Mock error webhook sent to {webhook_url} for job {job_data.get('job_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send error webhook to {webhook_url}: {e}")
            return False

    def get_sent_webhooks(self) -> list:
        """Get list of sent webhooks (for testing)"""
        return self.sent_webhooks

    def clear_sent_webhooks(self):
        """Clear sent webhooks list (for testing)"""
        self.sent_webhooks.clear()


class NotificationManager:
    """Unified notification manager for email and webhook services"""

    def __init__(self):
        # Always use ResendEmailService for real emails
        try:
            self.email_service = ResendEmailService()
            logger.info("Using ResendEmailService for production emails")
        except Exception as e:
            logger.error(f"Failed to initialize ResendEmailService: {e}")
            logger.error("Email notifications will not work. Please check your RESEND_API_KEY configuration.")
            self.email_service = None

        # Keep webhook service as mock for now
        self.webhook_service = MockWebhookService() if settings.mock_webhook_enabled else None

    async def notify_job_completion(self, job_data: Dict[str, Any],
                                  email: Optional[str] = None,
                                  webhook_url: Optional[str] = None) -> Dict[str, bool]:
        """
        Send completion notifications via email and/or webhook

        Returns:
            Dict with email and webhook success status
        """
        results = {"email": False, "webhook": False}

        # Send email notification
        if email and self.email_service:
            results["email"] = await self.email_service.send_completion_email(email, job_data)

        # Send webhook notification
        if webhook_url and self.webhook_service:
            results["webhook"] = await self.webhook_service.send_completion_webhook(webhook_url, job_data)

        return results

    async def notify_job_failure(self, job_data: Dict[str, Any], error_message: str,
                               email: Optional[str] = None,
                               webhook_url: Optional[str] = None) -> Dict[str, bool]:
        """
        Send failure notifications via email and/or webhook

        Returns:
            Dict with email and webhook success status
        """
        results = {"email": False, "webhook": False}

        # Send error email
        if email and self.email_service:
            results["email"] = await self.email_service.send_error_email(email, job_data, error_message)

        # Send error webhook
        if webhook_url and self.webhook_service:
            results["webhook"] = await self.webhook_service.send_error_webhook(webhook_url, job_data, error_message)

        return results

    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        stats = {
            "email_enabled": self.email_service is not None,
            "webhook_enabled": self.webhook_service is not None,
            "sent_emails": "N/A - Using real email service",
            "sent_webhooks": len(self.webhook_service.sent_webhooks) if self.webhook_service and hasattr(self.webhook_service, 'sent_webhooks') else 0
        }
        return stats


# Global notification manager instance
notification_manager = NotificationManager()


def get_notification_manager() -> NotificationManager:
    """Get global notification manager instance"""
    return notification_manager