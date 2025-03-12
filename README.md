# 🎬 Movie Recommendation System

This project builds a **movie recommendation system** using **OpenAI embeddings** and **ChromaDB**. It processes movie data, stores embeddings, and provides a **Streamlit-based UI** for querying movie recommendations.

---

## **🚀 Setup Guide**
### **1️⃣ Create and Activate a Virtual Environment**
Before running any scripts, it's recommended to create and activate a virtual environment:

```sh
# Create a virtual environment (only needed once)
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### **2️⃣ Install Dependencies**
Ensure you have all required Python packages installed:

```sh
pip install -r requirements.txt
```

---

## **🔄 Running the Data Processing Pipeline**
The data processing pipeline **downloads, extracts, and stores movie data**, then generates embeddings for efficient retrieval.

### **Step 1: Download Netflix Movie Dataset**
This script downloads raw movie data from HuggingFace and saves it in `data/`.

```sh
python scripts/data_processing/1a_download_netflix_data.py
```

### **Step 2: Extract Movie Descriptions**
This extracts **movie descriptions** and **metadata** into JSON format.

```sh
python scripts/data_processing/1b_extract_movie_descriptions.py
```

### **Step 3: Store Data & Generate Embeddings**
This script processes descriptions and **stores embeddings** in ChromaDB.

```sh
python scripts/data_processing/1c_store_movie_data.py
```

**(Optional)** If you need to re-run specific parts, you can execute individual scripts.

---

## **💡 Running the Streamlit App**
Once data is processed and embeddings are stored, run the Streamlit app for interactive recommendations.

### **Run the App**
```sh
streamlit run scripts/streamlit_app.py
```
This will start a local web server and open the **Movie Recommendation Assistant** in your browser.

---

## **📂 Project Structure**
```
ragui
├── chroma_db/                  # Stores ChromaDB embeddings
├── data/                        # Stores processed movie data
│   ├── netflix_movies.json      # Raw movie data
│   ├── movie_descriptions.json  # Extracted descriptions
│   ├── movie_metadata.json      # Metadata for filtering
├── docs/                        # Documentation files
├── scripts/
│   ├── data_processing/         # Prepares and processes data
│   │   ├── 1a_download_netflix_data.py
│   │   ├── 1b_extract_movie_descriptions.py
│   │   ├── 1c_store_movie_data.py
│   ├── rag/                     # Retrieval-Augmented Generation (RAG) logic
│   │   ├── rag_retrieval.py
│   ├── streamlit_app.py         # The main UI app
├── requirements.txt             # Python dependencies
├── venv/                        # Virtual environment (optional)
```

---

## **📌 Troubleshooting**
### **1️⃣ `OPENAI_API_KEY` Not Found**
Ensure you have an **`.env` file** with your OpenAI API key:
```sh
echo "OPENAI_API_KEY=your-api-key-here" > .env
```
Restart your terminal and run the scripts again.

### **2️⃣ Streamlit Not Found?**
Make sure it’s installed in your environment:
```sh
pip install streamlit
```

### **3️⃣ ChromaDB Not Found?**
Ensure ChromaDB is installed:
```sh
pip install chromadb
```

---

## **📜 License**
This project is licensed under the MIT License. 🚀
