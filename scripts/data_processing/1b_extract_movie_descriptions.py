import os
import json

# Get the absolute path to the project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# Define the data directory path
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Ensure the data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Load Netflix movie dataset
movies_path = os.path.join(DATA_DIR, "netflix_movies.json")
with open(movies_path, "r") as f:
    movies = json.load(f)

# Extract movie descriptions
descriptions = [movie["description"] for movie in movies if movie["description"]]

# Save extracted descriptions
descriptions_path = os.path.join(DATA_DIR, "movie_descriptions.json")
with open(descriptions_path, "w") as f:
    json.dump(descriptions, f, indent=4)

# Also save full movie data for metadata filtering later
metadata = []
for i, movie in enumerate(movies):
    if movie["description"]:  # Only include movies with descriptions
        movie_data = {
            "id": f"movie_{i}",
            "title": movie["title"],
            "type": movie["type"],
            "release_year": movie["release_year"],
            "rating": movie["rating"]
        }
        metadata.append(movie_data)

metadata_path = os.path.join(DATA_DIR, "movie_metadata.json")
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=4)

print(f"Extracted {len(descriptions)} movie descriptions and saved them to '{descriptions_path}'.")
print(f"Saved metadata for {len(metadata)} movies to '{metadata_path}'.")
