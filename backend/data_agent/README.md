# AI Dataset Orchestrator - Usage Guide

An intelligent data transformation system that uses AI to understand, analyze, and transform datasets through natural language commands.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r backend/data_agent/requirements.txt
```

### 2. Set up API Keys
Create a `.env` file in your project root:
```env
# Choose one or more providers
TANDEM_API_KEY=your_tandem_key_here
ANTHROPIC_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 3. Run the Orchestrator
```bash
python -m backend.data_agent.orchestrator_cli
```

## 🎭 CLI Commands

### Dataset Management
```bash
# Load a dataset
🎭 Orchestrator> load data/my_dataset.csv

# Check current status
🎭 Orchestrator> status

# Save current dataset
🎭 Orchestrator> save output/transformed_data.csv
```

### AI Provider Management
```bash
# Switch AI providers
🎭 Orchestrator> provider claude
🎭 Orchestrator> provider tandem
🎭 Orchestrator> provider openai

# Toggle script-only mode (no data modification)
🎭 Orchestrator> script-only on
🎭 Orchestrator> script-only off
```

### Data Transformations
```bash
# Natural language transformations
🎭 Orchestrator> transform "Remove outliers from numerical columns"
🎭 Orchestrator> transform "Fill missing values with mean for age, mode for city"
🎭 Orchestrator> transform "Create polynomial features for regression"
🎭 Orchestrator> transform "Convert daily stock data to monthly summaries"

# Generate transformation scripts
🎭 Orchestrator> script "clean data; normalize features; split train/test"
```

### History and Help
```bash
# View transformation history
🎭 Orchestrator> history

# Show all commands
🎭 Orchestrator> help

# Exit
🎭 Orchestrator> exit
```

## ✨ Key Features

### 🤖 Multi-AI Provider Support
- **Tandem (Qwen3-32B)**: Fast and efficient
- **Claude 4 Sonnet**: Advanced reasoning
- **OpenAI GPT-4**: Reliable and well-tested

### 🔄 Automatic Error Recovery
The system automatically retries failed transformations:
```
🎭 Tandem is orchestrating transformation...
❌ Code execution failed: syntax error
🔄 Attempt 2: AI is analyzing and fixing the error...
✅ Fixed! Transformation completed on attempt 2
```

### 📜 Script-Only Mode
Generate code without modifying your data:
```bash
🎭 Orchestrator> script-only on
🎭 Orchestrator> transform "clean missing values"
📜 Script generated successfully (no data modified)
```

### 📊 Comprehensive Logging
Track all transformations with detailed history:
- Prompts used
- AI provider and model
- Generated code
- Execution results
- Error analysis and fixes

## 🛠️ Supported Libraries

The orchestrator can generate code using:
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **scikit-learn**: Machine learning preprocessing
- **pycaret**: Low-code machine learning
- **darts**: Time series forecasting and analysis
- **feature-engine**: Feature engineering
- **imbalanced-learn**: Handling imbalanced datasets
- **category-encoders**: Categorical encoding

## 📝 Usage Examples

### Example 1: Basic Data Cleaning
```bash
🎭 Orchestrator> load data/customer_data.csv
📊 Dataset loaded successfully!
   Shape: (1000, 8)
   Columns: id, name, age, email, city, salary, department

🎭 Orchestrator> transform "clean missing values and remove duplicates"
🎭 Claude 4 Sonnet is orchestrating transformation...
✅ Execution: Transformation completed successfully
📊 Dataset Changes: Shape: (1000, 8) → (987, 8)
```

### Example 2: Feature Engineering
```bash
🎭 Orchestrator> provider tandem
🎭 Orchestrator> transform "create age groups and salary bins for analysis"
🎭 Tandem (Qwen3-32B) is orchestrating transformation...
✅ Execution: Transformation completed successfully
📊 Dataset Changes: Shape: (987, 8) → (987, 10)
   New columns: age_group, salary_bin
```

### Example 3: Script Generation
```bash
🎭 Orchestrator> script-only on
🎭 Orchestrator> transform "normalize numerical features and encode categories"
📜 Script generated successfully (no data modified)

📜 Generated Code:
```python
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder

# Normalize numerical features
scaler = StandardScaler()
numerical_cols = df.select_dtypes(include=['int64', 'float64']).columns
df[numerical_cols] = scaler.fit_transform(df[numerical_cols])

# Encode categorical features
le = LabelEncoder()
categorical_cols = df.select_dtypes(include=['object']).columns
for col in categorical_cols:
    df[col] = le.fit_transform(df[col].astype(str))
```

## 🔧 Configuration

### Timeout Settings
The system uses progressive timeouts for API calls:
- First attempt: 30 seconds
- Second attempt: 60 seconds
- Third attempt: 90 seconds

### Token Limits
- Claude: 4000 tokens (allows complete code generation)
- Tandem: Progressive retry with extended timeouts
- OpenAI: Standard API limits

### Retry Mechanism
- Maximum 3 attempts per transformation
- AI analyzes errors and generates fixes
- Detailed error reporting and recovery

## 🚨 Troubleshooting

### API Timeout Issues
```bash
# Switch to a different provider
🎭 Orchestrator> provider claude

# Or use script-only mode
🎭 Orchestrator> script-only on
```

### Missing API Keys
```bash
❌ AI provider not configured. Set appropriate API key.
```
Solution: Add the required API key to your `.env` file.

### Code Execution Errors
The system automatically retries with error analysis:
```
🔄 Attempt 2: AI is analyzing and fixing the error...
🔍 Error Analysis: Missing import statement for numpy
🔧 Fixes Applied: Added numpy import, Fixed variable naming
```

## 📁 Project Structure

### Essential Files
```
data_agent/
├── __init__.py                 # Package initialization
├── ai_providers.py            # AI provider implementations
├── dataset_orchestrator.py    # Core orchestration engine
└── orchestrator_cli.py        # CLI interface

requirements.txt               # Dependencies
run_orchestrator.py           # Main entry point
```

### Optional Files
- `data_visualization.ipynb`: Jupyter notebook for data exploration
- `demo_*.py`: Various demo scripts
- Provider-specific CLIs and explorers

## 🎯 Best Practices

1. **Start with script-only mode** to preview transformations
2. **Use specific prompts** for better results
3. **Switch providers** if one times out or fails
4. **Check transformation history** to track changes
5. **Save datasets** at key transformation points

## 📋 Requirements

- Python 3.8+
- Internet connection for AI API calls
- API keys for chosen providers
- See `requirements.txt` for complete dependency list

---

*Built for HackMIT 2024 - Intelligent data transformation through natural language*
