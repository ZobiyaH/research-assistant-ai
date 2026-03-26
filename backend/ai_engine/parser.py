import os
from llama_parse import LlamaParse
from dotenv import load_dotenv

load_dotenv()

def parse_pdf_to_markdown(file_path):
    # Initialize the parser
    parser = LlamaParse(
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
        result_type="markdown",  # Optimized for RAG
        num_workers=4,
        verbose=True,
        language="en"
    )
    
    # Parse the file
    documents = parser.load_data(file_path)
    
    # Return the markdown content of the first (or all) documents
    return "\n\n".join([doc.text for doc in documents])

if __name__ == "__main__":
    # Use an absolute path or ensure the folder exists
    test_path = os.path.join(os.getcwd(), "data", "test.pdf")
    if os.path.exists(test_path):
        md_content = parse_pdf_to_markdown(test_path)
        print("--- Markdown Preview ---")
        print(md_content[:500])
    else:
        print(f"Error: Could not find test file at {test_path}")