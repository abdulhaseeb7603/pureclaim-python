import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_parse import LlamaParse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Retrieve the LlamaParse API key from environment variables
api_key = os.getenv("LLAMA_CLOUD_API_KEY")
if not api_key:
    raise Exception("LLAMA_CLOUD_API_KEY environment variable not set.")

# Define the request model
class PDFRequest(BaseModel):
    pdf_url: str

# Define the PDF parsing function
def parse_pdf_to_markdown(pdf_url: str) -> list:
    """
    Downloads a PDF from the provided URL and parses it into clean Markdown.

    Args:
        pdf_url (str): URL of the PDF to be parsed.

    Returns:
        list: A list of Markdown strings, each representing a page from the PDF.
    """
    # Download the PDF from the provided URL
    response = requests.get(pdf_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download PDF. Status code: {response.status_code}")
    
    # Define the path to the temporary file in the /tmp directory
    temp_pdf_path = "/tmp/temp.pdf"
    with open(temp_pdf_path, "wb") as f:
        f.write(response.content)

    # Define content guideline instructions to guide markdown formatting.
    content_guideline_instruction = """
    You are a highly proficient document parser.
    Convert each page of the PDF into clean markdown suitable for large language model processing.
    Exclude any non-essential elements such as headers, footers, page numbers, and decorative images.
    Preserve the logical structure and hierarchy of the content, using appropriate Markdown syntax for headings, lists, and emphasis.
    Ensure that tables are accurately represented in Markdown format.
    """

    # Initialize LlamaParse with premium mode enabled.
    parser = LlamaParse(
        premium_mode=True,
        api_key=api_key,
        verbose=True,
        ignore_errors=False,
        invalidate_cache=True,
        do_not_cache=True,
        content_guideline_instruction=content_guideline_instruction,
        skip_diagonal_text=True,
        disable_ocr=True,
        do_not_unroll_columns=True,
        page_separator="",  # Remove page separators for continuous text
        result_type="markdown"
    )

    # Process the PDF file.
    json_result = parser.get_json_result(temp_pdf_path)
    markdown_pages = json_result[0]["pages"]

    # Remove the temporary file.
    os.remove(temp_pdf_path)
    return markdown_pages

# Define the new endpoint
@app.post("/parse-pdf-to-markdown/")
async def parse_pdf(request: PDFRequest):
    try:
        markdown_pages = parse_pdf_to_markdown(request.pdf_url)
        return {"message": "Parsing successful", "markdown_pages": markdown_pages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Existing endpoint for PDF to PNG conversion
class PDFToPNGRequest(BaseModel):
    pdf_url: str
    zoom: int = 2  # Default zoom level

@app.post("/convert-pdf-to-png/")
async def convert_pdf_to_png(request: PDFToPNGRequest):
    pdf_url = request.pdf_url
    zoom = request.zoom

    # Validate zoom level
    if zoom < 1 or zoom > 10:
        raise HTTPException(status_code=400, detail="Zoom level must be between 1 and 10.")

    # Download PDF if URL is provided
    response = requests.get(pdf_url)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to download the PDF. Please check the URL.")

    pdf_data = io.BytesIO(response.content)

    try:
        # Open the PDF document
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        mat = fitz.Matrix(zoom, zoom)
        base64_images = []

        # Loop through all pages
        for page_num, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert to base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            base64_string = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Create data URL
            data_url = f"data:image/png;base64,{base64_string}"
            base64_images.append({
                "page_number": page_num + 1,
                "data_url": data_url
            })

        return {
            "message": "Conversion successful",
            "images": base64_images
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
