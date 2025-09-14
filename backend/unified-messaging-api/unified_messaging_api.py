"""
Unified API for sending messages to both Email and Slack
"""

from flask import Flask, request, jsonify
import os
import json
import logging
from email_sender import EmailSender
from slack_sender import SlackSender

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize senders
email_sender = EmailSender()
slack_sender = SlackSender()

def load_config():
    """Load email and Slack configuration.
    Priority:
      1) email_config.json if present
      2) SMTP_SENDER_EMAIL / SMTP_SENDER_PASSWORD env vars
    Slack token from SLACK_BOT_TOKEN env.
    """
    ok = True
    # Email
    try:
        if os.path.exists('email_config.json'):
            with open('email_config.json', 'r') as f:
                email_config = json.load(f)
            email_sender.configure_smtp(
                sender_email=email_config['email_address'],
                sender_password=email_config['email_password'],
                smtp_server=email_config.get('smtp_server', 'smtp.gmail.com'),
                smtp_port=email_config.get('smtp_port', 587)
            )
            logger.info("Email configured from email_config.json")
        else:
            env_email = os.getenv('SMTP_SENDER_EMAIL')
            env_pass = os.getenv('SMTP_SENDER_PASSWORD')
            if env_email and env_pass:
                email_sender.configure_smtp(env_email, env_pass)
                logger.info("Email configured from environment variables")
            else:
                logger.warning("No email configuration found (email_config.json or env). Email sending may fail.")
    except Exception as e:
        logger.error(f"Failed to configure email: {e}")
        ok = False

    # Slack
    try:
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if slack_token:
            slack_sender.configure_token(slack_token)
            logger.info("Slack token configured from environment")
        else:
            logger.warning("SLACK_BOT_TOKEN not set; Slack sending may fail.")
    except Exception as e:
        logger.error(f"Failed to configure Slack: {e}")
        ok = False

    return ok

# Load config on startup
load_config()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "unified-messaging-api",
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
        
        # Process image filenames
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
                "platform": "email",
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
        logger.error(f"Email API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/send-slack', methods=['POST'])
def send_slack():
    """
    Send Slack message with image attachments
    
    Expected JSON payload:
    {
        "channel": "#general",
        "text": "Message text",
        "images": ["image1.jpg", "image2.png"]
    }
    """
    
    try:
        data = request.get_json()
        channel = data.get('channel')
        text = data.get('text', 'This message was sent via API.')
        image_filenames = data.get('images', [])
        
        # Process image filenames
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
        if not channel:
            return jsonify({
                "success": False,
                "error": "channel is required"
            }), 400
        
        # Send Slack message
        success = slack_sender.send_message(
            channel=channel,
            text=text,
            images=image_paths if image_paths else None
        )
        
        # Return response
        if success:
            return jsonify({
                "success": True,
                "platform": "slack",
                "message": f"Message sent successfully to {channel}",
                "channel": channel,
                "images_attached": len(image_paths)
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send Slack message. Check server logs for details."
            }), 500
    
    except Exception as e:
        logger.error(f"Slack API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/send-both', methods=['POST'])
def send_both():
    """
    Send to both email and Slack
    
    Expected JSON payload:
    {
        "recipient_email": "user@example.com",
        "slack_channel": "#general",
        "subject": "Email subject",
        "text": "Message text",
        "images": ["image1.jpg", "image2.png"]
    }
    """
    
    try:
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        slack_channel = data.get('slack_channel')
        subject = data.get('subject', 'Message from API')
        text = data.get('text', 'This message was sent via API.')
        image_filenames = data.get('images', [])
        
        # Process image filenames
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
        if not recipient_email and not slack_channel:
            return jsonify({
                "success": False,
                "error": "Either recipient_email or slack_channel is required"
            }), 400
        
        results = {}
        
        # Send email if recipient provided
        if recipient_email:
            email_success = email_sender.send_email(
                recipient_email=recipient_email,
                subject=subject,
                body=text,
                images=image_paths if image_paths else None
            )
            results['email'] = {
                "success": email_success,
                "recipient": recipient_email
            }
        
        # Send Slack if channel provided
        if slack_channel:
            slack_success = slack_sender.send_message(
                channel=slack_channel,
                text=text,
                images=image_paths if image_paths else None
            )
            results['slack'] = {
                "success": slack_success,
                "channel": slack_channel
            }
        
        # Check overall success
        all_successful = all(result['success'] for result in results.values())
        
        return jsonify({
            "success": all_successful,
            "platform": "both",
            "message": "Messages sent to multiple platforms",
            "results": results,
            "images_attached": len(image_paths)
        })
    
    except Exception as e:
        logger.error(f"Multi-platform API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/slack-channels', methods=['GET'])
def get_slack_channels():
    """Get list of available Slack channels"""
    try:
        channels = slack_sender.get_channels()
        return jsonify({
            "success": True,
            "channels": [{"id": ch["id"], "name": ch["name"]} for ch in channels if not ch.get("is_archived")]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Unified Messaging API Server")
    print("📧 Email & 💬 Slack Integration")
    print("=" * 50)
    print("📧 Endpoints available:")
    print("  POST /send-email - Send email with images")
    print("  POST /send-slack - Send Slack message with images")
    print("  POST /send-both - Send to both email and Slack")
    print("  GET /slack-channels - List Slack channels")
    print("  GET /health - Health check")
    print("\n📖 Setup Guide:")
    print("  1. Email: Configure email_config.json")
    print("  2. Slack: Set SLACK_BOT_TOKEN environment variable")
    
    app.run(debug=True, host='0.0.0.0', port=5002)
