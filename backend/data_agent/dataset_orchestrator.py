"""
AI orchestrator for dataset transformations using external libraries.
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import tempfile
import subprocess
import sys
from .ai_providers import AIProvider, AIProviderFactory

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

class DatasetOrchestrator:
    """
    AI orchestrator that can modify datasets using various libraries.
    """
    
    def __init__(self, provider_name: str = "tandem", max_retry_attempts: int = 2, script_only_mode: bool = False):
        self.data = None
        self.data_path = None
        self.ai_provider = None
        self.transformation_history = []
        self.max_retry_attempts = max_retry_attempts
        self.script_only_mode = script_only_mode
        self.available_libraries = {
            "pandas": "Data manipulation and analysis",
            "numpy": "Numerical computing",
            "scikit-learn": "Machine learning preprocessing",
            "pycaret": "Low-code machine learning",
            "darts": "Time series forecasting and analysis",
            "feature-engine": "Feature engineering",
            "imbalanced-learn": "Handling imbalanced datasets",
            "category_encoders": "Categorical encoding"
        }
        self.set_ai_provider(provider_name)
    
    def set_ai_provider(self, provider_name: str) -> bool:
        """Set the AI provider for orchestration."""
        try:
            self.ai_provider = AIProviderFactory.create_provider(provider_name)
            return True
        except ValueError as e:
            print(f"❌ {str(e)}")
            return False
    
    def load_dataset(self, file_path: str) -> bool:
        """Load a dataset from file."""
        try:
            if file_path.endswith('.csv'):
                self.data = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                self.data = pd.read_json(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                self.data = pd.read_excel(file_path)
            else:
                print(f"❌ Unsupported file format: {file_path}")
                return False
            
            self.data_path = file_path
            print(f"✅ Loaded: {self.data.shape[0]:,} rows × {self.data.shape[1]} columns")
            return True
            
        except Exception as e:
            print(f"❌ Error loading dataset: {str(e)}")
            return False
    
    def orchestrate_transformation(self, prompt: str) -> Dict[str, Any]:
        """Use AI to orchestrate dataset transformations with automatic error recovery."""
        if self.data is None:
            return {"error": "No dataset loaded"}
        
        if not self.ai_provider or not self.ai_provider.is_configured():
            return {"error": "AI provider not configured"}
        
        # Try transformation with retry mechanism
        for attempt in range(self.max_retry_attempts + 1):
            try:
                if attempt == 0:
                    # First attempt - use original prompt
                    orchestration_prompt = self._create_orchestration_prompt(prompt)
                    print(f"🎭 {self.ai_provider.get_provider_name()} is orchestrating transformation...")
                else:
                    # Retry attempt - use error recovery prompt
                    print(f"🔄 Attempt {attempt + 1}: AI is analyzing and fixing the error...")
                
                # Get AI recommendation
                ai_response = self.ai_provider.call_api(orchestration_prompt)
                
                if "error" in ai_response:
                    return ai_response
                
                # Clean and parse the AI response
                cleaned_response = self._clean_ai_response(ai_response)
            
                # Execute the transformation (or just validate in script-only mode)
                result = self._execute_transformation(cleaned_response, prompt, attempt)
                
                # In script-only mode, return after first successful code generation
                if self.script_only_mode:
                    if result.get("code_generated"):
                        print("📜 Script generated successfully (no data modified)")
                        self.transformation_history.append({
                            "prompt": prompt,
                            "timestamp": datetime.now().isoformat(),
                            "ai_recommendation": cleaned_response,
                            "result": result,
                            "attempts": attempt + 1,
                            "script_only": True
                        })
                        return result
                
                # If execution succeeded, store in history and return
                elif result.get("execution_result", {}).get("status") == "success":
                    self.transformation_history.append({
                        "prompt": prompt,
                        "timestamp": datetime.now().isoformat(),
                        "ai_recommendation": cleaned_response,
                        "result": result,
                        "attempts": attempt + 1
                    })
                    
                    if attempt > 0:
                        print(f"✅ Fixed! Transformation completed on attempt {attempt + 1}")
                    
                    return result
                
                # If execution failed and we have retries left, prepare error recovery prompt
                elif attempt < self.max_retry_attempts:
                    error_msg = result.get("execution_result", {}).get("error", "Unknown error")
                    failed_code = result.get("code_generated", "")
                    orchestration_prompt = self._create_error_recovery_prompt(prompt, failed_code, error_msg)
                else:
                    # No more retries, return the failed result
                    self.transformation_history.append({
                        "prompt": prompt,
                        "timestamp": datetime.now().isoformat(),
                        "ai_recommendation": cleaned_response,
                        "result": result,
                        "attempts": attempt + 1,
                        "final_status": "failed"
                    })
                    return result
                    
            except Exception as e:
                if attempt < self.max_retry_attempts:
                    print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
                    continue
                else:
                    return {"error": f"Orchestration failed after {self.max_retry_attempts + 1} attempts: {str(e)}"}
        
        return {"error": "Maximum retry attempts exceeded"}
    
    def _clean_ai_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and parse AI response that may contain thinking tags and markdown."""
        if isinstance(ai_response, dict) and "explanation" in ai_response:
            explanation = ai_response["explanation"]
            
            # Remove thinking tags
            if "<think>" in explanation:
                explanation = explanation.split("</think>")[-1].strip()
            
            # Extract JSON from markdown code blocks
            if "```json" in explanation:
                start_idx = explanation.find("```json") + 7
                end_idx = explanation.find("```", start_idx)
                if end_idx != -1:
                    json_str = explanation[start_idx:end_idx].strip()
                    try:
                        parsed_json = json.loads(json_str)
                        return parsed_json
                    except json.JSONDecodeError:
                        pass
            
            # Try to find JSON object in the explanation
            try:
                start_idx = explanation.find('{')
                end_idx = explanation.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = explanation[start_idx:end_idx]
                    parsed_json = json.loads(json_str)
                    return parsed_json
            except json.JSONDecodeError:
                pass
        
        return ai_response
    
    def _create_orchestration_prompt(self, user_prompt: str) -> str:
        """Create a comprehensive orchestration prompt."""
        # Get dataset context
        dataset_context = self._get_dataset_context()
        
        prompt = f"""
You are an expert data scientist orchestrator. Given a dataset and user request, you need to:
1. Understand what transformation/analysis is needed
2. Choose the appropriate libraries and methods
3. Generate executable Python code
4. Provide clear explanations

DATASET CONTEXT:
- Shape: {dataset_context['shape'][0]} rows, {dataset_context['shape'][1]} columns
- Columns: {', '.join(dataset_context['columns'])}
- Data types: {dataset_context['dtypes']}
- Missing values: {dataset_context['missing_summary']}
- Sample data: {json.dumps(dataset_context['sample_data'], indent=2)}

AVAILABLE LIBRARIES:
{json.dumps(self.available_libraries, indent=2)}

USER REQUEST: {user_prompt}

Respond with a JSON object containing:
{{
    "transformation_type": "preprocessing|feature_engineering|modeling|time_series|cleaning|analysis",
    "libraries_needed": ["library1", "library2"],
    "explanation": "What this transformation will do and why",
    "code": "# Complete Python code to execute the transformation\\nimport pandas as pd\\n# ... rest of code",
    "expected_changes": "Description of expected dataset changes",
    "output_columns": ["list", "of", "new", "or", "modified", "columns"],
    "save_result": true/false
}}

IMPORTANT:
- Generate complete, executable Python code
- Use 'df' as the dataframe variable name
- Include all necessary imports
- Handle errors gracefully
- For time series: use darts library
- For ML preprocessing: use pycaret or scikit-learn
- For feature engineering: use feature-engine or pandas
- Code should modify the dataframe in-place or return a new one
"""
        return prompt
    
    def _create_error_recovery_prompt(self, original_prompt: str, failed_code: str, error_message: str) -> str:
        """Create a prompt for AI to analyze and fix code errors."""
        dataset_context = self._get_dataset_context()
        
        prompt = f"""
You are an expert data scientist debugging code. A previous transformation attempt failed and you need to analyze the error and generate fixed code.

ORIGINAL USER REQUEST: {original_prompt}

DATASET CONTEXT:
- Shape: {dataset_context['shape'][0]} rows, {dataset_context['shape'][1]} columns
- Columns: {', '.join(dataset_context['columns'])}
- Data types: {dataset_context['dtypes']}
- Missing values: {dataset_context['missing_summary']}
- Sample data: {json.dumps(dataset_context['sample_data'], indent=2)}

FAILED CODE:
```python
{failed_code}
```

ERROR MESSAGE:
{error_message}

AVAILABLE LIBRARIES:
{json.dumps(self.available_libraries, indent=2)}

Please analyze the error and provide a corrected solution. Respond with a JSON object containing:
{{
    "error_analysis": "Detailed explanation of what went wrong",
    "transformation_type": "preprocessing|feature_engineering|modeling|time_series|cleaning|analysis",
    "libraries_needed": ["library1", "library2"],
    "explanation": "What the corrected transformation will do",
    "code": "# Fixed Python code that addresses the error\\nimport pandas as pd\\n# ... rest of corrected code",
    "fixes_applied": ["fix1", "fix2", "fix3"],
    "expected_changes": "Description of expected dataset changes",
    "output_columns": ["list", "of", "new", "or", "modified", "columns"],
    "save_result": true/false
}}

CRITICAL REQUIREMENTS:
- Fix the specific error that occurred
- Generate complete, executable Python code
- Use 'df' as the dataframe variable name
- Include all necessary imports
- Handle edge cases and potential errors
- Test your logic mentally before responding
- Do NOT create sample data - work with the loaded dataframe 'df'
- Ensure the code actually performs the requested transformation
"""
        return prompt
    
    def _get_dataset_context(self) -> Dict[str, Any]:
        """Get comprehensive dataset context."""
        return {
            "shape": self.data.shape,
            "columns": self.data.columns.tolist(),
            "dtypes": self.data.dtypes.astype(str).to_dict(),
            "missing_summary": f"{self.data.isnull().sum().sum()} total missing values",
            "sample_data": self.data.head(3).to_dict('records')
        }
    
    def _execute_transformation(self, ai_response: Dict[str, Any], original_prompt: str, attempt: int = 0) -> Dict[str, Any]:
        """Execute the AI-recommended transformation."""
        transformation_type = ai_response.get("transformation_type", "unknown")
        libraries_needed = ai_response.get("libraries_needed", [])
        explanation = ai_response.get("explanation", "AI-recommended transformation")
        code = ai_response.get("code", "")
        expected_changes = ai_response.get("expected_changes", "")
        output_columns = ai_response.get("output_columns", [])
        save_result = ai_response.get("save_result", False)
        
        result = {
            "transformation_info": {
                "type": transformation_type,
                "explanation": explanation,
                "expected_changes": expected_changes,
                "libraries_used": libraries_needed,
                "provider": self.ai_provider.get_provider_name(),
                "attempt": attempt + 1,
                "error_analysis": ai_response.get("error_analysis", ""),
                "fixes_applied": ai_response.get("fixes_applied", [])
            },
            "code_generated": code,
            "execution_result": None,
            "dataset_changes": None
        }
        
        if not code:
            result["execution_result"] = {"error": "No code generated by AI"}
            return result
        
        # Execute the transformation (or skip in script-only mode)
        if self.script_only_mode:
            # In script-only mode, just validate the code syntax without executing
            try:
                compile(code, '<string>', 'exec')
                result["execution_result"] = {"status": "success", "message": "Script generated and validated (not executed)"}
                result["dataset_changes"] = {"note": "No changes - script-only mode"}
            except SyntaxError as e:
                result["execution_result"] = {"error": f"Code syntax error: {str(e)}"}
        else:
            # Normal execution mode
            try:
                # Store original data info
                original_shape = self.data.shape
                original_columns = self.data.columns.tolist()
                
                # Create execution environment
                exec_globals = {
                    'pd': pd,
                    'np': np,
                    'df': self.data.copy(),
                    '__builtins__': __builtins__
                }
                
                # Try to import required libraries
                for lib in libraries_needed:
                    try:
                        if lib == "scikit-learn":
                            exec(f"import sklearn", exec_globals)
                        elif lib == "feature-engine":
                            exec(f"import feature_engine as fe", exec_globals)
                        elif lib == "imbalanced-learn":
                            exec(f"import imblearn", exec_globals)
                        elif lib == "category_encoders":
                            exec(f"import category_encoders as ce", exec_globals)
                        else:
                            exec(f"import {lib}", exec_globals)
                    except ImportError:
                        result["execution_result"] = {"error": f"Library {lib} not installed"}
                        return result
                
                # Execute the code
                exec(code, exec_globals)
                
                # Get the modified dataframe
                modified_df = exec_globals['df']
                
                # Update the dataset
                self.data = modified_df
                
                # Calculate changes
                new_shape = self.data.shape
                new_columns = self.data.columns.tolist()
                
                changes = {
                    "shape_change": f"{original_shape} → {new_shape}",
                    "rows_added": new_shape[0] - original_shape[0],
                    "columns_added": new_shape[1] - original_shape[1],
                    "new_columns": [col for col in new_columns if col not in original_columns],
                    "removed_columns": [col for col in original_columns if col not in new_columns]
                }
                
                result["execution_result"] = {"status": "success", "message": "Transformation completed successfully"}
                result["dataset_changes"] = changes
                
                # Save result if requested
                if save_result:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = f"data/transformed_{timestamp}.csv"
                    self.data.to_csv(output_path, index=False)
                    result["saved_to"] = output_path
                
            except Exception as e:
                result["execution_result"] = {"error": f"Code execution failed: {str(e)}"}
        
        return result
    
    def get_transformation_history(self) -> List[Dict[str, Any]]:
        """Get the history of transformations."""
        return self.transformation_history
    
    def save_current_dataset(self, file_path: Optional[str] = None) -> str:
        """Save the current dataset."""
        if self.data is None:
            raise ValueError("No dataset loaded")
        
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"data/dataset_{timestamp}.csv"
        
        self.data.to_csv(file_path, index=False)
        return file_path
    
    def generate_transformation_script(self, transformations: List[str]) -> str:
        """Generate a complete script for multiple transformations."""
        if not self.ai_provider or not self.ai_provider.is_configured():
            return "# Error: AI provider not configured"
        
        script_prompt = f"""
Generate a complete Python script that performs the following transformations on a dataset:

TRANSFORMATIONS REQUESTED:
{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(transformations))}

AVAILABLE LIBRARIES:
{json.dumps(self.available_libraries, indent=2)}

Generate a complete Python script with:
1. All necessary imports
2. Data loading function
3. Each transformation as a separate function
4. Main execution flow
5. Error handling
6. Comments explaining each step

The script should be ready to run independently.
"""
                
        try:
            response = self.ai_provider.call_api(script_prompt)
            if isinstance(response, dict) and "code" in response:
                return response["code"]
            elif isinstance(response, dict) and "explanation" in response:
                return response["explanation"]
            else:
                return str(response)
        except Exception as e:
            return f"# Error generating script: {str(e)}"
    
    def clear_history(self):
        """Clear transformation history."""
        self.transformation_history = []
    
    def set_script_only_mode(self, enabled: bool):
        """Toggle script-only mode on/off."""
        self.script_only_mode = enabled
        mode_status = "enabled" if enabled else "disabled"
        print(f"📜 Script-only mode {mode_status}")
    
    def is_script_only_mode(self) -> bool:
        """Check if script-only mode is enabled."""
        return self.script_only_mode
