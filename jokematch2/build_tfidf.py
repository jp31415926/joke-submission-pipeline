#!/usr/bin/env python3
"""
Builds TF-IDF vectors for jokes in the database.
"""

from __future__ import annotations

import logging
import pickle
from typing import List, Tuple, Dict
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from db import fetch_jokes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main() -> None:
    """Main function to build TF-IDF vectors from jokes."""
    logger.info("Starting TF-IDF vectorizer build")

    # Fetch jokes from database
    try:
        jokes = fetch_jokes()
    except Exception as exc:
        logger.error(f"Failed to fetch jokes: {exc}")
        raise

    # Extract IDs, titles, and texts
    ids: List[int] = []
    titles: Dict[int, str] = {}
    texts: List[str] = []

    for joke in jokes:
        joke_id, title, text = joke
        ids.append(joke_id)
        titles[joke_id] = title
        texts.append(text)

    logger.info(f"Fetched {len(texts)} jokes")

    # Build TF-IDF vectorizer
    vectorizer = TfidfVectorizer(
        stop_words="english",
        lowercase=True,
        ngram_range=(1, 2),
        min_df=2,
        max_features=50000
    )

    # Fit vectorizer and get sparse matrix
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Save artifacts
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    joblib.dump(vectorizer, output_dir / "tfidf_vectorizer.pkl")
    sparse.save_npz(output_dir / "tfidf_matrix.npz", tfidf_matrix)
    with open(output_dir / "tfidf_ids.pkl", "wb") as f:
        pickle.dump(ids, f)
    with open(output_dir / "tfidf_titles.pkl", "wb") as f:
        pickle.dump(titles, f)

    logger.info(f"TF-IDF build finished: {len(texts)} jokes.")


if __name__ == "__main__":
    main()