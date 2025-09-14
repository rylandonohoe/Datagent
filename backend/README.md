# Flask Backend for AI Visualization

This Flask backend handles OpenAI API requests to generate Altair visualizations for the iris dataset.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

3. Run the server:
```bash
python app.py
```

The server will run on `http://localhost:8080`

## API Endpoints

### POST /generate
Generates visualization code based on user input.

**Request body:**
```json
{
  "user_input": "Create a scatter plot of sepal_length vs sepal_width colored by species",
  "chart_code": ""
}
```

**Response:**
```json
{
  "chart_code": "chart = alt.Chart(df).mark_circle()...",
  "chart_html": "<html>...</html>",
  "error": null
}
```

### GET /health
Health check endpoint.

## Dataset
Uses the iris dataset from seaborn with columns:
- sepal_length
- sepal_width  
- petal_length
- petal_width
- species
