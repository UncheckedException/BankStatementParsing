import tabula

# Replace 'file.pdf' with your PDF file path
tables = tabula.read_pdf('/home/codeplay/Downloads/Statement_Nov_23_XXXXXXXX0611.pdf', pages='all', multiple_tables=True)

# Iterate over extracted tables and print as DataFrame
for i, table in enumerate(tables):
    print(f"Paytm Table {i+1}")
    print(table)
    print(dir(table))
    table.to_excel(f"Paytm_table_{i+1}.xlsx", index=False)
    print("\n")

# import pandas as pd
#
# for i in range()
# df=pd.read_excel('table_1.xlsx')
# print(df.head())
# print(df.columns)
