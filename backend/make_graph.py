import os
import sys
import argparse
import logging
from dotenv import load_dotenv
import pandas as pd
import altair as alt
import openai
import requests

# Locate messaging utilities in backend/unified-messaging-api/
sys.path.append(os.path.join(os.path.dirname(__file__), 'unified-messaging-api'))
from email_sender import EmailSender
from slack_sender import SlackSender
# Note: we will call the unified-messaging-api via HTTP (localhost:5002)
UMAPI_BASE = os.getenv('UMAPI_BASE', 'http://127.0.0.1:5002')

load_dotenv()
logging.basicConfig(level=logging.INFO)


def llm_generate_chart_code(df_preview: pd.DataFrame, user_prompt: str) -> str:
    """
    Ask OpenAI to produce Altair code with a `chart` variable based on the user prompt and schema.
    Code-only, no markdown, no backticks.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured in environment.")
    openai.api_key = api_key

    cols = df_preview.columns.tolist()
    head_json = df_preview.head(5).to_dict('records')

    # Prompt mirrors style/constraints from backend/app.py with financial twist
    prompt_template = (
        "You are an expert Python data visualization assistant working with a pandas DataFrame named df.\n"
        "Rules:\n"
        "- Return ONLY executable Python code. No markdown, no backticks, no explanations.\n"
        "- Use the Altair library only.\n"
        "- Use ONLY these columns: " + ", ".join(cols) + "\n"
        "- Assign the final chart to a variable named 'chart'.\n"
        "- Add a descriptive title and tooltips.\n"
        "- Favor financially meaningful insights (seasonality, cohort behavior, leakage, anomalies) if applicable.\n"
        f"User request: {user_prompt}\n"
        f"Data preview (first 5 rows): {head_json}\n"
        "Return code only."
    )

    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt_template}],
    )
    code = resp.choices[0].message.content.strip()
    # Strip accidental fences if any
    if code.startswith("```"):
        code = code.strip("`")
        lines = code.split("\n")
        if lines and lines[0].startswith("python"):
            lines = lines[1:]
        code = "\n".join(lines)
    return code


def llm_generate_reasoning(df_preview: pd.DataFrame, user_prompt: str) -> str:
    """Ask OpenAI for a one- or two-sentence rationale for the chosen visualization."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "(No reasoning available: OPENAI_API_KEY not configured)"
    openai.api_key = api_key
    cols = df_preview.columns.tolist()
    prompt = (
        "You are a data visualization expert. In 1-2 concise sentences, explain why the chosen Altair chart is a good fit "
        "for the user's request focusing on financial data analysis (e.g., seasonality, anomalies, leakage, cohort behavior). "
        f"Use only the available columns: {', '.join(cols)}. User request: {user_prompt}"
    )
    try:
        client = openai.OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return "(Reasoning generation failed)"


def render_chart_to_file(df: pd.DataFrame, code: str, out_path: str) -> str:
    """
    Execute Altair code to produce `chart` and save.
    Prefer PNG if the environment supports it; otherwise save HTML.
    """
    local_vars = {"df": df, "alt": alt, "pd": pd}
    logging.info("Executing generated code...\n%s", code)
    exec(code, {}, local_vars)
    chart = local_vars.get("chart")
    if chart is None:
        raise RuntimeError("No 'chart' object was produced by the generated code.")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Save as PNG (requires vl-convert-python or altair_saver configured)
    png_path = os.path.splitext(out_path)[0] + ".png"
    try:
        chart.save(png_path)
        logging.info("Saved chart PNG to %s", png_path)
        return png_path
    except Exception as e:
        raise RuntimeError(
            "PNG export failed. Please install and configure Altair PNG export. "
            "Try: pip install vl-convert-python (recommended) or altair_saver. "
            f"Original error: {e}"
        )


def send_via_email(attachment_path: str, recipient: str):
    """POST to unified-messaging-api /send-email with subject/body and attachment."""
    subject = "Financial Data Analysis Insight"
    body = (
        "Automated financial data analysis insights attached.\n\n"
        "This chart highlights key patterns based on your prompt."
    )
    payload = {
        'recipient_email': recipient,
        'subject': subject,
        'body': body,
        'images': [attachment_path]
    }
    resp = requests.post(f"{UMAPI_BASE}/send-email", json=payload, timeout=30)
    if not resp.ok or not (resp.json().get('success')):
        raise RuntimeError(f"Email API failed: {resp.status_code} {resp.text}")


def send_via_slack(attachment_path: str, channel: str = "#payroll-data-insights"):
    """POST to unified-messaging-api /send-slack with text and attachment."""
    text = (
        "Financial data analysis insight generated automatically.\n"
        "See the attached chart for details."
    )
    payload = {
        'channel': channel,
        'text': text,
        'images': [attachment_path]
    }
    resp = requests.post(f"{UMAPI_BASE}/send-slack", json=payload, timeout=30)
    if not resp.ok or not (resp.json().get('success')):
        raise RuntimeError(f"Slack API failed: {resp.status_code} {resp.text}")


def main():
    parser = argparse.ArgumentParser(description="Generate a financial insight chart and send it via email or Slack.")
    parser.add_argument("csv_path", help="Path to the final CSV dataset")
    parser.add_argument("prompt", help="Natural-language description of the insight to visualize")
    parser.add_argument("destination", choices=["email", "slack"], help="Where to send the chart")
    parser.add_argument("dest_value", help="Email address (if destination=email) or Slack channel (e.g., #payroll-data-insights)")
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv_path)
    if not os.path.exists(csv_path):
        raise SystemExit(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Generate code and reasoning with LLM using a small preview to keep prompts concise
    preview = df.head(200)
    code = llm_generate_chart_code(preview, args.prompt)
    reasoning = llm_generate_reasoning(preview, args.prompt)

    # Render output into backend/output/<base>_insight.(png|html)
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    base = os.path.splitext(os.path.basename(csv_path))[0]
    out_base = os.path.join(out_dir, f"{base}_insight")
    final_path = render_chart_to_file(df, code, out_base)

    # Print reasoning to console for user transparency
    print("--- Visualization Reasoning ---")
    print(reasoning)
    print("-------------------------------")

    if args.destination == "email":
        send_via_email(final_path, args.dest_value)
        print(f"✅ Email sent to {args.dest_value} with {final_path}")
    else:
        channel = args.dest_value or "#payroll-data-insights"
        if not channel.startswith("#") and channel != "payroll-data-insights":
            channel = f"#{channel}"
        send_via_slack(final_path, channel)
        print(f"✅ Slack message sent to {channel} with {final_path}")


if __name__ == "__main__":
    main()