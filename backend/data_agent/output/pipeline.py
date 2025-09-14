# Auto-generated cumulative transformation pipeline
# Each step is appended when you run 'transform' in the CLI.

import pandas as pd

steps = []

def apply_all(df: 'pd.DataFrame') -> 'pd.DataFrame':
    for s in steps:
        df = s(df)
    return df

# Step 1 - 2025-09-14T07:06:39.072222
# Prompt: drop action movies
# Reasoning: The filtering code correctly removes rows where the Genre contains 'Action'. Additionally, ensuring the directory exists before saving prevents errors.
def step_1(df: 'pd.DataFrame') -> 'pd.DataFrame':
    # Fixed Python code that addresses the error
    
    df = df[~df['Genre'].str.contains('Action', na=False)]
    
    directory = 'data'
    os.makedirs(directory, exist_ok=True)
    # If saving is needed:
    # df.to_csv(os.path.join(directory, 'filtered_movies.csv'), index=False)
    return df

steps.append(step_1)

