# Artificial Retrieval Intelligence (RAGUI)

A modular Streamlit application for interacting with retrieval-augmented AI systems.
Includes a tabbed UI with a chat interface and document explorer.

---

## 📁 Project Structure

```
ragui/
├── public/                        # Static assets (e.g., images, icons)
├── scripts/
│   ├── ari_streamlit.py          # Main Streamlit app (Tabbed UI)
│   └── simple_file_server.py     # Local file server to expose files to the app
│
├── tab1/
│   └── chat.py                   # Chat tab content renderer
│
├── tab3/
│   └── document_explorer_tab.py # Document explorer tab content renderer
│
├── requirements.txt              # Project dependencies
└── README.md                     # You're here
```

---

## 🔧 Setup

1. **Create Conda environment**

```bash
conda create -n ragui_env python=3.11
conda activate ragui_env
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the App

### 1. Start the Local File Server (Optional)

If your app needs to serve local files via HTTP:

```bash
python scripts/simple_file_server.py
```

* This will start an HTTP server at an available port (default: `8069` or the next open one).
* The port number will be saved in: `~/file_server_port.txt`.

> 📂 The root `/` directory is exposed, so access with caution.

---

### 2. Run the Streamlit App

In a separate terminal:

```bash
streamlit run scripts/ari_streamlit.py
```

* Opens a tabbed UI with:

  * 💬 **Chat** interface (`tab1/chat.py`)
  * 📄 **Document Explorer** (`tab3/document_explorer_tab.py`)

---

## 🛠 Troubleshooting

* If you see an import error like `Failed to import from chat_page.py`, make sure:

  * You're running from the project root (`~/ragui`)
  * All necessary files (`chat.py`, `document_explorer_tab.py`) are present and correct
