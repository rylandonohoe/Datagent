"""
Abstract AI provider system for easy model switching.
"""

import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv, find_dotenv


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self):
        self.api_key = None
        self.base_url = None
        self._load_config()
    
    @abstractmethod
    def _load_config(self):
        """Load provider-specific configuration."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this AI provider."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass
    
    @abstractmethod
    def call_api(self, prompt: str) -> Dict[str, Any]:
        """Make API call to the AI provider."""
        pass
    
    def create_analysis_prompt(self, user_prompt: str, dataset_context: Dict[str, Any]) -> str:
        """Create a structured prompt for analysis."""
        prompt = f"""
You are a data analysis expert. Analyze the following dataset and respond to the user's request.

DATASET CONTEXT:
- Shape: {dataset_context['shape'][0]} rows, {dataset_context['shape'][1]} columns
- Columns: {', '.join(dataset_context['columns'])}
- Numeric columns: {', '.join(dataset_context['numeric_columns'])}
- Categorical columns: {', '.join(dataset_context['categorical_columns'])}
- Missing values: {sum(dataset_context['missing_values'].values())} total

SAMPLE DATA:
{json.dumps(dataset_context['sample_data'], indent=2)}

USER REQUEST: {user_prompt}

Please provide:
1. Analysis type needed (overview, correlation, distribution, outliers, etc.)
2. Specific columns to analyze
3. Analysis parameters
4. Expected insights

Respond in JSON format:
{{
    "analysis_type": "type_of_analysis",
    "target_columns": ["column1", "column2"],
    "parameters": {{"param1": "value1"}},
    "explanation": "What this analysis will reveal"
}}
"""
        return prompt


class OpenAIProvider(AIProvider):
    """OpenAI GPT-4 provider."""
    
    def _load_config(self):
        load_dotenv(find_dotenv(), override=True)
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4"
    
    def get_provider_name(self) -> str:
        return "OpenAI GPT-4"
    
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    def call_api(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a data analysis expert that provides structured analysis recommendations."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                try:
                    parsed_response = json.loads(ai_response)
                    return parsed_response
                except json.JSONDecodeError:
                    return {
                        "analysis_type": "general",
                        "target_columns": [],
                        "parameters": {},
                        "explanation": ai_response
                    }
            else:
                return {"error": f"API call failed: {response.status_code} - {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}


class TandemProvider(AIProvider):
    """Tandem API provider."""
    
    def _load_config(self):
        load_dotenv(find_dotenv(), override=True)
        self.api_key = os.getenv('TANDEM_API_KEY')
        self.base_url = "https://api.tandemn.com/api/v1"
        # Use DeepSeek distilled Llama-70B model per user request
        self.model = "casperhansen/deepseek-r1-distill-llama-70b-awq"
    
    def get_provider_name(self) -> str:
        return "Tandem (Qwen3-32B)"
    
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    def call_api(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Match the exact API calling pattern requested
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        # Try with increasing timeouts and retries
        timeouts = [120, 120, 120]  # Progressive timeout increases
        
        for attempt, timeout in enumerate(timeouts):
            try:
                if attempt > 0:
                    print(f"🔄 Tandem API retry {attempt + 1}/{len(timeouts)} (timeout: {timeout}s)")
                
                response = requests.post(
                    "https://api.tandemn.com/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result["choices"][0]["message"]["content"]
                    
                    try:
                        parsed_response = json.loads(ai_response)
                        return parsed_response
                    except json.JSONDecodeError:
                        return {
                            "analysis_type": "general",
                            "target_columns": [],
                            "parameters": {},
                            "explanation": ai_response
                        }
                else:
                    if attempt == len(timeouts) - 1:  # Last attempt
                        return {"error": f"API call failed: {response.status_code} - {response.text}"}
                    
            except requests.exceptions.Timeout:
                if attempt == len(timeouts) - 1:  # Last attempt
                    return {"error": f"Tandem API timeout after {timeout}s. Try switching providers: 'provider claude' or 'provider openai'"}
                continue
                
            except requests.exceptions.RequestException as e:
                if attempt == len(timeouts) - 1:  # Last attempt
                    return {"error": f"Network error: {str(e)}. Try switching providers: 'provider claude' or 'provider openai'"}
                continue
        
        return {"error": "All retry attempts failed"}


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider."""
    
    def _load_config(self):
        load_dotenv(find_dotenv(), override=True)
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1"
        self.model = "claude-opus-4-1-20250805"
    
    def get_provider_name(self) -> str:
        return "Claude 4 Sonnet"
    
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    def call_api(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": f"You are a data analysis expert that provides structured analysis recommendations.\n\n{prompt}"
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["content"][0]["text"]
                
                try:
                    parsed_response = json.loads(ai_response)
                    return parsed_response
                except json.JSONDecodeError:
                    return {
                        "analysis_type": "general",
                        "target_columns": [],
                        "parameters": {},
                        "explanation": ai_response
                    }
            else:
                return {"error": f"API call failed: {response.status_code} - {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}


class AIProviderFactory:
    """Factory for creating AI providers."""
    
    _providers = {
        "openai": OpenAIProvider,
        "gpt4": OpenAIProvider,
        "tandem": TandemProvider,
        "claude": ClaudeProvider,
        "anthropic": ClaudeProvider
    }
    
    @classmethod
    def create_provider(cls, provider_name: str) -> AIProvider:
        """Create an AI provider by name."""
        provider_name = provider_name.lower()
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}. Available: {list(cls._providers.keys())}")
        
        return cls._providers[provider_name]()
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def get_configured_providers(cls) -> List[str]:
        """Get list of properly configured providers."""
        configured = []
        for name in cls._providers.keys():
            try:
                provider = cls.create_provider(name)
                if provider.is_configured():
                    configured.append(name)
            except:
                pass
        return configured
