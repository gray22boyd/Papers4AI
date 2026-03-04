"""
Generate embeddings for all papers in the database
This is a one-time operation that can take several hours

Usage:
    python scripts/generate_embeddings.py
"""
import sys
import json
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("ERROR: sentence-transformers not installed")
    print("Install with: pip install sentence-transformers")
    sys.exit(1)


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    papers_file = data_dir / "papers.json"
    output_file = data_dir / "paper_embeddings.npy"

    print("=" * 60)
    print("Paper Embedding Generation")
    print("=" * 60)

    # Load papers
    print(f"\n[1/4] Loading papers from {papers_file}...")
    with open(papers_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    print(f"  Loaded {len(papers):,} papers")

    # Load model
    print("\n[2/4] Loading SPECTER2 model...")
    print("  This may take a few minutes on first run...")
    try:
        model = SentenceTransformer('allenai/specter2')
        print("  Model loaded successfully")
    except Exception as e:
        print(f"  Failed to load SPECTER2: {e}")
        print("  Trying fallback model all-MiniLM-L6-v2...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("  Fallback model loaded")

    # Generate embeddings
    print("\n[3/4] Generating embeddings...")
    print("  This will take 1-4 hours depending on your hardware")
    print("  Progress will be saved every 10,000 papers")

    embeddings = []
    batch_size = 32  # Process 32 papers at a time

    # Process in batches
    for i in tqdm(range(0, len(papers), batch_size), desc="Embedding batches"):
        batch = papers[i:i+batch_size]

        # Combine title and abstract for better representation
        texts = []
        for paper in batch:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            text = f"{title}. {abstract}" if abstract else title
            texts.append(text)

        # Embed batch
        batch_embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        embeddings.extend(batch_embeddings)

        # Save checkpoint every 10k papers
        if (i + batch_size) % 10000 == 0:
            checkpoint_file = output_file.with_suffix('.checkpoint.npy')
            np.save(checkpoint_file, np.array(embeddings))
            print(f"\n  Checkpoint saved: {len(embeddings):,} papers embedded")

    # Convert to numpy array
    embeddings = np.array(embeddings)

    # Save final embeddings
    print(f"\n[4/4] Saving embeddings to {output_file}...")
    np.save(output_file, embeddings)

    # Print summary
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"  Papers embedded: {len(embeddings):,}")
    print(f"  Embedding dimension: {embeddings.shape[1]}")
    print(f"  File size: {file_size_mb:.1f} MB")
    print(f"  Saved to: {output_file}")
    print("\nYou can now use semantic search in the application!")
    print("=" * 60)


if __name__ == "__main__":
    main()
