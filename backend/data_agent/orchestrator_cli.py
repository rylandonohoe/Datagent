"""
Command-line interface for AI Dataset Orchestrator.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
from .dataset_orchestrator import DatasetOrchestrator


class OrchestratorCLI:
    """Command-line interface for AI dataset orchestration."""
    
    def __init__(self):
        self.orchestrator = DatasetOrchestrator()
        self.running = True
        # cumulative pipeline file path
        self.output_dir = os.path.join(os.path.dirname(__file__), "output")
        self.pipeline_path = os.path.join(self.output_dir, "pipeline.py")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def start(self):
        """Start the interactive CLI."""
        print("🎭 AI Dataset Orchestrator")
        print("=" * 50)
        print("Commands:")
        print("  load <file_path>     - Load a dataset")
        print("  provider <name>      - Switch AI provider (tandem, claude, openai)")
        print("  transform <prompt>   - AI-orchestrated dataset transformation")
        print("  script <prompts>     - Generate transformation script")
        print("  save [file_path]     - Save current dataset")
        print("  history              - Show transformation history")
        print("  status               - Show current status")
        print("  help                 - Show this help")
        print("  exit                 - Exit the orchestrator")
        print("\nExample transformations:")
        print("  'Remove outliers from numerical columns'")
        print("  'Create time series features for forecasting'")
        print("  'Encode categorical variables for ML'")
        print("  'Balance the dataset using SMOTE'")
        print("=" * 50)
        
        self.show_status()
        
        while self.running:
            try:
                user_input = input(f"\n🎭 Orchestrator> ").strip()
                if not user_input:
                    continue
                
                if not self.process_input(user_input):
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                break
    
    def process_input(self, user_input: str) -> bool:
        """Process user input and return False if should exit."""
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Handle commands
        if command == "exit" or command == "quit":
            print("👋 Goodbye!")
            return False
        
        elif command == "help":
            self.show_help()
            return True
        
        elif command == "load":
            if not args:
                print("❌ Usage: load <file_path>")
                return True
            
            if self.orchestrator.load_dataset(args):
                print(f"📊 Dataset loaded successfully!")
                print(f"   Shape: {self.orchestrator.data.shape}")
                print(f"   Columns: {', '.join(self.orchestrator.data.columns.tolist()[:5])}{'...' if len(self.orchestrator.data.columns) > 5 else ''}")
            return True
        
        elif command == "provider":
            if not args:
                print("❌ Usage: provider <name>")
                print("   Available: tandem, claude, openai")
                return True
            
            if self.orchestrator.set_ai_provider(args):
                print(f"✅ Switched to {self.orchestrator.ai_provider.get_provider_name()}")
            return True
        
        elif command == "script-only":
            if not args:
                # Toggle mode
                new_mode = not self.orchestrator.is_script_only_mode()
                self.orchestrator.set_script_only_mode(new_mode)
            else:
                # Set specific mode
                enabled = args.lower() in ['true', 'on', 'yes', '1', 'enable']
                self.orchestrator.set_script_only_mode(enabled)
            return True
        
        elif command == "transform":
            if not args:
                print("❌ Usage: transform <transformation_prompt>")
                print("   Example: transform 'Remove outliers and normalize data'")
                return True
            
            if self.orchestrator.data is None:
                print("❌ Please load a dataset first using: load <file_path>")
                return True
            
            if not self.orchestrator.ai_provider or not self.orchestrator.ai_provider.is_configured():
                print("❌ AI provider not configured. Set appropriate API key.")
                return True
            # Build a contextual prompt that includes previous steps
            contextual_prompt = self._build_contextual_prompt(args)
            result = self.orchestrator.orchestrate_transformation(contextual_prompt)
            print(self.format_transformation_output(result))
            # If success, append code to the cumulative pipeline file
            exec_result = result.get("execution_result", {}) if isinstance(result, dict) else {}
            if exec_result.get("status") == "success":
                self._append_to_pipeline(original_prompt=args, result=result)
            return True
        
        elif command == "script":
            if not args:
                print("❌ Usage: script <transformation1; transformation2; ...>")
                print("   Example: script 'Remove outliers; Encode categories; Scale features'")
                return True
            
            transformations = [t.strip() for t in args.split(';')]
            print(f"🎭 Generating transformation script...")
            script = self.orchestrator.generate_transformation_script(transformations)
            print("\n📜 Generated Script:")
            print("=" * 50)
            print(script)
            print("=" * 50)
            return True
        
        elif command == "save":
            if self.orchestrator.data is None:
                print("❌ No dataset loaded to save")
                return True
            
            try:
                file_path = self.orchestrator.save_current_dataset(args if args else None)
                print(f"✅ Dataset saved to: {file_path}")
            except Exception as e:
                print(f"❌ Error saving dataset: {str(e)}")
            return True
        
        elif command == "history":
            self.show_history()
            return True
        
        elif command == "status":
            self.show_status()
            return True
        
        elif command == "execute":
            # Execute a final pipeline from a JSON file describing blocks
            if not args:
                print("❌ Usage: execute <path_to_blocks.json>")
                return True
            path = args.strip().strip('"\'')
            if not os.path.exists(path):
                print(f"❌ JSON file not found: {path}")
                return True
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    blocks = json.load(f)
            except Exception as e:
                print(f"❌ Failed to read JSON: {e}")
                return True

            # Ensure provider is configured before execution
            if not self.orchestrator.ai_provider or not self.orchestrator.ai_provider.is_configured():
                print("❌ AI provider not configured. Use: provider <tandem|openai|claude>")
                return True

            print("🚀 Executing pipeline graph...")
            result = self.orchestrator.execute_final_pipeline(blocks)
            if 'error' in result:
                print("❌ Pipeline failed:")
                print(f"   Error: {result['error']}")
                if result.get('failed_block') is not None:
                    print(f"   Failed block: {result['failed_block']}")
                if result.get('partial_preview'):
                    pv = result['partial_preview']
                    print("   Partial preview:")
                    print(f"     Shape: {pv.get('shape')}")
                    print(f"     Columns: {pv.get('columns', [])[:10]}")
                return True

            print("✅ Pipeline success!")
            pv = result.get('preview', {})
            print(f"   Applied blocks: {result.get('applied_blocks', [])}")
            print(f"   Final shape: {pv.get('shape')}")
            print(f"   Columns: {pv.get('columns', [])[:10]}{'...' if pv.get('columns') and len(pv['columns'])>10 else ''}")
            if pv.get('head'):
                print("   Head (5 rows):")
                for row in pv['head']:
                    print(f"     - {row}")
            return True
        
        else:
            print(f"❌ Unknown command: {command}")
            print("   Type 'help' for available commands")
            return True
    
    def show_help(self):
        """Show help information."""
        print("\n🎭 AI Dataset Orchestrator Help")
        print("=" * 50)
        print("Commands:")
        print("  load <file_path>     - Load CSV, JSON, or Excel file")
        print("  provider <name>      - Switch AI provider:")
        print("                         • tandem - Tandem API")
        print("                         • claude - Anthropic Claude")
        print("                         • openai - OpenAI GPT-4")
        print("  transform <prompt>   - AI-orchestrated transformation")
        print("  script <prompts>     - Generate standalone script")
        print("  save [file_path]     - Save current dataset")
        print("  history              - Show transformation history")
        print("  status               - Show current status")
        print("  help                 - Show this help")
        print("  exit                 - Exit the orchestrator")
        print("\nTransformation Examples:")
        print("  'Remove outliers using IQR method'")
        print("  'Create polynomial features for regression'")
        print("  'Apply PCA for dimensionality reduction'")
        print("  'Generate time series lag features'")
        print("  'Balance dataset with SMOTE oversampling'")
        print("  'Encode categorical variables using target encoding'")
        print("  'Normalize numerical features using StandardScaler'")
        print("\nSupported Libraries:")
        print("  • pandas - Data manipulation")
        print("  • scikit-learn - ML preprocessing")
        print("  • pycaret - Low-code ML")
        print("  • darts - Time series")
        print("  • feature-engine - Feature engineering")
        print("  • imbalanced-learn - Dataset balancing")
        print("\nAPI Key Setup:")
        print("  export TANDEM_API_KEY=your_tandem_key")
        print("  export ANTHROPIC_API_KEY=your_claude_key") 
        print("  export OPENAI_API_KEY=your_openai_key")
    
    def show_status(self):
        """Show current orchestrator status."""
        print(f"\n🎭 Orchestrator Status:")
        
        # AI Provider status
        if self.orchestrator.ai_provider:
            provider_name = self.orchestrator.ai_provider.get_provider_name()
            is_configured = self.orchestrator.ai_provider.is_configured()
            status = "✅ Ready" if is_configured else "❌ Not configured"
            print(f"   AI Provider: {provider_name} ({status})")
        else:
            print("   AI Provider: ❌ None selected")
        
        # Dataset status
        if self.orchestrator.data is not None:
            shape = self.orchestrator.data.shape
            print(f"   Dataset: ✅ Loaded ({shape[0]:,} rows × {shape[1]} columns)")
        else:
            print("   Dataset: ❌ None loaded")
        
        # History
        history_count = len(self.orchestrator.transformation_history)
        print(f"   Transformations: {history_count} completed")
    
    def show_history(self):
        """Show transformation history."""
        history = self.orchestrator.get_transformation_history()
        
        if not history:
            print("📝 No transformation history yet")
            return
        
        print(f"\n📝 Transformation History ({len(history)} items)")
        print("=" * 60)
        
        for i, item in enumerate(history, 1):
            print(f"\n{i}. 🔍 Prompt: {item['prompt']}")
            print(f"   ⏰ Time: {item['timestamp']}")
            
            if 'transformation_info' in item['result']:
                info = item['result']['transformation_info']
                print(f"   🎭 Provider: {info.get('provider', 'N/A')}")
                print(f"   🔧 Type: {info.get('type', 'N/A')}")
                print(f"   📚 Libraries: {', '.join(info.get('libraries_used', []))}")
                print(f"   💡 Explanation: {info.get('explanation', 'N/A')}")
            
            if 'dataset_changes' in item['result'] and item['result']['dataset_changes']:
                changes = item['result']['dataset_changes']
                print(f"   📊 Changes: {changes.get('shape_change', 'N/A')}")
                if changes.get('new_columns'):
                    print(f"   ➕ New columns: {', '.join(changes['new_columns'])}")
            
            if 'execution_result' in item['result']:
                exec_result = item['result']['execution_result']
                if exec_result and 'status' in exec_result:
                    status = "✅" if exec_result['status'] == 'success' else "❌"
                    print(f"   {status} Status: {exec_result.get('message', 'N/A')}")
    
    def format_transformation_output(self, result: Dict[str, Any]) -> str:
        """Format transformation output for display."""
        if "error" in result:
            return f"❌ Error: {result['error']}"
        
        output = []
        
        # Display transformation results
        if "error" not in result:
            info = result.get("transformation_info", {})
            print(f"🎭 {info.get('provider', 'AI')} Orchestration:")
            print(f"   Type: {info.get('type', 'unknown')}")
            print(f"   💡 {info.get('explanation', 'N/A')}")
            if info.get('reasoning'):
                print(f"   🧠 Reasoning: {info.get('reasoning')}")
            print(f"   📚 Libraries: {', '.join(info.get('libraries_used', []))}")
            
            # Show error analysis and fixes if this was a retry
            if info.get('attempt', 1) > 1:
                print(f"   🔄 Attempt: {info.get('attempt')}")
                if info.get('error_analysis'):
                    print(f"   🔍 Error Analysis: {info.get('error_analysis')}")
                if info.get('fixes_applied'):
                    print(f"   🔧 Fixes Applied: {', '.join(info.get('fixes_applied'))}")
            
            if result.get("code_generated"):
                print(f"\n📜 Generated Code:")
                print("```python")
                print(result["code_generated"])
                print("```")
            
            exec_result = result.get("execution_result", {})
            if exec_result.get("status") == "success":
                print(f"\n✅ Execution: {exec_result.get('message', 'Success')}")
                
                changes = result.get("dataset_changes", {})
                if changes and "note" not in changes:
                    print(f"\n📊 Dataset Changes:")
                    print(f"   Shape: {changes.get('shape_change', 'N/A')}")
                    if changes.get("new_columns"):
                        print(f"   New columns: {', '.join(changes['new_columns'])}")
                    if changes.get("removed_columns"):
                        print(f"   Removed columns: {', '.join(changes['removed_columns'])}")
                elif changes and "note" in changes:
                    print(f"\n📜 {changes['note']}")
            else:
                print(f"\n❌ Execution failed: {exec_result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Error: {result['error']}")
        
        return True

    # --- Added helpers for contextual prompting and pipeline accumulation ---
    def _build_contextual_prompt(self, user_prompt: str) -> str:
        """Compose a prompt that includes a brief summary of previous steps for context."""
        history = self.orchestrator.get_transformation_history()
        if not history:
            return user_prompt
        # Include up to last 5 steps of context
        last = history[-5:]
        lines = ["Previous steps context:"]
        base_idx = len(history) - len(last) + 1
        for i, item in enumerate(last, base_idx):
            info = item.get("result", {}).get("transformation_info", {})
            desc = info.get("explanation") or info.get("type") or ""
            lines.append(f"- Step {i}: {desc}")
        lines.append("")
        lines.append(f"Current request: {user_prompt}")
        return "\n".join(lines)

    def _ensure_pipeline_header(self):
        """Create pipeline file with header if it does not exist."""
        if not os.path.exists(self.pipeline_path):
            with open(self.pipeline_path, "w", encoding="utf-8") as f:
                f.write("# Auto-generated cumulative transformation pipeline\n")
                f.write("# Each step is appended when you run 'transform' in the CLI.\n\n")
                f.write("import pandas as pd\n\n")
                f.write("steps = []\n\n")
                f.write("def apply_all(df: 'pd.DataFrame') -> 'pd.DataFrame':\n")
                f.write("    for s in steps:\n")
                f.write("        df = s(df)\n")
                f.write("    return df\n\n")

    def _append_to_pipeline(self, original_prompt: str, result: Dict[str, Any]):
        """Append a new step with generated code to the pipeline file."""
        self._ensure_pipeline_header()
        # Determine step number by counting existing step_ functions
        existing = 0
        try:
            with open(self.pipeline_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("def step_"):
                        existing += 1
        except FileNotFoundError:
            existing = 0
        step_num = existing + 1

        info = result.get("transformation_info", {})
        reasoning = (info.get("reasoning") or "").strip()
        code = (result.get("code_generated") or "").rstrip()
        ts = datetime.now().isoformat()

        # Strip leading code fences if any
        if code.startswith("```"):
            code = code.strip("`")
            lines = code.split("\n")
            if lines and lines[0].startswith("python"):
                lines = lines[1:]
            code = "\n".join(lines)

        # Remove import lines and any data loading lines; rely on incoming df
        pruned = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue
            if "pd.read_csv(" in stripped or stripped.startswith("df = pd.read_"):
                continue
            pruned.append(line)
        code_body = "\n".join(pruned).rstrip()
        if not code_body:
            code_body = "# No executable body returned by provider\n    return df"

        # Ensure the function returns df
        if "return df" not in code_body:
            if not code_body.endswith("\n"):
                code_body += "\n"
            code_body += "return df"

        with open(self.pipeline_path, "a", encoding="utf-8") as f:
            f.write(f"# Step {step_num} - {ts}\n")
            f.write(f"# Prompt: {original_prompt}\n")
            if reasoning:
                oneline = reasoning.replace("\n", " ")
                if len(oneline) > 500:
                    oneline = oneline[:500] + " ..."
                f.write(f"# Reasoning: {oneline}\n")
            f.write(f"def step_{step_num}(df: 'pd.DataFrame') -> 'pd.DataFrame':\n")
            for ln in code_body.splitlines():
                f.write("    " + ln + ("\n" if not ln.endswith("\n") else ""))
            if not code_body.endswith("\n"):
                f.write("\n")
            f.write(f"steps.append(step_{step_num})\n\n")

def main():
    """Main entry point for Orchestrator CLI."""
    cli = OrchestratorCLI()
    cli.start()


if __name__ == "__main__":
    main()
