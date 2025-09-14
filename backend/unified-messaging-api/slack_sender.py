"""
Slack message sender with image attachments
"""

import requests
import json
import os
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class SlackSender:
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.base_url = "https://slack.com/api"
        
    def configure_token(self, bot_token: str):
        """Configure Slack bot token"""
        self.bot_token = bot_token
        logger.info("Slack bot token configured")
    
    def send_message(self, channel: str, text: str, images: List[str] = None) -> bool:
        """Send message to Slack channel with optional image attachments"""
        
        if not self.bot_token:
            logger.error("Slack bot token not configured")
            return False
        
        headers = {
            'Authorization': f'Bearer {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Send text message first
            message_payload = {
                'channel': channel,
                'text': text
            }
            
            response = requests.post(
                f"{self.base_url}/chat.postMessage",
                headers=headers,
                json=message_payload
            )
            
            result = response.json()
            
            if not result.get('ok'):
                logger.error(f"Failed to send Slack message: {result.get('error')}")
                return False
            
            logger.info(f"Message sent to Slack channel: {channel}")
            
            # Upload images if provided
            if images:
                for image_path in images:
                    if os.path.exists(image_path):
                        self._upload_file(channel, image_path)
                    else:
                        logger.warning(f"Image not found: {image_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    def _upload_file(self, channel: str, file_path: str) -> bool:
        """Upload file to Slack channel using new v2 API"""
        
        headers = {
            'Authorization': f'Bearer {self.bot_token}'
        }
        
        try:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Step 1: Get upload URL
            upload_data = {
                'filename': filename,
                'length': file_size
            }
            
            response = requests.post(
                f"{self.base_url}/files.getUploadURLExternal",
                headers=headers,
                data=upload_data
            )
            
            result = response.json()
            
            if not result.get('ok'):
                logger.error(f"Failed to get upload URL: {result.get('error')}")
                return False
            
            upload_url = result['upload_url']
            file_id = result['file_id']
            
            # Step 2: Upload file to the URL
            with open(file_path, 'rb') as file_content:
                upload_response = requests.post(upload_url, files={'file': file_content})
            
            if upload_response.status_code != 200:
                logger.error(f"Failed to upload file to URL: {upload_response.status_code}")
                return False
            
            # Step 3: Complete the upload and share to channel
            # Convert channel name to ID if needed
            channel_id = self._get_channel_id(channel) if channel.startswith('#') else channel
            
            complete_data = {
                'files': [{'id': file_id, 'title': f"Image: {filename}"}],
                'channel_id': channel_id,
                'initial_comment': f"Uploaded: {filename}"
            }
            
            complete_response = requests.post(
                f"{self.base_url}/files.completeUploadExternal",
                headers=headers,
                json=complete_data
            )
            
            complete_result = complete_response.json()
            
            if complete_result.get('ok'):
                logger.info(f"File uploaded to Slack: {filename}")
                return True
            else:
                logger.error(f"Failed to complete upload: {complete_result.get('error')}")
                return False
                    
        except Exception as e:
            logger.error(f"Error uploading file to Slack: {e}")
            return False
    
    def _get_channel_id(self, channel_name: str) -> str:
        """Get channel ID from channel name"""
        if channel_name == "#payroll-data-insights":
            return "C09FWRWC3T2"
        return channel_name.replace('#', '')
    
    def get_channels(self) -> List[dict]:
        """Get list of Slack channels"""
        
        if not self.bot_token:
            return []
        
        headers = {
            'Authorization': f'Bearer {self.bot_token}'
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/conversations.list",
                headers=headers
            )
            
            result = response.json()
            
            if result.get('ok'):
                return result.get('channels', [])
            else:
                logger.error(f"Failed to get channels: {result.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting Slack channels: {e}")
            return []
