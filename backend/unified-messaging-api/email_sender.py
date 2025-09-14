"""
Email Sender with Image Attachments and Schedule Integration
Sends emails with images based on a schedule to specified recipients
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os
import json
from datetime import datetime, timedelta
import schedule
import time
import threading
from typing import List, Dict, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = None
        self.sender_password = None
        self.scheduled_jobs = []
        
    def configure_smtp(self, sender_email: str, sender_password: str, 
                      smtp_server: str = None, smtp_port: int = None):
        """Configure SMTP settings"""
        self.sender_email = sender_email
        self.sender_password = sender_password
        if smtp_server:
            self.smtp_server = smtp_server
        if smtp_port:
            self.smtp_port = smtp_port
        
        logger.info(f"SMTP configured for {sender_email}")
    
    def validate_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def create_email_message(self, recipient_email: str, subject: str, 
                           body: str, images: List[str] = None, 
                           html_body: str = None) -> MIMEMultipart:
        """Create email message with optional image attachments"""
        
        # Validate recipient email
        if not self.validate_email(recipient_email):
            raise ValueError(f"Invalid email address: {recipient_email}")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = self.sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Add text body
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # Add HTML body if provided
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # Add image attachments
        if images:
            for image_path in images:
                if os.path.exists(image_path):
                    try:
                        with open(image_path, 'rb') as f:
                            img_data = f.read()
                        
                        # Determine image type
                        image_name = os.path.basename(image_path)
                        image_ext = os.path.splitext(image_path)[1].lower()
                        
                        if image_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                            # Create MIMEImage
                            img = MIMEImage(img_data)
                            img.add_header('Content-Disposition', f'attachment; filename="{image_name}"')
                            msg.attach(img)
                        else:
                            # Create MIMEBase for other file types
                            attachment = MIMEBase('application', 'octet-stream')
                            attachment.set_payload(img_data)
                            encoders.encode_base64(attachment)
                            attachment.add_header('Content-Disposition', f'attachment; filename="{image_name}"')
                            msg.attach(attachment)
                        
                        logger.info(f"Attached image: {image_name}")
                    except Exception as e:
                        logger.error(f"Failed to attach image {image_path}: {e}")
                else:
                    logger.warning(f"Image not found: {image_path}")
        
        return msg
    
    def send_email(self, recipient_email: str, subject: str, body: str, 
                   images: List[str] = None, html_body: str = None) -> bool:
        """Send email with optional image attachments"""
        
        if not self.sender_email or not self.sender_password:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            # Create message
            msg = self.create_email_message(recipient_email, subject, body, images, html_body)
            
            # Create SMTP session
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(self.sender_email, recipient_email, text)
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False
    
    def send_bulk_emails(self, recipients: List[str], subject: str, body: str, 
                        images: List[str] = None, html_body: str = None) -> Dict[str, bool]:
        """Send emails to multiple recipients"""
        results = {}
        
        for recipient in recipients:
            success = self.send_email(recipient, subject, body, images, html_body)
            results[recipient] = success
            
            # Small delay between emails to avoid being flagged as spam
            time.sleep(1)
        
        successful = sum(results.values())
        logger.info(f"Bulk email complete: {successful}/{len(recipients)} emails sent successfully")
        
        return results
    
    def create_html_template(self, title: str, content: str, images: List[str] = None) -> str:
        """Create a basic HTML email template"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ background-color: #f4f4f4; padding: 10px; text-align: center; font-size: 12px; }}
                .image-gallery {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0; }}
                .image-item {{ max-width: 300px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                {content.replace(chr(10), '<br>')}
            </div>
        """
        
        if images:
            html += '<div class="image-gallery">'
            for i, image_path in enumerate(images):
                image_name = os.path.basename(image_path)
                html += f'<div class="image-item"><p>Attachment: {image_name}</p></div>'
            html += '</div>'
        
        html += """
            <div class="footer">
                <p>This email was sent automatically.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def schedule_email(self, recipient_email: str, subject: str, body: str, 
                      send_time: str, images: List[str] = None, 
                      html_body: str = None, repeat: str = None):
        """Schedule an email to be sent at a specific time"""
        
        def send_scheduled_email():
            logger.info(f"Sending scheduled email to {recipient_email}")
            self.send_email(recipient_email, subject, body, images, html_body)
        
        # Parse time format (HH:MM)
        try:
            hour, minute = map(int, send_time.split(':'))
            
            if repeat == 'daily':
                schedule.every().day.at(send_time).do(send_scheduled_email)
                logger.info(f"Scheduled daily email to {recipient_email} at {send_time}")
            elif repeat == 'weekly':
                schedule.every().week.at(send_time).do(send_scheduled_email)
                logger.info(f"Scheduled weekly email to {recipient_email} at {send_time}")
            else:
                # One-time schedule for today or tomorrow
                now = datetime.now()
                scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if scheduled_time <= now:
                    scheduled_time += timedelta(days=1)
                
                schedule.every().day.at(send_time).do(send_scheduled_email).tag(f'onetime_{recipient_email}')
                logger.info(f"Scheduled one-time email to {recipient_email} at {scheduled_time}")
                
                # Remove the job after it runs once
                def remove_job():
                    schedule.clear(f'onetime_{recipient_email}')
                
                schedule.every().day.at(send_time).do(remove_job).tag(f'cleanup_{recipient_email}')
            
            self.scheduled_jobs.append({
                'recipient': recipient_email,
                'subject': subject,
                'time': send_time,
                'repeat': repeat or 'once'
            })
            
        except ValueError:
            logger.error(f"Invalid time format: {send_time}. Use HH:MM format.")
    
    def start_scheduler(self):
        """Start the email scheduler in a background thread"""
        def run_scheduler():
            logger.info("Email scheduler started")
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Email scheduler thread started")
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """Get list of scheduled jobs"""
        return self.scheduled_jobs
    
    def load_schedule_from_file(self, schedule_file: str):
        """Load email schedule from JSON file"""
        try:
            with open(schedule_file, 'r') as f:
                schedule_data = json.load(f)
            
            for item in schedule_data:
                self.schedule_email(
                    recipient_email=item['recipient'],
                    subject=item['subject'],
                    body=item['body'],
                    send_time=item['time'],
                    images=item.get('images', []),
                    html_body=item.get('html_body'),
                    repeat=item.get('repeat')
                )
            
            logger.info(f"Loaded {len(schedule_data)} scheduled emails from {schedule_file}")
            
        except Exception as e:
            logger.error(f"Failed to load schedule from {schedule_file}: {e}")

def main():
    """Demo function"""
    sender = EmailSender()
    
    print("Email Sender Configuration")
    print("=" * 40)
    
    # Get SMTP credentials (in production, use environment variables)
    sender_email = input("Enter your email: ")
    sender_password = input("Enter your app password: ")
    
    sender.configure_smtp(sender_email, sender_password)
    
    # Example usage
    recipient = input("Enter recipient email: ")
    subject = "Test Email with Images"
    body = """
    Hello!
    
    This is a test email sent from the automated email system.
    Please find the attached images.
    
    Best regards,
    Automated Email System
    """
    
    # Example with images (update paths as needed)
    images = []
    image_input = input("Enter image paths (comma-separated, or press Enter to skip): ")
    if image_input.strip():
        images = [path.strip() for path in image_input.split(',')]
    
    # Create HTML version
    html_body = sender.create_html_template(subject, body, images)
    
    # Send email
    success = sender.send_email(recipient, subject, body, images, html_body)
    
    if success:
        print("✅ Email sent successfully!")
    else:
        print("❌ Failed to send email")
    
    # Schedule example
    schedule_choice = input("Schedule a recurring email? (y/n): ")
    if schedule_choice.lower() == 'y':
        send_time = input("Enter time (HH:MM): ")
        repeat = input("Repeat (daily/weekly/once): ")
        
        sender.schedule_email(
            recipient, 
            "Scheduled Email", 
            "This is a scheduled email.", 
            send_time, 
            images, 
            repeat=repeat if repeat != 'once' else None
        )
        
        sender.start_scheduler()
        print(f"📅 Email scheduled for {send_time}")
        print("Scheduler is running... Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nScheduler stopped")

if __name__ == "__main__":
    main()
