import logging
import os
from typing import Any, Dict, List, Optional, Union

import resend
from app.common.config import settings
from app.common.email import render_template

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        if self.api_key:
            resend.api_key = self.api_key
        else:
            logger.warning("RESEND_API_KEY is not set. Email sending will fail.")

    def send_email(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        cc_email: Optional[Union[str, List[str]]] = None,
        bcc_email: Optional[Union[str, List[str]]] = None,
    ) -> bool:
        """
        Send an email using Resend API.

        Args:
            to_email: Recipient email address(es)
            subject: Email subject
            template_name: Name of the Jinja2 template to render
            context: Context dictionary for template rendering
            cc_email: CC recipient(s)
            bcc_email: BCC recipient(s)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.api_key:
            logger.error("Cannot send email: RESEND_API_KEY not configured")
            return False

        try:
            # Render the email body
            if context is None:
                context = {}
            html_content = render_template(template_name, context)

            # Prepare parameters
            # Resend expects 'to' to be a list of strings or a single string
            params = {
                "from": settings.EMAIL_FROM,
                "to": to_email,
                "subject": subject,
                "html": html_content,
            }

            if cc_email:
                params["cc"] = cc_email

            if bcc_email:
                params["bcc"] = bcc_email

            # Send
            response = resend.Emails.send(params)  # ty:ignore[invalid-argument-type]

            # Resend returns a dict with 'id' on success
            if response and response.get("id"):
                logger.info(f"Email sent successfully. ID: {response['id']}")
                return True
            else:
                logger.error(f"Failed to send email. Response: {response}")
                return False

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False


# Global instance
email_service = EmailService()
