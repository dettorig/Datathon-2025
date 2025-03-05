import os
import re
import json
import pandas as pd
from huggingface_hub import InferenceClient

def extract_json_from_response(response_text):
    """
    Extracts the JSON substring by finding the first '{' and the last '}'.
    """
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}')
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        return response_text[start_idx:end_idx + 1]
    return None

def ensure_required_keys(data):
    """
    Checks that the output dictionary contains all required keys.
    If a key is missing, it adds a default value.
    """
    defaults = {
        "date": "NA",
        "publisher": "NA",
        "language": "NA",
        "author": "NA",
        "corrected_text": "NA",
        "sentiment": {"positive": 0.0, "negative": 0.0, "neutral": 0.0},
        "emotion_scores": {"fear": 0.0, "anger": 0.0, "hope": 0.0, "glory": 0.0, "patriotism": 0.0},
        "word_frequencies": {"victory": 0, "death": 0, "enemy": 0, "glory": 0},
        "topic_scores": {"military": 0.0, "economy": 0.0, "propaganda": 0.0},
        "propaganda_techniques": {"name_calling": 0.0, "loaded_language": 0.0, "doubt": 0.0, "appeal_to_fear": 0.0, "flag_waving": 0.0, 
                                  "exaggeration": 0.0},
        "readability_score": 0.0,
        "sentence_complexity": 0.0,
        "imperative_usage": 0.0,
        "historical_references": {"battle_mentions": 0, "leader_mentions": 0}
    }
    for key, default in defaults.items():
        if key not in data:
            data[key] = default
    return data

# Load API Key
HF_API_KEY = os.getenv("HF_API_KEY")
if not HF_API_KEY:
    raise ValueError("API key not found. Make sure you've set HF_API_KEY.")

# Path to the text file
file_path = "C:/Users/detto/WWI-Poster-Analysis-Datathon/data/Posters/texts/french/FL4984787_1_DIGI_0035_00001_VIEW_MAIN.jpg.txt"

# Read the text file
with open(file_path, "r", encoding="utf-8") as file:
    text_content = file.read()

# Refined prompt with clear instructions and all required keys
prompt = f'''
You are a historical text analyst. Your task is to analyze WW1 propaganda text by:
1. Correcting common OCR errors (e.g., misread characters, missing spaces, incorrect word formations).
2. Extracting metadata such as date, publisher, language, and author, along with numerical scores for various attributes.
Analyze the following text:

"{text_content}"

### Instructions:
- Correct OCR errors: fix misinterpreted characters (0↔O, 1↔l, I↔1, rn→m, vv→w).
- Correct misspellings based on the document language (French, German, Dutch).
- Restore broken words and remove unnecessary line breaks.
- Return ONLY a valid JSON object, starting with the first '{' and ending with the last '}', with NO additional text or commentary.
- The JSON must include ALL the following keys: 
  "date", "publisher", "language", "author", "corrected_text", 
  "sentiment", "emotion_scores", "word_frequencies", "topic_scores", 
  "propaganda_techniques", "readability_score", "sentence_complexity", 
  "imperative_usage", "historical_references".
- For the output file follow these instructions:
    - "date" should be in the following format dd-mm-yy. If day not available use format mm-yy
    - Scores in the following variables should be between 0 and 1:
    "sentiment", "emotion_scores", "word_frequencies", "topic_scores", 
    "propaganda_techniques", "readability_score", "sentence_complexity", 
    "imperative_usage", "historical_references".  
    - For propaganda_techniques use the following items' definitions:
        - name_calling: “Labeling the object of the propaganda campaign as either something the target audience
        fears, hates, finds undesirable or otherwise loves or praises”
        - loaded_language: “Using words or phrases with strong emotional implications to influence an audience”
        - doubt: “Questioning the credibility of someone or something”
        - appeal_to_fear: “Seeking to build support for an idea by instilling anxiety and/or panic in the population
        towards an alternative, possibly based on preconceived judgments”
        - flag_waving: “Playing on strong national feeling (or with respect to a group, e.g., race, gender, political
        preference) to justify or promote an action or idea”
        - exaggeration:  “Either representing something in an excessive manner: making things larger, better, worse
        (e.g., “the best of the best”, “quality guaranteed”) or making something seem less important
        or smaller than it actually is ”
    - If any metadata is not available, assign it the value "NA" (or an appropriate numerical default).

Return the JSON object now.
'''

# Create the inference client
client = InferenceClient(provider="together", api_key=HF_API_KEY)

messages = [
    {
        "role": "user",
        "content": prompt
    }
]

# Make the API call
completion = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-R1",
    messages=messages,
    max_tokens=3000,
)

# Print full response (for debugging/logging)
response_text = completion.choices[0].message['content']
print("Full response from model:\n", response_text)

# Extract JSON from the model's response
json_text = extract_json_from_response(response_text)
if json_text is None:
    print("Error: No valid JSON found in response.")
    response_data = {}
else:
    try:
        response_data = json.loads(json_text)
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON response.")
        response_data = {}

# Ensure all required keys exist, setting defaults if missing
response_data = ensure_required_keys(response_data)

# Convert the response dictionary to a DataFrame
df = pd.json_normalize(response_data)

# Define the Excel file path
excel_path = "C:/Users/detto/WWI-Poster-Analysis-Datathon/data/analysis_results.xlsx"

# Append to an existing Excel file if it exists; otherwise, create a new one
try:
    if os.path.exists(excel_path):
        existing_df = pd.read_excel(excel_path)
        df = pd.concat([existing_df, df], ignore_index=True)
except Exception as e:
    print("Error reading existing Excel file:", e)

# Save the DataFrame to Excel
df.to_excel(excel_path, index=False)
print("Analysis results saved to", excel_path)
