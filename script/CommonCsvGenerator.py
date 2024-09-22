import PyPDF2
import pandas as pd
import os


# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    # Check if the file exists
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return None

    try:
        pdf_reader = PyPDF2.PdfReader(pdf_path)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() if page.extract_text() else ''
        return text
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None


# Function to convert extracted text to DataFrame
def text_to_dataframe(text):
    try:
        # Assuming the text is in a CSV-like format
        lines = text.split('\n')
        data = [line.split(',') for line in lines if line.strip() != '']

        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
        else:
            df = pd.DataFrame()
        return df
    except Exception as e:
        print(f"Error converting text to DataFrame: {e}")
        return pd.DataFrame()


# Paths to the files
pdf_path = '/home/codeplay/PycharmProjects/StamentAnalysis/data/Acct Statement_XX6976_15092024.pdf'
txt_path = '/home/codeplay/PycharmProjects/StamentAnalysis/data/115800923_1727028538599.txt'
output_csv_path = '/home/codeplay/PycharmProjects/StamentAnalysis/data/combined_data.csv'

# Extract text from PDF and convert to DataFrame
pdf_text = extract_text_from_pdf(pdf_path)
if pdf_text:
    pdf_df = text_to_dataframe(pdf_text)
else:
    pdf_df = pd.DataFrame()

# Read the current month's data from the TXT file
try:
    current_month_df = pd.read_csv(txt_path)
except Exception as e:
    print(f"Error reading TXT file: {e}")
    current_month_df = pd.DataFrame()

# Combine the data only if both dataframes have data
if not pdf_df.empty and not current_month_df.empty:
    combined_df = pd.concat([pdf_df, current_month_df], ignore_index=True)
elif not pdf_df.empty:
    combined_df = pdf_df
elif not current_month_df.empty:
    combined_df = current_month_df
else:
    print("No data to combine.")
    combined_df = pd.DataFrame()

# Save the combined data to a new CSV file
if not combined_df.empty:
    try:
        combined_df.to_csv(output_csv_path, index=False)
        print(f"Combined data saved to {output_csv_path}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")
else:
    print("No data available to save.")
