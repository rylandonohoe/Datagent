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

# Step 2 - 2025-09-14T09:00:35.779459
# Prompt: 'drop outliers'
# Reasoning: Outliers can significantly skew the results of the data analysis. It is important to handle them because they can lead to misleading representations and affect the statistical analysis. The Interquartile Range (IQR) method is used here to identify and remove outliers. This method is chosen because it is less sensitive to extreme values compared to the Z-score method.
def step_2(df: 'pd.DataFrame') -> 'pd.DataFrame':
    # Fixed Python code that addresses the error
    
    # Identify numerical columns
    numerical_cols = ['IMDB_Rating', 'Meta_score', 'No_of_Votes']
    
    # Calculate IQR for each numerical column and remove outliers
    df_clean = df.copy()
    for col in numerical_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        df_clean = df_clean[~((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR)))]
    return df

steps.append(step_2)

# Step 3 - 2025-09-14T09:05:34.968338
# Prompt: 'remove action movies'
# Reasoning: The user wants to remove all action movies from the dataset. This can be achieved by filtering the 'Genre' column to exclude rows that contain the word 'Action'.
def step_3(df: 'pd.DataFrame') -> 'pd.DataFrame':
    # Fixed Python code that addresses the error
    # Exclude rows where 'Genre' contains 'Action'
    df = df[~df['Genre'].str.contains('Action')]
    return df

steps.append(step_3)

# Step 4 - 2025-09-14T09:13:55.031285
# Prompt: 'drop action movies'
# Reasoning: The task requires two steps: outlier removal and filtering based on a condition. For outlier removal, we can use the IQR method. For filtering, we can use the str.contains() method in pandas. Both of these tasks are common preprocessing steps in data analysis.
def step_4(df: 'pd.DataFrame') -> 'pd.DataFrame':
    # Fixed Python code that addresses the error
    
    # Calculate IQR for each numerical column and remove outliers
    cols = df.select_dtypes(include=[np.number]).columns
    for col in cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        df = df[~((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR)))]
    
    # Filter out rows where the 'Genre' column contains the word 'Action'
    df = df[~df['Genre'].str.contains('Action')]
    return df

steps.append(step_4)

# Step 5 - 2025-09-14T09:15:10.366796
# Prompt: 'keep only old movies'
# Reasoning: The corrected approach will first clean the 'Released_Year' column by removing non-numeric characters and then convert the column to integers. This will allow us to filter out movies that were released in the last 20 years. The approach will work because it handles the specific error that occurred and ensures that the 'Released_Year' column contains only valid data for the subsequent filtering operation.
def step_5(df: 'pd.DataFrame') -> 'pd.DataFrame':
    # Fixed Python code that addresses the error
    
    # Remove non-numeric characters from 'Released_Year'
    df['Released_Year'] = df['Released_Year'].str.extract('(\d+)', expand=False)
    
    # Drop rows with missing 'Released_Year'
    df = df.dropna(subset=['Released_Year'])
    
    # Convert 'Released_Year' to integer
    df['Released_Year'] = df['Released_Year'].astype(int)
    
    # Get the current year
    current_year = datetime.datetime.now().year
    
    # Filter out movies that were released in the last 20 years
    df = df[df['Released_Year'] <= current_year - 20]
    return df

steps.append(step_5)

