#!/usr/bin/env python3
"""
TF-IDF search script for joke duplicate detection.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

import joblib
#import numpy as np
from scipy.sparse import load_npz
from sklearn.metrics.pairwise import linear_kernel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_artifacts(artifacts_dir: Path) -> Tuple:
    """Load persisted TF-IDF artifacts."""
    try:
        vectorizer_path = artifacts_dir / "tfidf_vectorizer.pkl"
        matrix_path = artifacts_dir / "tfidf_matrix.npz"
        ids_path = artifacts_dir / "tfidf_ids.pkl"
        titles_path = artifacts_dir / "tfidf_titles.pkl"
        
        # Load vectorizer (saved with joblib)
        vectorizer = joblib.load(vectorizer_path)
        
        # Load sparse matrix properly
        tfidf_matrix = load_npz(matrix_path)
        
        # Load IDs (saved with pickle)
        import pickle
        with open(ids_path, "rb") as f:
            joke_ids = pickle.load(f)
        
        # Load titles (saved with pickle)
        with open(titles_path, "rb") as f:
            joke_titles = pickle.load(f)
            
        logger.info("Successfully loaded TF-IDF artifacts")
        return vectorizer, tfidf_matrix, joke_ids, joke_titles
        
    except Exception as e:
        logger.error(f"Error loading artifacts: {e}")
        raise

def search_joke(query_text: str, vectorizer, tfidf_matrix, joke_ids, joke_titles) -> List[Tuple[float, int, str]]:
    """Search for similar jokes using TF-IDF and cosine similarity."""
    try:
        # Transform query text to TF-IDF vector
        query_vector = vectorizer.transform([query_text])
        
        # Compute cosine similarities
        similarities = linear_kernel(query_vector, tfidf_matrix).flatten()
        
        # Get top 10 most similar jokes (descending order)
        top_indices = similarities.argsort()[::-1][:10]
        
         # Format results - make sure we handle types properly
        results = []
        for i in top_indices:
            #logger.info(f"i = {i}")
            score = float(similarities[i])
            #logger.info(f"score = {score}")
            joke_id = int(joke_ids[i])  # Properly convert to int
            #logger.info(f"joke_id = {joke_id}")
            # The index i is the position in the similarity array, but we need to use joke_id as dict key
            # This fixes the KeyError where numpy.int64 indices don't match dictionary keys
            try:
                # This is the correct approach: use joke_id as the dictionary key
                title = str(joke_titles[joke_id]) if joke_titles[joke_id] is not None else ""
            except KeyError:
                # Fallback in case joke_id is not found in titles (shouldn't happen with valid matching)
                logger.warning(f"joke_id {joke_id} not found in joke_titles, using empty title")
                title = ""
            results.append((score, joke_id, title))
            
        #logger.info(f"Found {len(results)} similar jokes")
        return results
        
    except Exception as e:
        logger.error(f"Error during search: {repr(e)}")
        raise

def main():
    """Main function to handle CLI arguments and execute search."""
    parser = argparse.ArgumentParser(description="Search for similar jokes using TF-IDF")
    parser.add_argument("joke_file", help="Path to a plain-text file containing a new joke")
    # Optional directory for the persisted TF-IDF artifacts
    parser.add_argument(
        "-a",
        "--artifacts-dir",
        default="data",
        help="Directory where the TF-IDF artifacts are stored (default: data)",
    )
    # Flag to output only the best match in a single line
    parser.add_argument(
        "-1",
        "--one-line",
        action="store_true",
        help="Print only the first (best) match in a single line",
    )
    
    args = parser.parse_args()
    
    try:
        # Load artifacts from the directory supplied by the user (default: data)
        artifacts_dir = Path(args.artifacts_dir)
        
        logger.info(f"Loading artifacts from {artifacts_dir}")
        vectorizer, tfidf_matrix, joke_ids, joke_titles = load_artifacts(artifacts_dir)
        
        # Read joke file
        joke_file_path = Path(args.joke_file)
        if not joke_file_path.exists():
            logger.error(f"Joke file not found: {joke_file_path}")
            sys.exit(1)
            
        with open(joke_file_path, "r", encoding="utf-8") as f:
            joke_text = f.read().strip()
            
        if not joke_text:
            logger.error("Input joke file is empty")
            sys.exit(1)
            
        logger.info(f"Searching for: {joke_text[:50]}...")
        
        # Perform search
        results = search_joke(joke_text, vectorizer, tfidf_matrix, joke_ids, joke_titles)
        
        # Print results table
        if args.one_line:
            # Only output the top match
            if results:
                score, joke_id, title = results[0]
                print(f"{int(score * 100.0)} {joke_id} {title}")
        else:
            # Full table
            print(f"{'Rank':<6} {'Score':<10} {'ID':^5}   Title")
            #for score, joke_id, title in results:
            for rank, (score, joke_id, title) in enumerate(results, start=1):
                #print(f"{score:.4f}   {joke_id}   {title}")
                print(f"{rank:>2}     {score:<10.4f} {joke_id:>5}   {title:<40}")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()