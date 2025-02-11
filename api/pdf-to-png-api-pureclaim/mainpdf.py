import os
import io
import base64
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from colorama import Fore, Style
import fitz  # PyMuPDF
from PIL import Image

app = FastAPI()

class PDFRequest(BaseModel):
    pdf_url: str
    zoom: int = 2  # Default zoom level

@app.post("/convert-pdf-to-png/")
async def convert_pdf_to_png(request: PDFRequest):
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
