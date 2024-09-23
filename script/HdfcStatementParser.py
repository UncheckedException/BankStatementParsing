import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import re


# Function to format amounts in Indian Rupee format
def format_inr(amount):
    return "{:,.2f}".format(amount)


# Directory containing the text files
directory_path = '/home/codeplay/PycharmProjects/StamentAnalysis/data/hdfc'

# Initialize an empty DataFrame to hold all data
df_list = []

# Loop through all text files in the directory and read them into DataFrames
for filename in os.listdir(directory_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory_path, filename)
        temp_df = pd.read_csv(
            file_path,
            delimiter=',',
            skipinitialspace=True,
            names=[
                'Date', 'Narration', 'Value Date', 'Debit Amount',
                'Credit Amount', 'Chq/Ref Number', 'Closing Balance'
            ],
            header=0,
            dtype={
                'Date': str,
                'Narration': str,
                'Value Date': str,
                'Debit Amount': str,
                'Credit Amount': str,
                'Chq/Ref Number': str,
                'Closing Balance': str
            }
        )

        # Remove leading and trailing spaces from all fields in the DataFrame
        temp_df = temp_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        # Convert 'Date' column to datetime format, handle parsing errors
        temp_df['Date'] = pd.to_datetime(temp_df['Date'], format='%d/%m/%y', errors='coerce')

        # Convert 'Debit Amount' and 'Credit Amount' to numeric, handling errors
        temp_df['Debit Amount'] = pd.to_numeric(temp_df['Debit Amount'].str.replace(',', ''), errors='coerce').fillna(0)
        temp_df['Credit Amount'] = pd.to_numeric(temp_df['Credit Amount'].str.replace(',', ''), errors='coerce').fillna(0)

        # Remove redundant transactions: Keep only rows where either debit or credit is non-zero
        temp_df = temp_df[(temp_df['Debit Amount'] > 0) & (temp_df['Credit Amount'] == 0) |
                          (temp_df['Credit Amount'] > 0) & (temp_df['Debit Amount'] == 0)]

        # Append the temporary DataFrame to the list
        df_list.append(temp_df)

# Combine all DataFrames into a single DataFrame
df = pd.concat(df_list, ignore_index=True)

# Function to extract generalized narration patterns
def get_generalized_narration(narration):
    # Group narrations starting with 'UPI-'
    match = re.match(r'UPI-[^@]+', narration)
    if match:
        return match.group()

    # Group narrations starting with 'ACH D- INDIAN CLEARING CORP-' and remove the part after the last hyphen
    match = re.match(r'(ACH D- INDIAN CLEARING CORP)-[^-]+', narration)
    if match:
        return match.group(1)  # Return only the general part before the last hyphen

    # Add more patterns as needed here, for now return the original narration
    return narration


# Create a new column in the DataFrame for generalized narration patterns (for filtering only)
df['Generalized Narration'] = df['Narration'].apply(get_generalized_narration)

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Financial Data Analysis"

# Layout of the app
app.layout = html.Div([
    html.H1("Financial Data Analysis", style={'text-align': 'center', 'font-size': '30px', 'margin-bottom': '30px',
                                              'text-decoration': 'underline'}),

    # Date range picker
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=df['Date'].min(),
        end_date=df['Date'].max(),
        display_format='DD/MM/YYYY',
        style={'margin': '20px'}
    ),

    # Toggle button for narration filter
    html.Button(
        'Toggle Narration Filter',
        id='toggle-button',
        n_clicks=0,
        style={'margin': '10px'}
    ),

    # Narration filter dropdown (uses Generalized Narration for options)
    dcc.Dropdown(
        id='narration-dropdown',
        multi=True,  # Allow multiple selections
        placeholder="Select Narration(s)",
        style={'margin': '20px', 'max-height': '400px', 'width': '50%'},
        options=[],
    ),

    # Collapsible checklist for bulk selection
    html.Div(
        id='narration-checklist-container',
        style={'display': 'none', 'margin': '20px', 'width': '50%'},
        children=[
            # Search bar for checklist
            dcc.Input(
                id='checklist-search',
                type='text',
                placeholder='Search Narration...',
                style={'width': '100%', 'margin-bottom': '10px'}
            ),
            dcc.Checklist(
                id='narration-checklist',
                style={'overflowY': 'scroll', 'maxHeight': '300px'},
                options=[]
            )
        ]
    ),

    # Include/Exclude radio buttons
    dcc.RadioItems(
        id='filter-mode',
        options=[
            {'label': 'Include Selected Narrations', 'value': 'include'},
            {'label': 'Exclude Selected Narrations', 'value': 'exclude'}
        ],
        value='exclude',
        labelStyle={'display': 'inline-block', 'margin-right': '10px'},
        style={'text-align': 'center', 'margin-bottom': '20px'}
    ),

    # Display total credit, total debit, and total days in the selected range
    html.Div(id='total-info', style={'font-size': '18px', 'margin': '20px', 'text-align': 'center'}),

    # Display credit-debit difference
    html.Div(id='credit-debit-difference', style={'font-size': '20px', 'margin': '20px', 'text-align': 'center'}),

    # Graph for credits and debits over time
    dcc.Graph(id='credits-debits-graph'),
])


# Function to determine the color based on the debit amount
def get_debit_color(amount):
    if amount > 20000:
        return 'red'
    elif amount > 5000:
        return 'purple'
    elif amount > 1000:
        return 'yellow'
    else:
        return 'blue'  # Default color for debits <= 1000


# Callback to update narration filter options based on selected date range and search input
@app.callback(
    [Output('narration-dropdown', 'options'),
     Output('narration-checklist', 'options')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('checklist-search', 'value')]
)
def update_narration_options(start_date, end_date, search_value):
    # Convert the input start_date and end_date to datetime objects
    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        return [], []  # Return empty list if date conversion fails

    # Filter the data based on the selected date range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    # Get unique generalized narrations for the filtered date range
    unique_narrations = [{'label': narration, 'value': narration} for narration in
                         filtered_df['Generalized Narration'].unique()]

    # Filter options based on search input if provided
    if search_value:
        unique_narrations = [option for option in unique_narrations if search_value.lower() in option['label'].lower()]

    return unique_narrations, unique_narrations


# Combined callback to handle toggle actions
@app.callback(
    [Output('narration-dropdown', 'style'),
     Output('narration-checklist-container', 'style')],
    [Input('toggle-button', 'n_clicks')],
    [State('narration-dropdown', 'value')]
)
def toggle_narration_filter(n_clicks, dropdown_value):
    if n_clicks % 2 == 1:
        # Show checklist, hide dropdown
        return {'display': 'none'}, {'display': 'block'}
    else:
        # Show dropdown, hide checklist
        return {'display': 'block'}, {'display': 'none'}


# Callback to update graph and total info based on selected date range, narration filter, and filter mode
@app.callback(
    [Output('credits-debits-graph', 'figure'),
     Output('total-info', 'children'),
     Output('credit-debit-difference', 'children')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('narration-dropdown', 'value'),
     Input('narration-checklist', 'value'),
     Input('filter-mode', 'value')]
)
def update_graph_and_info(start_date, end_date, dropdown_value, checklist_value, filter_mode):
    # Determine the effective narration selection based on whether checklist or dropdown is visible
    selected_narrations = checklist_value if checklist_value else dropdown_value

    # Convert the input start_date and end_date to datetime objects
    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        return go.Figure(), f"Invalid date format. Error: {str(e)}", ""

    # Filter the data based on the selected date range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    # Apply the filter based on the selected mode (include/exclude)
    if selected_narrations:
        if filter_mode == 'exclude':
            # Exclude based on the generalized narration pattern
            filtered_df = filtered_df[~filtered_df['Generalized Narration'].isin(selected_narrations)]
        elif filter_mode == 'include':
            # Include based on the generalized narration pattern
            filtered_df = filtered_df[filtered_df['Generalized Narration'].isin(selected_narrations)]

    # Separate filtered debit and credit data
    filtered_debit_df = filtered_df[filtered_df['Debit Amount'] > 0]
    filtered_credit_df = filtered_df[filtered_df['Credit Amount'] > 0]

    # Calculate total debit, total credit, and total days in the selected range
    total_debit = filtered_debit_df['Debit Amount'].sum()
    total_credit = filtered_credit_df['Credit Amount'].sum()
    total_days = (end_date - start_date).days + 1  # Adding 1 to include both start and end date
    credit_debit_diff = total_credit - total_debit  # Calculate the difference between credit and debit

    # Format total debit and credit in Indian Rupee format
    total_info_text = (f"Total Credit: ₹{format_inr(total_credit)} | "
                       f"Total Debit: ₹{format_inr(total_debit)} | "
                       f"Total Days: {total_days}")

    # Determine color for credit-debit difference
    diff_color = 'green' if credit_debit_diff >= 0 else 'red'
    credit_debit_diff_text = html.Div(
        f"Credit - Debit Difference: ₹{format_inr(credit_debit_diff)}",
        style={'color': diff_color, 'font-weight': 'bold'}
    )

    # Create scatter plot for credits and debits
    fig = go.Figure()

    # Debit transactions with color coding based on amount
    fig.add_trace(go.Scatter(
        x=filtered_debit_df['Date'],
        y=filtered_debit_df['Debit Amount'],
        mode='markers',
        name='Debit Amount',
        marker=dict(
            color=[get_debit_color(amount) for amount in filtered_debit_df['Debit Amount']],
            size=10
        ),
        hoverinfo='text',
        hovertext=(
                'Date: ' + filtered_debit_df['Date'].dt.strftime('%d-%m-%Y') + '<br>' +
                'Amount: ₹' + filtered_debit_df['Debit Amount'].apply(format_inr) + '<br>' +
                'Narration: ' + filtered_debit_df['Narration'] + '<br>' +
                'Chq/Ref Number: ' + filtered_debit_df['Chq/Ref Number']
        )
    ))

    # Credit transactions (green dots)
    fig.add_trace(go.Scatter(
        x=filtered_credit_df['Date'],
        y=filtered_credit_df['Credit Amount'],
        mode='markers',
        name='Credit Amount',
        marker=dict(color='green', size=10),
        hoverinfo='text',
        hovertext=(
                'Date: ' + filtered_credit_df['Date'].dt.strftime('%d-%m-%Y') + '<br>' +
                'Amount: ₹' + filtered_credit_df['Credit Amount'].apply(format_inr) + '<br>' +
                'Narration: ' + filtered_credit_df['Narration'] + '<br>' +
                'Chq/Ref Number: ' + filtered_credit_df['Chq/Ref Number']
        )
    ))

    fig.update_layout(
        title=f'Credits and Debits Over Time ({start_date.strftime("%d-%m-%Y")} to {end_date.strftime("%d-%m-%Y")})',
        xaxis_title='Date',
        yaxis_title='Amount (₹)',
        xaxis=dict(tickformat='%d-%m-%Y'),
        template='plotly_white',
        margin=dict(l=40, r=20, t=50, b=50),
        hovermode='closest'
    )

    return fig, total_info_text, credit_debit_diff_text


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
