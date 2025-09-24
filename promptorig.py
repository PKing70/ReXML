import pandas as pd
from openai import OpenAI

# Load csv data
csv_file = 'Jira.csv'
csv_data = pd.read_csv(csv_file)
# Limit to first 100 rows
limited_csv = csv_data.head(10)
# Convert limited CSV to string
csv_text = limited_csv.to_string()

client = OpenAI()

prompt = (
f"Convert the following CSV data into MediaWiki table format:\n\n"
f"{csv_text}\n\n"
"Please format it as a MediaWiki table."
)

response = client.responses.create(
    model="gpt-4o",
    input=prompt,
)

print(response.output_text)
