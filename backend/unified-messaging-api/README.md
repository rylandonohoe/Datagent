# Unified Messaging API 📧💬

A complete email and Slack messaging system with image attachment support.

## Features
- ✅ Email sending with SMTP (Gmail support)
- ✅ Slack messaging with bot integration
- ✅ Image attachments for both platforms
- ✅ Unified API to send to both simultaneously
- ✅ Scheduling support for emails
- ✅ REST API endpoints

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   export SLACK_BOT_TOKEN="your-slack-bot-token"
   ```

3. **Set up email config:**
   - Copy `email_config.json.example` to `email_config.json`
   - Add your email credentials

4. **Start the server:**
   ```bash
   python3 unified_messaging_api.py
   ```

## API Endpoints

- `POST /send-email` - Send email with images
- `POST /send-slack` - Send Slack message with images  
- `POST /send-both` - Send to both platforms
- `GET /slack-channels` - List Slack channels
- `GET /health` - Health check

## Example Usage

```bash
curl -X POST http://localhost:5002/send-both \
  -H "Content-Type: application/json" \
  -d '{
    "email": "recipient@example.com",
    "channel": "#general", 
    "subject": "Test Message",
    "text": "Hello world!",
    "images": ["image1.jpg", "image2.png"]
  }'
```

## Files Overview

- `unified_messaging_api.py` - Main Flask API server
- `email_sender.py` - Email functionality
- `slack_sender.py` - Slack functionality
- `test_*.py` - Test scripts
- Setup guides in `*_setup_guide.md`
