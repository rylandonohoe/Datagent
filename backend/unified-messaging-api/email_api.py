"""
REST API for Email Sending with Image Attachments
Accepts POST requests with email address and images, returns JSON success/failure
"""

from flask import Flask, request, jsonify
import os
import json
import tempfile
import base64
from email_sender import EmailSender
from werkzeug.utils import secure_filename
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize email sender
email_sender = EmailSender()

def load_email_config():
    """Load email configuration from config file"""
    try:
        with open('email_config.json', 'r') as f:
            config = json.load(f)
        
        email_sender.configure_smtp(
            sender_email=config['email_address'],
            sender_password=config['email_password'],
            smtp_server=config.get('smtp_server', 'smtp.gmail.com'),
            smtp_port=config.get('smtp_port', 587)
        )
        return True
    except Exception as e:
        logger.error(f"Failed to load email config: {e}")
        return False

# Load config on startup
if not load_email_config():
    logger.warning("Email config not loaded. API will return errors until configured.")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "email-api",
        "version": "1.0.0"
    })

@app.route('/send-email', methods=['POST'])
def send_email():
    """
    Send email with image attachments
    
    Expected JSON payload:
    {
        "recipient_email": "user@example.com",
        "subject": "Email subject",
        "body": "Email body text",
        "images": ["image1.jpg", "image2.png"]
    }
    """
    
    try:
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        subject = data.get('subject', 'Email from API')
        body = data.get('body', 'This email was sent via API.')
        image_filenames = data.get('images', [])
        
        # Process image filenames - look for files in current directory
        image_paths = []
        for filename in image_filenames:
            if os.path.exists(filename):
                image_paths.append(filename)
                logger.info(f"Found image: {filename}")
            else:
                logger.warning(f"Image not found: {filename}")
                return jsonify({
                    "success": False,
                    "error": f"Image file not found: {filename}"
                }), 400
        
        # Validate required fields
        if not recipient_email:
            return jsonify({
                "success": False,
                "error": "recipient_email is required"
            }), 400
        
        # Send email
        success = email_sender.send_email(
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            images=image_paths if image_paths else None
        )
        
        # Return response
        if success:
            return jsonify({
                "success": True,
                "message": f"Email sent successfully to {recipient_email}",
                "recipient": recipient_email,
                "images_attached": len(image_paths)
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send email. Check server logs for details."
            }), 500
    
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/send-bulk-email', methods=['POST'])
def send_bulk_email():
    """
    Send email to multiple recipients
    
    Expected JSON payload:
    {
        "recipient_emails": ["user1@example.com", "user2@example.com"],
        "subject": "Email subject",
        "body": "Email body text",
        "images": [
            {
                "filename": "image1.jpg", 
                "data": "base64_encoded_image_data"
            }
        ]
    }
    """
    
    try:
        data = request.get_json()
        recipient_emails = data.get('recipient_emails', [])
        subject = data.get('subject', 'Bulk Email from API')
        body = data.get('body', 'This bulk email was sent via API.')
        images_data = data.get('images', [])
        
        if not recipient_emails:
            return jsonify({
                "success": False,
                "error": "recipient_emails array is required"
            }), 400
        
        # Process images
        image_paths = []
        temp_files = []
        
        for img_data in images_data:
            if 'filename' in img_data and 'data' in img_data:
                try:
                    image_bytes = base64.b64decode(img_data['data'])
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f"_{secure_filename(img_data['filename'])}"
                    )
                    temp_file.write(image_bytes)
                    temp_file.close()
                    
                    image_paths.append(temp_file.name)
                    temp_files.append(temp_file.name)
                    
                except Exception as e:
                    logger.error(f"Failed to process image {img_data.get('filename')}: {e}")
                    continue
        
        # Send bulk emails
        results = email_sender.send_bulk_emails(
            recipients=recipient_emails,
            subject=subject,
            body=body,
            images=image_paths if image_paths else None
        )
        
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        # Count successes
        successful_count = sum(results.values())
        
        return jsonify({
            "success": True,
            "message": f"Bulk email completed: {successful_count}/{len(recipient_emails)} sent successfully",
            "results": results,
            "total_recipients": len(recipient_emails),
            "successful_sends": successful_count,
            "images_attached": len(image_paths)
        })
    
    except Exception as e:
        logger.error(f"Bulk email API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/schedule-email', methods=['POST'])
def schedule_email():
    """
    Schedule an email to be sent at a specific time
    
    Expected JSON payload:
    {
        "recipient_email": "user@example.com",
        "subject": "Scheduled Email",
        "body": "Email body",
        "send_time": "09:00",
        "repeat": "daily",
        "images": [...]
    }
    """
    
    try:
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        subject = data.get('subject', 'Scheduled Email')
        body = data.get('body', 'This is a scheduled email.')
        send_time = data.get('send_time')
        repeat = data.get('repeat')
        images_data = data.get('images', [])
        
        if not recipient_email or not send_time:
            return jsonify({
                "success": False,
                "error": "recipient_email and send_time are required"
            }), 400
        
        # Process images (similar to above)
        image_paths = []
        for img_data in images_data:
            if 'filename' in img_data and 'data' in img_data:
                try:
                    image_bytes = base64.b64decode(img_data['data'])
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f"_{secure_filename(img_data['filename'])}"
                    )
                    temp_file.write(image_bytes)
                    temp_file.close()
                    image_paths.append(temp_file.name)
                except:
                    continue
        
        # Schedule email
        email_sender.schedule_email(
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            send_time=send_time,
            images=image_paths if image_paths else None,
            repeat=repeat
        )
        
        # Start scheduler if not already running
        email_sender.start_scheduler()
        
        return jsonify({
            "success": True,
            "message": f"Email scheduled for {recipient_email} at {send_time}",
            "recipient": recipient_email,
            "send_time": send_time,
            "repeat": repeat or "once"
        })
    
    except Exception as e:
        logger.error(f"Schedule email API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/scheduled-jobs', methods=['GET'])
def get_scheduled_jobs():
    """Get list of scheduled email jobs"""
    try:
        jobs = email_sender.get_scheduled_jobs()
        return jsonify({
            "success": True,
            "scheduled_jobs": jobs,
            "total_jobs": len(jobs)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "success": False,
        "error": "File too large. Maximum size is 16MB."
    }), 413

if __name__ == '__main__':
    print("🚀 Starting Email API Server")
    print("📧 Endpoints available:")
    print("  POST /send-email - Send single email with images")
    print("  POST /send-bulk-email - Send to multiple recipients")
    print("  POST /schedule-email - Schedule email for later")
    print("  GET /scheduled-jobs - View scheduled jobs")
    print("  GET /health - Health check")
    print("\n📖 API Documentation: See example_api_usage.py")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
