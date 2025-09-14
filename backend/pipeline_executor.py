"""
Pipeline executor - Entry point for frontend to execute data processing pipelines.
"""

import os
import json
import csv
import warnings
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import deque
from data_agent.dataset_orchestrator import DatasetOrchestrator
import subprocess
import sys


class PipelineExecutor:
    """
    Frontend entry point for executing data processing pipelines.
    Handles topological ordering and execution of block-based workflows.
    """
    
    def __init__(self, provider_name: str = "openai"):
        self.orchestrator = DatasetOrchestrator(provider_name=provider_name)
        self.pipeline_sources = {}
        self.execution_history = []
    
    def execute_pipeline(self, blocks_json: Any) -> Dict[str, Any]:
        """
        Execute a pipeline of data processing blocks.
        
        Args:
            blocks_json: List of blocks or {"blocks": [...]} containing:
                - input_source: {"block_type":"input_source","block_id":1,"csv_source":"path"}
                - process: {"block_type":"process","block_id":2,"pre_req":[1],"prompt":"..."}
                - output: {"block_type":"output","block_id":3,"pre_req":[2],"output_source":"email|slack","output_data":"email@addr|#channel"}
                - destination: {"block_type":"destination","block_id":4,"pre_req":[3],"email_type":"email|slack","output_data":"..."}
        
        Returns:
            Dict with status, results, and preview of final dataset
        """
        try:
            # Parse and validate input
            blocks = self._parse_blocks(blocks_json)
            if isinstance(blocks, dict) and "error" in blocks:
                return blocks
            
            # Categorize blocks by type
            categorized = self._categorize_blocks(blocks)
            if isinstance(categorized, dict) and "error" in categorized:
                return categorized
            
            input_blocks, process_blocks, output_blocks, destination_blocks = categorized
            
            # Load all input sources
            load_result = self._load_input_sources(input_blocks)
            if isinstance(load_result, dict) and "error" in load_result:
                return load_result
            
            # For each destination block, find its dependency chain and execute
            results = []
            for dest_block in destination_blocks:
                result = self._execute_destination_pipeline(
                    dest_block, blocks, input_blocks, process_blocks, output_blocks
                )
                results.append(result)
                
                # If any destination fails, return the error
                if isinstance(result, dict) and "error" in result:
                    return result
            
            # Return combined results
            return {
                "status": "success",
                "destinations_processed": len(destination_blocks),
                "results": results,
                "execution_history": self.execution_history
            }
            
        except Exception as e:
            return {"error": f"Pipeline execution failed: {str(e)}"}
    
    def _parse_blocks(self, blocks_json: Any) -> Any:
        """Parse and validate blocks input format."""
        if isinstance(blocks_json, dict) and "blocks" in blocks_json:
            blocks = blocks_json["blocks"]
        elif isinstance(blocks_json, list):
            blocks = blocks_json
        else:
            return {"error": "Invalid blocks format. Provide a list of blocks or {'blocks': [...]}"}
        
        # Validate each block has required fields
        for block in blocks:
            if not isinstance(block, dict):
                return {"error": "Each block must be a dictionary"}
            if "block_id" not in block:
                return {"error": "Each block must have a 'block_id'"}
            if "block_type" not in block:
                return {"error": "Each block must have a 'block_type'"}
        
        return blocks
    
    def _categorize_blocks(self, blocks: List[Dict]) -> Any:
        """Categorize blocks by type and create lookup maps."""
        input_blocks = []
        process_blocks = []
        output_blocks = []
        destination_blocks = []
        
        # Create block lookup map
        self.block_map = {}
        
        for block in blocks:
            block_id = block["block_id"]
            block_type = block["block_type"]
            
            # Check for duplicate IDs
            if block_id in self.block_map:
                return {"error": f"Duplicate block_id found: {block_id}"}
            
            self.block_map[block_id] = block
            
            # Categorize by type
            if block_type == "input_source":
                input_blocks.append(block)
            elif block_type == "process":
                process_blocks.append(block)
            elif block_type == "output":
                output_blocks.append(block)
            elif block_type == "destination":
                destination_blocks.append(block)
            elif block_type == "visualization":
                # Visualization blocks are executed within the destination chain,
                # but we don't need a separate category list for them here.
                pass
            else:
                return {"error": f"Unknown block_type: {block_type}"}
        
        return input_blocks, process_blocks, output_blocks, destination_blocks
    
    def _load_input_sources(self, input_blocks: List[Dict]) -> Optional[Dict]:
        """Load all input source files into memory."""
        self.pipeline_sources = {}
        
        for src_block in input_blocks:
            block_id = src_block["block_id"]
            file_path = src_block.get("csv_source") or src_block.get("file_path")
            
            if not file_path:
                return {"error": f"input_source block {block_id} requires 'csv_source' field"}
            
            # Resolve file path
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            if not os.path.exists(file_path):
                return {"error": f"Input file not found: {file_path}"}
            
            # Load file with robust parsing
            try:
                if file_path.endswith('.csv'):
                    try:
                        df = pd.read_csv(file_path)
                    except Exception as e:
                        warnings.warn(f"Standard CSV parse failed ({e}). Using fallback parser.")
                        df = pd.read_csv(file_path, engine='python', on_bad_lines='skip')
                elif file_path.endswith('.json'):
                    df = pd.read_json(file_path)
                elif file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                else:
                    return {"error": f"Unsupported file format: {file_path}"}
                
                self.pipeline_sources[block_id] = df
                print(f"✅ Loaded source {block_id}: {df.shape[0]:,} rows × {df.shape[1]} columns")
                
            except Exception as e:
                return {"error": f"Failed to load {file_path}: {str(e)}"}
        
        return None  # Success
    
    def _execute_destination_pipeline(self, dest_block: Dict, all_blocks: List[Dict], 
                                    input_blocks: List[Dict], process_blocks: List[Dict], 
                                    output_blocks: List[Dict]) -> Dict[str, Any]:
        """Execute the pipeline for a specific destination block."""
        dest_id = dest_block["block_id"]
        
        # Find all dependencies for this destination
        dependency_chain = self._get_dependency_chain(dest_block, all_blocks)
        if isinstance(dependency_chain, dict) and "error" in dependency_chain:
            return dependency_chain
        
        # Get topological order of execution
        execution_order = self._topological_sort(dependency_chain)
        if isinstance(execution_order, dict) and "error" in execution_order:
            return execution_order
        
        print(f"🎯 Processing destination {dest_id}")
        print(f"📋 Execution order: {execution_order}")
        
        # Execute blocks in order
        current_data = None
        executed_steps = []
        viz_prompt: Optional[str] = None
        
        for block_id in execution_order:
            block = self.block_map[block_id]
            block_type = block["block_type"]
            
            if block_type == "input_source":
                # Set working dataset to this input source
                current_data = self.pipeline_sources[block_id].copy()
                self.orchestrator.data = current_data
                self.orchestrator.data_path = str(block_id)
                executed_steps.append(f"Loaded input source {block_id}")
                
            elif block_type == "process":
                # Execute AI transformation
                prompt = block.get("prompt", "").strip()
                if not prompt:
                    continue  # Skip empty prompts
                
                # Build contextual prompt with previous steps
                contextual_prompt = self._build_contextual_prompt(prompt, executed_steps)
                
                print(f"🤖 Processing block {block_id}: {prompt[:50]}...")
                result = self.orchestrator.orchestrate_transformation(contextual_prompt)
                
                if "error" in result or (result.get("execution_result") and result["execution_result"].get("error")):
                    return {
                        "error": result.get("error") or result.get("execution_result", {}).get("error"),
                        "failed_block": block_id,
                        "prompt": prompt,
                        "destination": dest_id
                    }
                
                # Update current data
                current_data = self.orchestrator.data.copy()
                executed_steps.append(f"Block {block_id}: {prompt}")
                
            elif block_type == "output":
                # Handle output destination
                output_source = block.get("output_source", "").strip()
                output_data = block.get("output_data", "").strip()
                
                if output_source and output_data:
                    # Process the output destination
                    if output_source == "email":
                        executed_steps.append(f"Prepared data for email delivery to {output_data}")
                    elif output_source == "slack":
                        executed_steps.append(f"Prepared data for Slack delivery to {output_data}")
                    else:
                        executed_steps.append(f"Prepared data for {output_source} delivery to {output_data}")
                else:
                    executed_steps.append(f"Output block {block_id} processed (no destination specified)")
                
                # Save final cleaned dataset with custom naming
                if current_data is not None:
                    try:
                        # Create output directory if it doesn't exist
                        output_dir = "data"
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Generate custom filename
                        final_filename = f"clean_{block_id}.csv"
                        final_path = os.path.join(output_dir, final_filename)
                        
                        # Save the cleaned dataset
                        current_data.to_csv(final_path, index=False)
                        
                        # Store the final file info for return
                        final_cleaned_file = {
                            "path": os.path.abspath(final_path),
                            "filename": final_filename,
                            "block_id": block_id
                        }
                        
                        executed_steps.append(f"Saved final dataset: {final_filename}")
                        
                    except Exception as e:
                        return {
                            "error": f"Failed to save final dataset for output block {block_id}: {str(e)}",
                            "failed_block": block_id,
                            "destination": dest_id
                        }
            elif block_type == "visualization":
                # Capture the visualization prompt to drive make_graph later
                viz_prompt_val = block.get("prompt", "").strip()
                if viz_prompt_val:
                    viz_prompt = viz_prompt_val
                    executed_steps.append(f"Visualization prompt captured from block {block_id}")
                else:
                    executed_steps.append(f"Visualization block {block_id} present with empty prompt")
        
        # Record execution history
        self.execution_history.append({
            "destination_id": dest_id,
            "email_type": dest_block.get("email_type"),
            "output_data": dest_block.get("output_data"),
            "email_dest": dest_block.get("email_dest"),  # Keep for backward compatibility
            "execution_order": execution_order,
            "executed_steps": executed_steps,
            "final_shape": current_data.shape if current_data is not None else None,
            "timestamp": datetime.now().isoformat()
        })
        
        # Optionally invoke make_graph.py to generate and send PNG via email or Slack
        viz_send_result: Dict[str, Any] = {}
        try:
            # Ensure the latest dataset is written to backend/output/1_latest.csv for make_graph.py
            try:
                if current_data is not None:
                    out_dir = os.path.join(os.path.dirname(__file__), "output")
                    os.makedirs(out_dir, exist_ok=True)
                    latest_path = os.path.join(out_dir, "1_latest.csv")
                    current_data.to_csv(latest_path, index=False)
                    executed_steps.append("Wrote latest dataset for visualization: output/1_latest.csv")
            except Exception as e:
                # If we cannot persist, still proceed but note the issue
                executed_steps.append(f"Warning: failed to write output/1_latest.csv: {e}")

            # Determine destination mode and value
            dest_mode = None
            dest_value = None
            if dest_block.get("email_dest"):
                dest_mode = "email"
                dest_value = dest_block.get("email_dest")
            elif dest_block.get("slack_channel") or dest_block.get("slack"):
                dest_mode = "slack"
                dest_value = dest_block.get("slack_channel") or dest_block.get("slack")
            
            if dest_mode and dest_value:
                # Fallback prompt if none captured
                if not viz_prompt:
                    viz_prompt = "Generate a meaningful financial insight chart highlighting trends and anomalies."
                
                make_graph_path = os.path.join(os.path.dirname(__file__), "make_graph.py")
                cmd = [
                    sys.executable if 'python' in sys.executable else 'python3',
                    make_graph_path,
                    viz_prompt,
                    dest_mode,
                    str(dest_value)
                ]
                # Run and capture output
                proc = subprocess.run(cmd, cwd=os.path.dirname(__file__), capture_output=True, text=True, timeout=180)
                viz_send_result = {
                    "command": " ".join(cmd),
                    "returncode": proc.returncode,
                    "stdout": proc.stdout[-1000:],
                    "stderr": proc.stderr[-1000:],
                    "status": "sent" if proc.returncode == 0 else "failed",
                    "image_path": os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "1_latest_insight.png"))
                }
            else:
                viz_send_result = {"status": "skipped", "reason": "No destination provided in destination block"}
        except Exception as e:
            viz_send_result = {"status": "failed", "error": str(e)}

        # Return result for this destination
        return {
            "destination_id": dest_id,
            "email_type": dest_block.get("email_type"),
            "output_data": dest_block.get("output_data"),
            "email_dest": dest_block.get("email_dest"),  # Keep for backward compatibility
            "status": "success",
            "execution_order": execution_order,
            "final_preview": self._get_data_preview(current_data) if current_data is not None else None,
            "final_cleaned_file": final_cleaned_file,
            "visualization_send": viz_send_result
        }
    
    def _get_dependency_chain(self, dest_block: Dict, all_blocks: List[Dict]) -> Any:
        """Get all blocks that this destination depends on (recursively)."""
        visited = set()
        dependency_chain = []
        
        def dfs(block_id):
            if block_id in visited:
                return
            
            if block_id not in self.block_map:
                return {"error": f"Block {block_id} referenced but not found"}
            
            visited.add(block_id)
            block = self.block_map[block_id]
            
            # Add dependencies first (DFS)
            prereqs = block.get("pre_req", []) or []
            for prereq_id in prereqs:
                result = dfs(prereq_id)
                if isinstance(result, dict) and "error" in result:
                    return result
            
            dependency_chain.append(block_id)
        
        # Start DFS from destination
        result = dfs(dest_block["block_id"])
        if isinstance(result, dict) and "error" in result:
            return result
        
        return dependency_chain
    
    def _topological_sort(self, block_ids: List[int]) -> Any:
        """Sort blocks in topological order based on dependencies."""
        # Build adjacency list and in-degree count
        in_degree = {bid: 0 for bid in block_ids}
        adj_list = {bid: [] for bid in block_ids}
        
        for block_id in block_ids:
            block = self.block_map[block_id]
            prereqs = block.get("pre_req", []) or []
            
            for prereq_id in prereqs:
                if prereq_id in block_ids:  # Only count dependencies within our chain
                    adj_list[prereq_id].append(block_id)
                    in_degree[block_id] += 1
        
        # Kahn's algorithm
        queue = deque([bid for bid in block_ids if in_degree[bid] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(result) != len(block_ids):
            return {"error": "Cyclic dependencies detected in pipeline"}
        
        return result
    
    def _build_contextual_prompt(self, prompt: str, executed_steps: List[str]) -> str:
        """Build a contextual prompt including previous execution steps."""
        if not executed_steps:
            return f"{prompt}\n(Available sources: {list(self.pipeline_sources.keys())})"
        
        context_lines = ["Previous pipeline steps:"]
        for i, step in enumerate(executed_steps, 1):
            context_lines.append(f"- Step {i}: {step}")
        
        context_lines.append(f"- Available sources: {list(self.pipeline_sources.keys())}")
        context_lines.append("")
        context_lines.append(f"Current request: {prompt}")
        
        return "\n".join(context_lines)
    
    def _get_data_preview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get a preview of the dataframe."""
        try:
            return {
                "shape": [int(df.shape[0]), int(df.shape[1])],
                "columns": df.columns.tolist(),
                "head": df.head(3).to_dict('records')
            }
        except Exception:
            return {"error": "Could not generate preview"}


# Convenience function for direct usage
def execute_pipeline(blocks_json: Any, provider_name: str = "openai") -> Dict[str, Any]:
    """
    Execute a data processing pipeline.
    
    Args:
        blocks_json: Pipeline blocks configuration
        provider_name: AI provider to use ("openai", "tandem", "claude")
    
    Returns:
        Execution results with status and data previews
    """
    executor = PipelineExecutor(provider_name=provider_name)
    return executor.execute_pipeline(blocks_json)


if __name__ == "__main__":
    # Example usage
    sample_pipeline = {
        "blocks": [
            {
                "block_type": "input_source",
                "block_id": 1,
                "csv_source": "data.csv"
            },
            {
                "block_type": "process", 
                "block_id": 2,
                "pre_req": [1],
                "prompt": "Clean the data by removing missing values"
            },
            {
                "block_type": "output",
                "block_id": 3,
                "pre_req": [2],
                "output_source": "email",
                "output_data": "user@example.com"
            },
            {
                "block_type": "visualize",
                "block_id": 4,
                "pre_req": [3],
                "prompt": ""
            },
            {
                "block_type": "output",
                "block_id": 5,
                "pre_req": [4],
                "output_source": "email",
                "output_data": "rianadutta13@gmail.com"
            }
        ]
    }
    
    result = execute_pipeline(sample_pipeline)
    print(json.dumps(result, indent=2))
