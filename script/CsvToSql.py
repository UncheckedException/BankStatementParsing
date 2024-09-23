import os
import pandas as pd
import mysql.connector
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
    # Add mappings for other banks as needed
    'ICICI': {
        'date': 'Transaction Date',
        'narration': 'Description',
        'chq_ref_number': 'Reference Number',
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
    """Format date from 'dd/MM/yy' to 'YYYY-MM-DD'."""
    try:
        formatted_date = datetime.strptime(date_str.strip(), '%d/%m/%y').strftime('%Y-%m-%d')
    except ValueError:
        # Handle cases where date parsing fails, returning None or a default value
        formatted_date = None
    return formatted_date


def clean_data(value: str) -> str:
    """Trim whitespace and handle any specific cleaning."""
    if isinstance(value, str):
        return value.strip()
    return value


def process_file(file_path: str, bank_name: str, cursor):
    """Process a single file and insert data into the MySQL table."""
    # Retrieve the column mapping for the specified bank
    column_mapping = COLUMN_MAPPINGS.get(bank_name, COLUMN_MAPPINGS[DEFAULT_BANK_NAME])

    # Read the file and map the columns accordingly
    try:
        # Read the .txt or .csv file, skipping the first row as it contains headers
        df = pd.read_csv(file_path, delimiter=',', skiprows=1, names=DEFAULT_COLUMN_NAMES, skipinitialspace=True)

        # Clean and format data
        df = df.map(clean_data)

        # Convert date column to correct format
        df['Date'] = df['Date'].apply(format_date)

        # Convert numeric columns to float for database compatibility
        df['Credit Amount'] = pd.to_numeric(df['Credit Amount'], errors='coerce').fillna(0.0)
        df['Debit Amount'] = pd.to_numeric(df['Debit Amount'], errors='coerce').fillna(0.0)
        df['Closing Balance'] = pd.to_numeric(df['Closing Balance'], errors='coerce').fillna(0.0)

        # Filter and rename columns based on mapping
        mapped_columns = {db_column: df_column for db_column, df_column in column_mapping.items() if
                          df_column in df.columns}
        filtered_df = df[list(mapped_columns.values())].rename(columns={v: k for k, v in mapped_columns.items()})

        # Adding bank_name column with the bank name value
        filtered_df['bank_name'] = bank_name

        # Debugging: Print filtered DataFrame structure
        print(f"Filtered DataFrame for {file_path}:\n", filtered_df.head())

        # Convert DataFrame to list of tuples for batch insertion
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

        # Debugging: Print data to be inserted
        print(f"Data to be inserted for {file_path}:\n", data[:5])

        # Insert data into the database
        insert_data(cursor, data)
        print(f"Data from {file_path} inserted successfully for {bank_name}.")
    except Exception as e:
        print(f"Error processing file {file_path} for bank {bank_name}: {e}")


def process_files(directory: str, bank_name: str = DEFAULT_BANK_NAME, insert: bool = True):
    """Process all files in a directory for a specified bank."""
    # Establish a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Loop through all CSV and TXT files in the specified directory
        for filename in os.listdir(directory):
            if filename.endswith(".csv") or filename.endswith(".txt"):
                file_path = os.path.join(directory, filename)
                print(f"Processing file: {file_path}")

                # Process each file and optionally insert into the database
                process_file(file_path, bank_name, cursor)

                # Commit the transaction if insert is enabled
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
    # Directory containing the CSV and TXT files
    csv_directory = 'StamentAnalysis/data/hdfc'  # Replace with your directory path

    # Call the process_files function for HDFC bank with insert enabled
    process_files(csv_directory, bank_name='HDFC', insert=True)

    # You can call this function for other banks as well, for example:
    # process_files(csv_directory, bank_name='ICICI', insert=True)
