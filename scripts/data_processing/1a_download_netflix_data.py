import os
from datasets import load_dataset
import json
from tqdm import tqdm

# Define the root directory (one level up from this script)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# Ensure the data directory is in the project root
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

print("Downloading Netflix movie dataset from HuggingFace...")

# Load the dataset
dataset = load_dataset("hugginglearners/netflix-shows", split="train")

print(f"Downloaded {len(dataset)} movie entries.")

# Convert to a list of dictionaries for easier processing
movies = []
for i in tqdm(range(len(dataset)), desc="Processing"):
    movies.append({
        "title": dataset[i]["title"] or "",
        "type": dataset[i]["type"] or "",
        "release_year": dataset[i]["release_year"] or -1,
        "rating": dataset[i]["rating"] or "",
        "description": dataset[i]["description"] or ""
    })

# Save to JSON file in the root data folder
output_path = os.path.join(DATA_DIR, "netflix_movies.json")
with open(output_path, "w") as f:
    json.dump(movies, f, indent=4)

print(f"\nDownload complete. Data saved to '{output_path}'")
