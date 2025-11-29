import pdfplumber
from app.core.config_loader import load_paths_config


def analyze_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        pages_to_read = min(2, num_pages)  # only first 2 pages

        print(f"Total pages: {num_pages}. Reading first {pages_to_read} page(s)...\n")

        for i in range(pages_to_read):
            page = pdf.pages[i]
            print(f"\n=== PAGE {i + 1} ===")

            tables = page.extract_tables()
            if not tables:
                print("No tables found on this page.")
                continue

            for t_index, table in enumerate(tables):
                print(f"\n--- TABLE {t_index + 1} ---")
                for row in table:
                    # Print each row line by line
                    print(row)


if __name__ == "__main__":
    paths = load_paths_config()
    pdf_path = ""

    analyze_pdf(pdf_path)
