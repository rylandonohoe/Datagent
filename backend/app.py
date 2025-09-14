import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import altair as alt
import openai

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
        
        if not user_input:
            return jsonify({'error': 'No user input provided'}), 400
        
        # Prompt template for OpenAI
        prompt_template = (
            "You are an expert Python data visualization assistant. The user is working with the iris dataset from seaborn (https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv).\n"
            "The DataFrame 'df' has these columns: sepal_length, sepal_width, petal_length, petal_width, species.\n"
            "Your task:\n"
            "- YOUR NEXT RESPONSE MUST STRICTLY BE PYTHON CODE ONLY. NO EXPLANATIONS, NO MARKDOWN, NO COMMENTS OUTSIDE THE CODE.\n"
            "- Given the current Altair code and the user's modification request, generate a single, complete, and valid Altair code snippet that implements the user's intent.\n"
            "- The code must use only the columns listed above and must be executable as-is in a Python environment.\n"
            "- Do NOT include any markdown formatting or triple backticks—return only the code.\n"
            "- Always assign the chart to a variable named 'chart'.\n"
            "- Always add a chart title that reflects the user's request.\n"
            "- Always add tooltip encoding to show all columns when hovering over points.\n"
            "- Always add data axes and legends with appropriate titles.\n"
            "- If the user requests a chart type or transformation that is not possible with Altair or the iris dataset, return the closest valid alternative and explain the change in a Python comment at the top of the code.\n"
            f"Current Altair code:\n{chart_code}\nUser request:\n{user_input}\nReturn only the new Python code for the chart, using Altair and the same DataFrame variable 'df'."
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
        df = pd.read_csv(DATA_URL)
        
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

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=8080)
