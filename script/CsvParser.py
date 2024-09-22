import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go


# Function to format amounts in Indian Rupee format
def format_inr(amount):
    return "{:,.2f}".format(amount)


# Load data from the text file
txt_path = '/home/4697685_1727029366018.txt'

# Read data
df = pd.read_csv(
    txt_path,
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
df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

# Convert 'Date' column to datetime format, handle parsing errors
df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%y', errors='coerce')

# Convert 'Debit Amount' and 'Credit Amount' to numeric, handling errors
df['Debit Amount'] = pd.to_numeric(df['Debit Amount'].str.replace(',', ''), errors='coerce').fillna(0)
df['Credit Amount'] = pd.to_numeric(df['Credit Amount'].str.replace(',', ''), errors='coerce').fillna(0)

# Remove redundant transactions: Keep only rows where either debit or credit is non-zero
df = df[(df['Debit Amount'] > 0) & (df['Credit Amount'] == 0) | (df['Credit Amount'] > 0) & (df['Debit Amount'] == 0)]

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Financial Data Analysis"

# Layout of the app
app.layout = html.Div([
    html.H1("Financial Data Analysis", style={'text-align': 'center', 'font-size': '30px', 'margin-bottom': '30px'}),

    # Date range picker
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=df['Date'].min(),
        end_date=df['Date'].max(),
        display_format='DD/MM/YYYY',
        style={'margin': '20px'}
    ),

    # Narration filter dropdown
    dcc.Dropdown(
        id='narration-filter',
        multi=True,  # Allow multiple narrations to be selected
        placeholder="Select Narration(s) to Exclude",
        style={'margin': '20px'}
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


# Callback to update narration filter options based on selected date range
@app.callback(
    Output('narration-filter', 'options'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_narration_options(start_date, end_date):
    # Convert the input start_date and end_date to datetime objects
    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        return []  # Return empty list if date conversion fails

    # Filter the data based on the selected date range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    # Get unique narrations for the filtered date range
    unique_narrations = [{'label': narration, 'value': narration} for narration in filtered_df['Narration'].unique()]
    return unique_narrations


# Callback to update graph and total info based on selected date range and narration filter
@app.callback(
    [Output('credits-debits-graph', 'figure'),
     Output('total-info', 'children'),
     Output('credit-debit-difference', 'children')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('narration-filter', 'value')]
)
def update_graph_and_info(start_date, end_date, excluded_narrations):
    # Convert the input start_date and end_date to datetime objects
    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        return go.Figure(), f"Invalid date format. Error: {str(e)}", ""

    # Filter the data based on the selected date range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    # Exclude selected narrations from the filtered data
    if excluded_narrations:
        filtered_df = filtered_df[~filtered_df['Narration'].isin(excluded_narrations)]

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
