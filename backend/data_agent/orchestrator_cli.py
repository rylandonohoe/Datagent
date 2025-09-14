"""
Command-line interface for AI Dataset Orchestrator.
"""

import os
import sys
from typing import Dict, Any
from dataset_orchestrator import DatasetOrchestrator


class OrchestratorCLI:
    """Command-line interface for AI dataset orchestration."""
    
    def __init__(self):
        self.orchestrator = DatasetOrchestrator()
        self.running = True
    
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
            
            result = self.orchestrator.orchestrate_transformation(args)
            print(self.format_transformation_output(result))
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

def main():
    """Main entry point for Orchestrator CLI."""
    cli = OrchestratorCLI()
    cli.start()


if __name__ == "__main__":
    main()
