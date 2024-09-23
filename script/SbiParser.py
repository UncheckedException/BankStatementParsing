import os
import pandas as pd
import mysql.connector
import pdfplumber
from typing import List
from datetime import datetime

# Database connection details for localhost MySQL
DB_HOST = 'localhost'
DB_PORT = 3306  # Default MySQL port
DB_NAME = 'finance_db'  # Replace with your database name
DB_USER = 'mysql'  # Replace with your username
DB_PASSWORD = 'mysql'  # Replace with your password

# Define the SQL table name
TABLE_NAME = 'bank_statement_replica'

# Column mapping configuration for different banks
COLUMN_MAPPINGS = {
    'HDFC': {
        'date': 'Date',
        'narration': 'Narration',
        'chq_ref_number': 'Chq/Ref Number',
        'credit_amount': 'Credit Amount',
        'debit_amount': 'Debit Amount',
        'closing_balance': 'Closing Balance'
    },
    'ICICI': {
        'date': 'Transaction Date',
        'narration': 'Description',
        'chq_ref_number': 'Reference Number',
        'credit_amount': 'Credit',
        'debit_amount': 'Debit',
        'closing_balance': 'Balance'
    },
    'SBI': {
        'date': 'Txn Date',
        'narration': 'Description',
        'chq_ref_number': 'Ref No./Cheque No.',
        'credit_amount': 'Credit',
        'debit_amount': 'Debit',
        'closing_balance': 'Balance'
    }
}

# Define default bank name
DEFAULT_BANK_NAME = 'HDFC'

# Define default column names if not present in the file
DEFAULT_COLUMN_NAMES = [
    'Date',
    'Narration',
    'Value Dat',  # Ignored in processing
    'Debit Amount',
    'Credit Amount',
    'Chq/Ref Number',
    'Closing Balance'
]


def get_db_connection():
    """Establish a database connection to MySQL."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def insert_data(cursor, data: List[tuple]):
    """Insert data into the MySQL table."""
    insert_query = f"""
        INSERT INTO {TABLE_NAME} 
        (date, narration, chq_ref_number, credit_amount, debit_amount, closing_balance, bank_name) 
        VALUES 
        (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.executemany(insert_query, data)


def format_date(date_str: str) -> str:
    """Format date from 'dd/MM/yy' or 'd M Y' to 'YYYY-MM-DD'."""
    try:
        # Try different formats until one works
        for fmt in ['%d/%m/%y', '%d %b %Y']:
            try:
                formatted_date = datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
                return formatted_date
            except ValueError:
                continue
        return None
    except ValueError:
        return None


def clean_data(value: str) -> str:
    """Trim whitespace and handle any specific cleaning."""
    if isinstance(value, str):
        return value.strip()
    return value


def process_pdf(file_path: str, column_names: List[str]) -> pd.DataFrame:
    """Process a PDF file in a bottom-up manner and return a DataFrame."""
    rows = []
    data_started = False
    with pdfplumber.open(file_path) as pdf:
        # Iterate from the last page to the first
        for page in reversed(pdf.pages):
            text = page.extract_text()
            lines = text.splitlines()[::-1]  # Reverse the lines on the page

            for line in lines:
                # Check for the required values in a line to start processing
                if all(col.lower() in line.lower() for col in column_names):
                    data_started = True
                    continue  # Skip the header line itself

                # Process lines only after headers are found
                if data_started:
                    parts = line.split()
                    # Ensure the line has the minimum expected number of elements
                    if len(parts) >= 7:
                        try:
                            # Adjust parsing logic according to the expected format
                            txn_date = format_date(parts[0])
                            narration = ' '.join(parts[1:-5])
                            ref_no = parts[-5]
                            debit = parts[-4]
                            credit = parts[-3]
                            balance = parts[-2]

                            # Make sure all fields have been parsed correctly
                            if txn_date and ref_no and balance:
                                row = {
                                    'Date': txn_date,
                                    'Narration': narration,
                                    'Chq/Ref Number': ref_no,
                                    'Debit Amount': debit,
                                    'Credit Amount': credit,
                                    'Closing Balance': balance
                                }
                                rows.append(row)
                        except (IndexError, ValueError) as e:
                            continue  # Skip lines that don't match the expected format

                # Stop processing if sufficient rows have been found
                if len(rows) > 10:  # Adjust the number as needed
                    break

            # Stop processing pages if sufficient rows have been found
            if len(rows) > 10:  # Adjust the number as needed
                break

    # Convert the list of rows into a DataFrame
    df = pd.DataFrame(rows)
    return df



def process_file(file_path: str, bank_name: str, cursor):
    """Process a single file (CSV or PDF) and insert data into the MySQL table."""
    column_mapping = COLUMN_MAPPINGS.get(bank_name, COLUMN_MAPPINGS[DEFAULT_BANK_NAME])
    file_extension = os.path.splitext(file_path)[1].lower()

    try:
        if file_extension == '.pdf':
            # Process PDF file, using only the keys from the column mapping as expected column names
            df = process_pdf(file_path, list(column_mapping.values()))
        elif file_extension == '.csv' or file_extension == '.txt':
            df = pd.read_csv(file_path, delimiter=',', skiprows=1, names=DEFAULT_COLUMN_NAMES, skipinitialspace=True)
            df = df.applymap(clean_data)
            df['Date'] = df['Date'].apply(format_date)
            df['Credit Amount'] = pd.to_numeric(df['Credit Amount'], errors='coerce').fillna(0.0)
            df['Debit Amount'] = pd.to_numeric(df['Debit Amount'], errors='coerce').fillna(0.0)
            df['Closing Balance'] = pd.to_numeric(df['Closing Balance'], errors='coerce').fillna(0.0)

        mapped_columns = {db_column: df_column for db_column, df_column in column_mapping.items() if
                          df_column in df.columns}
        filtered_df = df[list(mapped_columns.values())].rename(columns={v: k for k, v in mapped_columns.items()})
        filtered_df['bank_name'] = bank_name

        print(f"Filtered DataFrame for {file_path}:\n", filtered_df.head())

        data = [
            (
                row['date'],
                row['narration'],
                row['chq_ref_number'],
                row['credit_amount'],
                row['debit_amount'],
                row['closing_balance'],
                row['bank_name']
            )
            for _, row in filtered_df.iterrows()
        ]

        print(f"Data to be inserted for {file_path}:\n", data[:5])

        insert_data(cursor, data)
        print(f"Data from {file_path} inserted successfully for {bank_name}.")
    except Exception as e:
        print(f"Error processing file {file_path} for bank {bank_name}: {e}")


def process_files(bank_directories: dict, insert: bool = True):
    """Process all files for each bank in their respective directories."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        for bank_name, directory in bank_directories.items():
            print(f"Processing files for bank: {bank_name} in directory: {directory}")
            for filename in os.listdir(directory):
                if filename.endswith((".csv", ".txt", ".pdf")):
                    file_path = os.path.join(directory, filename)
                    print(f"Processing file: {file_path}")

                    process_file(file_path, bank_name, cursor)

                    if insert:
                        conn.commit()
                        print(f"Transaction committed for file {filename}.")
    except Exception as e:
        conn.rollback()
        print(f"Error occurred: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Dictionary containing bank names and their corresponding directories
    bank_directories = {
        #'HDFC': '/path_to_hdfc_directory',  # Replace with your HDFC directory path
        'SBI': 'PycharmProjects/StamentAnalysis/data/sbi',  # Replace with your SBI directory path
        # Add more banks and their directories as needed
    }

    process_files(bank_directories, insert=True)
