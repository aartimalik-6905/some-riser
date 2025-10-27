# === 1. IMPORTS ===
# Standard libraries
import io
import os
import tempfile
import json 

# Third-party libraries
import spacy
import pandas as pd
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import docx
from img2table.ocr import TesseractOCR
from img2table.document import Image as Img2TableImage
from spacy.lang.en.stop_words import STOP_WORDS
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai # Our new AI brain

# --- 2. ALL BUG FIXES & SETUP ---

# FIX 1: Numba/img2table cache error [Errno 2]
numba_cache_dir = os.path.join(tempfile.gettempdir(), 'numba_cache')
if not os.path.exists(numba_cache_dir):
    os.makedirs(numba_cache_dir)
os.environ['NUMBA_CACHE_DIR'] = numba_cache_dir # <-- THIS LINE WAS MISSING

# FIX 2: Tesseract PATH error
# This line *ADDS* to your path, it doesn't overwrite it.
tesseract_path = r'C:\Program Files\Tesseract-OCR'
os.environ['PATH'] = tesseract_path + os.pathsep + os.environ.get('PATH', '')
pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_path, 'tesseract.exe')


# --- 3. CONFIGURE THE AI BRAIN ---
# FIX 3: Load API key securely from environment
try:
    # This reads the key you set in your terminal
    api_key = os.environ.get('API_KEY') 
    if not api_key:
        print("CRITICAL ERROR: 'API_KEY' environment variable not set.")
        print("Please set it before running the app:")
        print("Windows CMD: set API_KEY=YOUR_KEY_HERE")
        print("PowerShell:  $env:API_KEY = 'YOUR_KEY_HERE'")
        exit()
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Error configuring Google AI. {e}")
    
# --- 4. LOAD SPACY MODEL ---
try:
    nlp = spacy.load("en_core_web_sm", disable=["lemmatizer"])
except OSError:
    print("Error: 'en_core_web_sm' model not found. Run 'python -m spacy download en_core_web_sm'")
    exit()

# --- 5. CREATE FLASK APP ---
app = Flask(__name__)
# Allow all origins for simplicity
CORS(app, resources={r"/*": {"origins": "*"}}) 

# --- 6. SUMMARIZER FUNCTIONS (THE "BRAINS") ---

def summarize_document(text_content):
    """
    Analyzes document text using the Google AI (Gemini) API.
    This is the new "abstractive" summarizer.
    """
    
    if not text_content or not text_content.strip():
        return {
            "summary": "No text was provided to summarize.",
            "keywords": [],
            "entities": [],
            "image_count": 0
        }
        
    # FIX 4: Use a valid, existing model
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    Analyze the following text and provide two things in a clean JSON format:
    1. "summary": A concise, abstractive summary that explains the main topic, 
       its key points, and its conclusions.
    2. "keywords": A list of the 10 most important and relevant keywords and key phrases
       (e.g., "air pollution", "environmental justice").

    Do not include the ```json markdown. Only output the raw JSON.

    Here is the text:
    ---
    {text_content}
    ---
    """
    
    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().lstrip("```json").rstrip("```")
        ai_results = json.loads(json_text)
        
        return {
            "summary": ai_results.get("summary", "Summary could not be generated."),
            "keywords": ai_results.get("keywords", []),
            "entities": [],
            "image_count": 0
        }
        
    except Exception as e:
        print(f"Error calling Google AI: {e}")
        if 'response' in locals():
            print(f"Raw AI response that failed: {response.text}")
        return {
            "summary": "Error: The AI summary could not be generated. Check your API key and server log.",
            "keywords": [],
            "entities": [],
            "image_count": 0
        }

def summarize_table_from_text(csv_text):
    """
    Analyzes CSV text content and returns a dictionary (JSON).
    This function is stable.
    """
    try:
        csv_file = io.StringIO(csv_text)
        df = pd.read_csv(csv_file)

        columns = df.columns.tolist()
        num_rows = df.shape[0]
        num_cols = df.shape[1]

        column_types_list = []
        for col, dtype in df.dtypes.items():
            if 'int' in str(dtype) or 'float' in str(dtype):
                col_type = 'Number'
            else:
                col_type = 'Text'
            column_types_list.append(f"{col} ({col_type})")

        row_names = []
        row_header_name = ""
        if df.iloc[:, 0].dtype == 'object': 
            row_header_name = columns[0]
            row_names = df.iloc[:, 0].unique().tolist()[:5]

        sample_row = df.head(1).to_dict(orient='records')[0]

        insights = [
            f"This table has {num_rows} rows and {num_cols} columns.",
            f"Column types: {', '.join(column_types_list)}."
        ]
        if row_names:
            insights.append(f"The first column '{row_header_name}' seems to act as row headers.")
            insights.append(f"Example row names: {', '.join(row_names)}.")
        if 'Sales' in columns or 'Revenue' in columns or 'Q1' in columns:
            insights.append("This table appears to track financial or quarterly data.")

        return {
            "columns": columns,
            "num_rows": num_rows,
            "num_cols": num_cols,
            "sample_row": sample_row,
            "column_types": column_types_list,
            "row_names": row_names,
            "insights": insights
        }
    except Exception as e:
        return {"error": f"Could not parse table. Is it a valid CSV? ({e})"}

# --- 7. API "Routes" (The "Bridges") ---

@app.route('/summarize-doc', methods=['POST'])
def handle_doc_summary():
    """
    Bridge for pasted text or .txt files.
    """
    try:
        data = request.json
        if 'text' not in data or not data['text'].strip():
            return jsonify({"error": "No text provided"}), 400
        text = data['text']
        summary_data = summarize_document(text) # Calls the NEW Gemini function
        return jsonify(summary_data)
    except Exception as e:
        print(f"Error processing document: {e}")
        return jsonify({"error": "Could not analyze document."}), 500
        
@app.route('/summarize-table', methods=['POST'])
def handle_table_summary():
    """
    Bridge for .csv files.
    """
    data = request.json
    if 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    csv_text = data['text']
    summary_data = summarize_table_from_text(csv_text)
    return jsonify(summary_data)

@app.route('/summarize-image', methods=['POST'])
def handle_image_summary():
    """
    Bridge for .png/.jpg images. Uses img2table.
    """
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        img_bytes = file.read() # Read bytes ONCE

        # 1. Use img2table to find tables
        ocr = TesseractOCR(n_threads=1, lang="eng")
        doc = Img2TableImage(src=img_bytes) 
        extracted_tables = doc.extract_tables(ocr=ocr,
                                            implicit_rows=True,
                                            borderless_tables=True,
                                            min_confidence=50)

        table_summary = {"error": "No valid table was detected in this image."}
        doc_summary = {}

        if extracted_tables:
            first_table_df = extracted_tables[0].dataframe
            csv_text = first_table_df.to_csv(index=False)
            table_summary = summarize_table_from_text(csv_text)

        # 2. Get the Text Summary (pytesseract)
        img_for_pytesseract = Image.open(io.BytesIO(img_bytes))
        extracted_text = pytesseract.image_to_string(img_for_pytesseract)

        if not extracted_text.strip() and not extracted_tables:
            return jsonify({"error": "Could not read any text from the image."}), 400

        doc_summary = summarize_document(extracted_text) # Calls the NEW Gemini function

        if extracted_tables:
            doc_summary["summary"] = "Image was identified as a table. See table insights below."

        # 3. Return the COMBINED results
        return jsonify({
            "doc_summary": doc_summary, 
            "table_summary": table_summary
        })

    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({"error": f"Could not analyze image. {e}"}), 500
    
@app.route('/summarize-mixed-doc', methods=['POST'])
def handle_mixed_doc():
    """
    Bridge for .pdf and .docx files.
    """
    try:
        if 'doc' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['doc']
        all_text = ""
        all_tables = [] 
        image_count = 0 

        # 1. Read the File
        if file.filename.endswith('.pdf'):
            with fitz.open(stream=file.stream, filetype='pdf') as pdf_doc:
                for page in pdf_doc:
                    all_text += page.get_text() + "\n"
                    image_count += len(list(page.get_images(full=True)))
                    for table in page.find_tables():
                        all_tables.append(table.extract()) 

        elif file.filename.endswith('.docx'):
            doc = docx.Document(file.stream)
            for para in doc.paragraphs:
                all_text += para.text + "\n"
            for shape in doc.inline_shapes:
                if shape.type == 13: # FIX: 13 = WD_SHAPE_TYPE.PICTURE
                    image_count += 1
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                all_tables.append(table_data)
        else:
             return jsonify({"error": "Unsupported file type"}), 400

        # 2. Run BOTH Summarizers
        doc_summary_results = summarize_document(all_text) # Calls the NEW Gemini function
        doc_summary_results["image_count"] = image_count # Add image count

        table_summary_results = {"error": "No tables were found in this document."}
        if all_tables:
            first_table_list = all_tables[0] 
            if first_table_list and len(first_table_list) > 1:
                df = pd.DataFrame(first_table_list[1:], columns=first_table_list[0])
                csv_text = df.to_csv(index=False)
                table_summary_results = summarize_table_from_text(csv_text)
            else:
                table_summary_results = {"error": "Found a table, but it was empty."}

        # 3. Return the COMBINED results
        return jsonify({
            "doc_summary": doc_summary_results, 
            "table_summary": table_summary_results
        })

    except Exception as e:
        print(f"Error processing mixed document: {e}")
        return jsonify({"error": f"Could not analyze file. It may be corrupt or protected. {e}"}), 500
    
# --- 8. RUN THE SERVER ---
if __name__ == '__main__':
    print("Starting Flask server... Go to your index.html in the browser.")

    app.run(debug=True, port=5000)
