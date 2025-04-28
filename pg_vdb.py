#!/usr/bin/env python3
"""
PostgreSQL Vector‑DB sanity check
–––––––––––––––––––––––––––––––––
• Connects to Mark’s VDB
• Prints schema + record count
• Executes a hybrid‑search query and dumps the top‑3 hits
• Cleans up the SQLModel session on exit
"""

import sys
import json
from time import time
from sqlalchemy import text

# ── Local mapping for file‑path rewrites ─────────────────────────────────────
STORE_JSON_PATH = "/shared_folders/team_1/colton_bruni/store_clean_test.json"

def load_store_data():
    try:
        with open(STORE_JSON_PATH, "r") as f:
            return json.load(f)
    except Exception as exc:
        print("⚠️  Could not read JSON mapping:", exc)
        return {}

# ── Add VDB pipeline to path & import helpers ───────────────────────────────
sys.path.append("/shared_folders/team_1/mark_vdb/vdb_pipeline")

try:
    from init_vector_db import init_vector_db
    from search_vdb import search_vdb
    from vector import vector
    from variables import MODEL, NUM_OF_SEARCH_RESULTS

    print("✅ VDB modules loaded • model:", MODEL,
          "• default N:", NUM_OF_SEARCH_RESULTS)
except ImportError as e:
    sys.exit(f"Import error: {e}")

# ── 1) Connection introspection ─────────────────────────────────────────────

def test_connection():
    print("\n📊 Connecting to Postgres …")
    t0 = time()
    session, _ = init_vector_db(wipe_database=False)
    print(f"✅ Connected in {time() - t0:.2f}s")

    print("\n📋 Table schema (vector):")
    for name, col in vector.__table__.columns.items():
        print(f"   • {name}: {col.type}")

    total = session.exec(text(f"SELECT COUNT(*) FROM {vector.__tablename__}"))
    print(f"\n📈 Total records: {list(total)[0][0]:,}")

    return session

# ── 2) Run a query & pretty‑print results ───────────────────────────────────

def test_search(query: str, n: int = 3):
    print(f"\n🔍 Query  →  {query!r}")
    store = load_store_data()

    t0 = time()
    hits = search_vdb(query, num_results=n)
    print(f"✅ {len(hits)} results in {time() - t0:.2f}s")

    tuple_cols = [
        "id", "semantic_score", "bm25_score", "fused_score",
        "markdown", "filepath", "description"
    ]

    for idx, hit in enumerate(hits, 1):
        print("\n── Hit", idx)
        if isinstance(hit, tuple):
            for c, v in zip(tuple_cols, hit):
                print(f"{c}: {v}")
            filepath = hit[5]
        elif isinstance(hit, dict):
            for k, v in hit.items():
                print(f"{k}: {v}")
            filepath = hit.get("filepath", "")
        else:
            print("⚠️  Unrecognised hit format", type(hit))
            continue

        # mapping → local path
        local_path = filepath.replace(
            "/data/projects/filefindr/",
            "/shared_folders/team_1/document_batch/",
        ) if filepath.startswith("/data/projects/filefindr/") else filepath

        mapping = store.get(filepath.split("/")[-1], {})
        print("mapping:", mapping)
        print("📁 Local:", local_path)
        print("🔗 Link  : file://" + local_path)

# ── main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🛠  PostgreSQL Vector‑DB quick test")
    session = test_connection()
    try:
        test_search("chemical reactions in catalytic processes")
    finally:
        if session.is_active:
            session.close()
            print("🗙 Session closed")
