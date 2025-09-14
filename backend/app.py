import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import altair as alt
import openai
from data_agent.dataset_orchestrator import DatasetOrchestrator

logging.basicConfig(level=logging.INFO)
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Use the iris dataset
DATA_URL = 'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv'

@app.route('/generate', methods=['POST'])
def generate_visualization():
    try:
        data = request.get_json()
        user_input = data.get('user_input', '')
        chart_code = data.get('chart_code', '')
        graph_context = data.get('graph_context', {})
        
        if not user_input:
            return jsonify({'error': 'No user input provided'}), 400
        
        # Extract context information
        files = graph_context.get('files', [])
        prompts = graph_context.get('prompts', [])
        
        # Try to load and analyze the actual CSV data
        df_info = None
        sample_data = None
        
        if files:
            # Use the first CSV file found
            csv_path = files[0]
            try:
                # Load the CSV file
                df_sample = pd.read_csv(csv_path, nrows=5)  # Load first 5 rows for analysis
                # Clean column names for consistency
                df_sample.columns = df_sample.columns.str.replace('/', '_').str.replace(' ', '_').str.strip()
                df_info = {
                    'columns': list(df_sample.columns),
                    'dtypes': {col: str(dtype) for col, dtype in df_sample.dtypes.items()},
                    'sample_values': df_sample.to_dict('records')
                }
                sample_data = df_sample.head(3).to_string(index=False)
            except Exception as e:
                print(f"Error loading CSV {csv_path}: {e}")
                # Fallback to iris dataset
                df_info = {
                    'columns': ['sepal_length', 'sepal_width', 'petal_length', 'petal_width', 'species'],
                    'dtypes': {'sepal_length': 'float64', 'sepal_width': 'float64', 'petal_length': 'float64', 'petal_width': 'float64', 'species': 'object'},
                    'sample_values': []
                }
                sample_data = "sepal_length  sepal_width  petal_length  petal_width species\n5.1           3.5          1.4           0.2         setosa"
        else:
            # Default to iris dataset
            df_info = {
                'columns': ['sepal_length', 'sepal_width', 'petal_length', 'petal_width', 'species'],
                'dtypes': {'sepal_length': 'float64', 'sepal_width': 'float64', 'petal_length': 'float64', 'petal_width': 'float64', 'species': 'object'},
                'sample_values': []
            }
            sample_data = "sepal_length  sepal_width  petal_length  petal_width species\n5.1           3.5          1.4           0.2         setosa"
        
        # Build context string
        context_info = f"Dataset: {files[0] if files else 'iris dataset'}\n"
        context_info += f"Columns: {', '.join(df_info['columns'])}\n"
        if sample_data:
            context_info += f"Sample data:\n{sample_data}\n"
        if prompts:
            context_info += f"Previous prompts: {'; '.join(prompts)}\n"
        
        # Prompt template for OpenAI
        prompt_template = (
            "You are an expert Python data visualization assistant.\n"
            f"{context_info}\n"
            "Your task:\n"
            "- YOUR NEXT RESPONSE MUST STRICTLY BE PYTHON CODE ONLY. NO EXPLANATIONS, NO MARKDOWN, NO COMMENTS OUTSIDE THE CODE.\n"
            "- Generate a complete Altair visualization that uses the actual dataset columns shown above.\n"
            "- The code must be executable as-is in a Python environment.\n"
            "- Do NOT include any markdown formatting or triple backticks—return only the code.\n"
            "- Always assign the chart to a variable named 'chart'.\n"
            "- Always add a chart title that reflects the user's request.\n"
            "- Always add tooltip encoding to show relevant columns when hovering.\n"
            "- Always add appropriate axes labels and legends.\n"
            "- Use only the columns that exist in the dataset.\n"
            f"User request: {user_input}\n"
            "Return only the Python code for the chart using Altair and the DataFrame variable 'df'."
        )
        
        # Call OpenAI API
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt_template}
            ]
        )
        
        new_code = response.choices[0].message.content
        
        # Execute the code safely with error handling
        error_msg = None
        chart_html = ''
        
        # Load the actual dataset or fallback to iris
        if files:
            try:
                df = pd.read_csv(files[0])
                # Clean column names to match what AI expects
                df.columns = df.columns.str.replace('/', '_').str.replace(' ', '_').str.strip()
            except Exception as e:
                print(f"Error loading CSV {files[0]}: {e}")
                df = pd.read_csv(DATA_URL)  # Fallback to iris
        else:
            df = pd.read_csv(DATA_URL)  # Default to iris
        
        local_vars = {'df': df, 'alt': alt, 'pd': pd}
        cleaned_code = new_code.strip()
        
        # Clean markdown formatting if present
        if cleaned_code.startswith('```'):
            cleaned_code = cleaned_code.strip('`')
            lines = cleaned_code.split('\n')
            if lines[0].startswith('python'):
                lines = lines[1:]
            cleaned_code = '\n'.join(lines)
        
        try:
            logging.info("Executing generated code:\n%s", cleaned_code)
            exec(cleaned_code, {}, local_vars)
            chart = local_vars.get('chart')
            
            if chart:
                chart_html = chart.to_html()
            else:
                error_msg = 'No chart object was created. Please ensure your code assigns the chart to a variable named "chart".'
                
        except Exception as e:
            logging.error("Error executing generated code: %s", str(e))
            
            # If it's a syntax error, try to get a new code from the API
            if isinstance(e, SyntaxError):
                logging.info("Retrying with explicit request for valid Python code.")
                retry_prompt = f"The previous code was not valid Python. Please return only valid, executable Python code for the user's request: {user_input}. Do not include markdown or explanations. Use only the columns in the iris dataset. Assign the chart to a variable named 'chart'."
                
                retry_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "user", "content": retry_prompt}
                    ]
                )
                
                retry_code = retry_response.choices[0].message.content.strip()
                if retry_code.startswith('```'):
                    retry_code = retry_code.strip('`')
                    lines = retry_code.split('\n')
                    if lines[0].startswith('python'):
                        lines = lines[1:]
                    retry_code = '\n'.join(lines)
                
                try:
                    exec(retry_code, {}, local_vars)
                    chart = local_vars.get('chart')
                    if chart:
                        chart_html = chart.to_html()
                        error_msg = None
                        cleaned_code = retry_code
                    else:
                        error_msg = 'No chart object was created. Please ensure your code assigns the chart to a variable named "chart".'
                except Exception as e2:
                    logging.error("Retry also failed: %s", str(e2))
                    error_msg = f"Initial error: {str(e)}. Retry error: {str(e2)}"
            else:
                error_msg = str(e)
        
        logging.info("chart_html preview: %s", chart_html[:500] if chart_html else 'EMPTY')
        
        return jsonify({
            'chart_code': cleaned_code,
            'chart_html': chart_html,
            'error': error_msg
        })
        
    except Exception as e:
        logging.error("Unexpected error: %s", str(e))
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/data-agent/orchestrate', methods=['POST'])
def orchestrate_with_data_agent():
    """Run the DatasetOrchestrator on a dataset using AI provider.

    JSON body:
    {
      "dataset_path": "path/to/file.csv" | "https://...",  // required
      "prompt": "clean missing values and create moving averages", // required
      "provider": "tandem" | "openai" | "claude",           // optional, default tandem
      "script_only": true|false                                // optional, default false
    }
    """
    try:
        body = request.get_json(force=True)
        dataset_path = body.get('dataset_path')
        prompt = body.get('prompt')
        provider = (body.get('provider') or 'tandem').lower()
        script_only = bool(body.get('script_only', False))

        if not dataset_path or not prompt:
            return jsonify({
                'success': False,
                'error': 'dataset_path and prompt are required'
            }), 400

        # If a URL is provided, let pandas read it directly via orchestrator
        orch = DatasetOrchestrator(provider_name=provider, script_only_mode=script_only)

        # Attempt to load dataset
        loaded = False
        if dataset_path.startswith('http://') or dataset_path.startswith('https://'):
            try:
                df = pd.read_csv(dataset_path)
                # save to a temp csv for orchestrator
                tmp_path = os.path.join('/tmp', 'data_agent_input.csv')
                df.to_csv(tmp_path, index=False)
                loaded = orch.load_dataset(tmp_path)
            except Exception as e:
                return jsonify({'success': False, 'error': f'Failed to load dataset from URL: {e}'}), 400
        else:
            # Resolve relative path from backend directory
            path = dataset_path
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            if not os.path.exists(path):
                return jsonify({'success': False, 'error': f'Dataset not found: {path}'}), 400
            loaded = orch.load_dataset(path)

        if not loaded:
            return jsonify({'success': False, 'error': 'Failed to load dataset'}), 400

        # Orchestrate with retries handled internally
        result = orch.orchestrate_transformation(prompt)

        # Attach a tiny preview of resulting dataframe if available
        preview = None
        try:
            if orch.data is not None:
                preview = {
                    'shape': list(orch.data.shape),
                    'columns': orch.data.columns.tolist(),
                    'head': orch.data.head(5).to_dict('records')
                }
        except Exception:
            preview = None

        return jsonify({
            'success': 'error' not in result,
            'provider': provider,
            'script_only': script_only,
            'result': result,
            'preview': preview
        })

    except Exception as e:
        logging.exception('Data Agent orchestration failed')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/blocks/execute', methods=['POST'])
def execute_blocks():
    """Handle block execution requests with array of block objects.
    
    Expected JSON format (array of blocks):
    [
      {
        "block_type": "input_source",
        "block_id": 1,
        "csv_source": "path/to/file.csv"
      },
      {
        "block_type": "process", 
        "block_id": 2,
        "pre_req": [1],
        "prompt": "user prompt for transformation"
      },
      {
        "block_type": "output",
        "block_id": 3,
        "pre_req": [2],
        "init_script": "python code"
      },
      {
        "block_type": "destination",
        "block_id": 4,
        "pre_req": [3],
        "email_dest": "email@example.com"
      }
    ]
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Expect an array of blocks
        if not isinstance(data, list):
            return jsonify({'error': 'Expected an array of block objects'}), 400
        
        if len(data) == 0:
            return jsonify({'error': 'Empty blocks array provided'}), 400
        
        # Valid block types
        valid_block_types = ['input_source', 'process', 'output', 'destination']
        
        # Log the start of execution
        logging.info("=" * 60)
        logging.info("BLOCKS EXECUTION REQUEST")
        logging.info(f"Total blocks received: {len(data)}")
        logging.info("=" * 60)
        
        processed_blocks = []
        errors = []
        
        # Process each block
        for i, block in enumerate(data):
            try:
                # Validate required fields
                block_type = block.get('block_type')
                block_id = block.get('block_id')
                
                if not block_type or block_id is None:
                    error_msg = f'Block {i}: block_type and block_id are required'
                    errors.append(error_msg)
                    continue
                
                if block_type not in valid_block_types:
                    error_msg = f'Block {i}: Invalid block_type "{block_type}". Must be one of: {valid_block_types}'
                    errors.append(error_msg)
                    continue
                
                # Log block details
                logging.info(f"--- BLOCK {i+1} ---")
                logging.info(f"Block Type: {block_type}")
                logging.info(f"Block ID: {block_id}")
                logging.info(f"Prerequisites: {block.get('pre_req', [])}")
                
                # Validate and log block-specific fields
                block_valid = True
                
                if block_type == 'input_source':
                    csv_source = block.get('csv_source')
                    logging.info(f"CSV Source: {csv_source}")
                    if not csv_source:
                        errors.append(f'Block {block_id}: csv_source is required for input_source blocks')
                        block_valid = False
                        
                elif block_type == 'process':
                    prompt = block.get('prompt')
                    logging.info(f"Prompt: {prompt}")
                    if not prompt:
                        errors.append(f'Block {block_id}: prompt is required for process blocks')
                        block_valid = False
                        
                elif block_type == 'output':
                    init_script = block.get('init_script', '')
                    logging.info(f"Init Script: {init_script}")
                    
                elif block_type == 'destination':
                    email_dest = block.get('email_dest')
                    logging.info(f"Email Destination: {email_dest}")
                    if not email_dest:
                        errors.append(f'Block {block_id}: email_dest is required for destination blocks')
                        block_valid = False
                
                # Log complete block data
                logging.info(f"Complete Block Data: {block}")
                
                if block_valid:
                    processed_blocks.append({
                        'block_id': block_id,
                        'block_type': block_type,
                        'status': 'processed',
                        'pre_req': block.get('pre_req', [])
                    })
                    logging.info(f"Block {block_id} processed successfully")
                else:
                    logging.info(f"Block {block_id} failed validation")
                
                logging.info("-" * 30)
                
            except Exception as e:
                error_msg = f'Block {i}: Error processing block - {str(e)}'
                errors.append(error_msg)
                logging.error(error_msg)
        
        logging.info("=" * 60)
        logging.info("END BLOCKS EXECUTION REQUEST")
        logging.info("=" * 60)
        
        # Prepare response
        response = {
            'success': len(errors) == 0,
            'total_blocks': len(data),
            'processed_blocks': len(processed_blocks),
            'failed_blocks': len(errors),
            'blocks': processed_blocks,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        if errors:
            response['errors'] = errors
            return jsonify(response), 400
        else:
            response['message'] = f'Successfully processed {len(processed_blocks)} blocks'
            return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error processing blocks request: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=8080)
