"""
Semantic Search Engine using embeddings for intelligent paper/author discovery
Supports multi-modal retrieval beyond keyword matching
"""
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter
import re

# Import centralized configuration
from intelligent_config import (
    get_adaptive_threshold,
    USE_HARMONIC_MEAN,
    ALLOW_DOMINANT_TOPIC,
    DOMINANT_TOPIC_MIN_SCORE,
    DOMINANT_TOPIC_OTHER_MIN
)

# Optional: sentence-transformers for embeddings (install separately)
try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False
    print("[WARNING] sentence-transformers not installed. Semantic search will use fallback mode.")
    print("  Install with: pip install sentence-transformers")


class SemanticSearchEngine:
    """
    Intelligent search using semantic understanding, not just keywords
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.embeddings_file = data_dir / "paper_embeddings.npy"
        self.model = None
        self.paper_embeddings = None

        # Research area keywords for expertise modeling
        self.topic_keywords = {
            "reinforcement_learning": [
                "reinforcement learning", "rl", "policy gradient", "q-learning",
                "actor-critic", "ppo", "dqn", "reward", "markov decision",
                "temporal difference", "value function", "policy optimization",
                # NEW: Interdisciplinary RL terms
                "visuomotor", "visual rl", "vision-based rl", "model-based rl",
                "offline rl", "imitation learning", "inverse rl",
                "embodied rl", "world models", "model-free rl"
            ],
            "computer_vision": [
                "computer vision", "cv", "image", "visual", "object detection",
                "segmentation", "recognition", "convolutional", "cnn", "detection",
                "tracking", "pose estimation", "optical flow",
                # NEW: Modern CV terms
                "vision transformer", "vit", "visual encoder", "image encoder",
                "visual representation", "visual feature", "visual understanding",
                "self-supervised vision", "visual learning"
            ],
            "video_generation": [
                "video generation", "video synthesis", "temporal", "frame prediction",
                "video diffusion", "motion synthesis", "video editing", "generative video"
            ],
            "robotics": [
                "robot", "manipulation", "grasping", "navigation", "motion planning",
                "control", "sim-to-real", "embodied", "dexterous"
            ],
            "nlp": [
                "natural language", "nlp", "language model", "transformer", "bert",
                "gpt", "text", "translation", "question answering", "dialogue"
            ],
            "diffusion_models": [
                "diffusion", "ddpm", "ddim", "score-based", "denoising",
                "latent diffusion", "stable diffusion"
            ],
            "gans": [
                "gan", "generative adversarial", "generator", "discriminator",
                "adversarial training", "stylegan"
            ],
            "meta_learning": [
                "meta-learning", "few-shot", "maml", "meta", "transfer learning",
                "domain adaptation", "zero-shot"
            ],
            "graph_neural_networks": [
                "graph neural", "gnn", "graph convolutional", "gcn", "message passing",
                "graph attention", "node embedding"
            ],
            "self_supervised": [
                "self-supervised", "contrastive learning", "simclr", "moco",
                "pretext task", "unsupervised representation"
            ],
            # NEW: Interdisciplinary topics
            "embodied_ai": [
                "embodied", "embodied ai", "embodiment", "visuomotor",
                "sensorimotor", "manipulation", "sim-to-real", "embodied agent"
            ],
            "multimodal": [
                "multimodal", "multi-modal", "vision-language", "clip",
                "visual-linguistic", "image-text", "video-text", "vision and language"
            ]
        }

        # Load embeddings if available
        if HAS_EMBEDDINGS:
            self._load_model()
            self._load_embeddings()

    def _load_model(self):
        """Load sentence transformer model for embeddings"""
        if not HAS_EMBEDDINGS:
            return

        try:
            # Use scientific paper-specific model
            print("[SEMANTIC] Loading SPECTER2 model...")
            self.model = SentenceTransformer('allenai/specter2')
            print("[SEMANTIC] Model loaded successfully")
        except Exception as e:
            print(f"[SEMANTIC] Failed to load model: {e}")
            print("[SEMANTIC] Falling back to all-MiniLM-L6-v2...")
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                print("[SEMANTIC] Fallback model loaded")
            except Exception as e2:
                print(f"[SEMANTIC] Failed to load fallback model: {e2}")
                self.model = None

    def _load_embeddings(self):
        """Load pre-computed paper embeddings"""
        if self.embeddings_file.exists():
            try:
                self.paper_embeddings = np.load(self.embeddings_file)
                print(f"[SEMANTIC] Loaded {len(self.paper_embeddings)} paper embeddings")
            except Exception as e:
                print(f"[SEMANTIC] Failed to load embeddings: {e}")

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """Embed a text string into vector space"""
        if not self.model:
            return None

        try:
            return self.model.encode(text, convert_to_numpy=True)
        except Exception as e:
            print(f"[SEMANTIC] Embedding error: {e}")
            return None

    def semantic_similarity(self, query_emb: np.ndarray, paper_embeddings: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and papers"""
        # Normalize
        query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-8)
        papers_norm = paper_embeddings / (np.linalg.norm(paper_embeddings, axis=1, keepdims=True) + 1e-8)

        # Cosine similarity
        similarities = np.dot(papers_norm, query_norm)
        return similarities

    def extract_topics_from_text(self, text: str) -> Dict[str, float]:
        """
        Extract topic scores from text using keyword matching
        Fallback when embeddings aren't available
        """
        text_lower = text.lower()
        topic_scores = {}

        for topic, keywords in self.topic_keywords.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in text_lower)
            # Normalize by number of keywords
            score = matches / len(keywords)
            topic_scores[topic] = score

        return topic_scores

    def analyze_paper_content(self, paper: Dict) -> Dict:
        """
        Deep analysis of paper content to understand contribution
        """
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        combined = f"{title}. {abstract}"

        # Extract topics
        topics = self.extract_topics_from_text(combined)

        # Determine primary vs secondary topics
        sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)
        primary_topic = sorted_topics[0][0] if sorted_topics and sorted_topics[0][1] > 0 else None

        # Detect contribution type
        contribution_signals = {
            "novel_method": any(phrase in abstract for phrase in [
                "we propose", "we introduce", "we present", "novel", "new method"
            ]),
            "survey": any(phrase in abstract for phrase in [
                "survey", "review", "overview", "comprehensive study"
            ]),
            "benchmark": any(phrase in abstract for phrase in [
                "benchmark", "dataset", "evaluation", "comparison"
            ]),
            "application": any(phrase in abstract for phrase in [
                "we apply", "application of", "using existing"
            ])
        }

        return {
            "topics": topics,
            "primary_topic": primary_topic,
            "contribution_type": contribution_signals,
            "topic_depth": max(topics.values()) if topics else 0
        }

    def compute_author_expertise(self, papers: List[Dict]) -> Dict[str, float]:
        """
        Compute author's expertise distribution across topics
        Based on all their papers
        """
        if not papers:
            return {}

        # Aggregate topic scores across all papers
        topic_totals = Counter()
        topic_counts = Counter()

        for paper in papers:
            analysis = self.analyze_paper_content(paper)
            for topic, score in analysis["topics"].items():
                if score > 0:
                    topic_totals[topic] += score
                    topic_counts[topic] += 1

        # Compute average scores
        expertise = {}
        for topic in topic_totals:
            avg_score = topic_totals[topic] / topic_counts[topic]
            # Weight by number of papers in topic
            weighted_score = avg_score * min(topic_counts[topic] / 5.0, 1.0)
            expertise[topic] = round(weighted_score, 3)

        return expertise

    def analyze_interdisciplinary_fit(
        self,
        papers: List[Dict],
        required_topics: List[str],
        min_expertise: float = None,
        adaptive_threshold: bool = True
    ) -> Tuple[bool, Dict]:
        """
        Check if author has deep expertise in multiple required topics

        Args:
            papers: Author's papers
            required_topics: Topics to check expertise in
            min_expertise: Manual threshold (overrides adaptive if set)
            adaptive_threshold: Use adaptive thresholds based on topic count

        Returns:
            (is_match, details)
        """
        expertise = self.compute_author_expertise(papers)

        # Auto-select threshold based on topic count
        if min_expertise is None and adaptive_threshold:
            num_topics = len(required_topics)
            min_expertise = get_adaptive_threshold(num_topics)

        # Fallback to original default if still None
        if min_expertise is None:
            min_expertise = 0.3

        # Check each required topic
        topic_scores = {}
        for topic in required_topics:
            score = expertise.get(topic, 0.0)
            topic_scores[topic] = score

        # Strategy 1: Strict - ALL topics meet threshold
        strict_ok = all(score >= min_expertise for score in topic_scores.values())

        # Strategy 2: Dominant topic - One strong topic + others moderate (NEW)
        dominant_ok = False
        if ALLOW_DOMINANT_TOPIC and len(topic_scores) >= 2:
            scores_sorted = sorted(topic_scores.values(), reverse=True)
            # Strongest topic >= DOMINANT_TOPIC_MIN_SCORE (0.30)
            # Other topics >= DOMINANT_TOPIC_OTHER_MIN (0.15)
            dominant_ok = (
                scores_sorted[0] >= DOMINANT_TOPIC_MIN_SCORE and
                all(s >= DOMINANT_TOPIC_OTHER_MIN for s in scores_sorted[1:])
            )

        # Accept if either strategy passes
        all_meet_threshold = strict_ok or dominant_ok

        # Compute combined score
        if topic_scores:
            scores_array = np.array(list(topic_scores.values()))

            # Use harmonic mean (less punishing) or geometric mean
            if USE_HARMONIC_MEAN:
                # Harmonic mean: n / sum(1/x_i)
                # Add small epsilon to avoid division by zero
                combined_score = len(scores_array) / np.sum(1.0 / (scores_array + 1e-8))
            else:
                # Geometric mean (original): (x1 * x2 * ... * xn)^(1/n)
                combined_score = np.prod(scores_array) ** (1.0 / len(scores_array))

            # If we passed via dominant strategy, boost score slightly
            if dominant_ok and not strict_ok:
                combined_score *= 0.95  # Small penalty for imbalanced expertise
        else:
            combined_score = 0.0

        return all_meet_threshold, {
            "expertise": expertise,
            "required_topics": topic_scores,
            "combined_score": round(combined_score, 3),
            "meets_threshold": all_meet_threshold,
            "threshold_used": min_expertise,
            "strategy": "dominant" if (dominant_ok and not strict_ok) else "strict"
        }

    def analyze_research_trajectory(self, papers: List[Dict]) -> Dict:
        """
        Understand how author's research has evolved over time
        """
        # Group papers by year
        papers_by_year = {}
        for paper in papers:
            year = paper.get("year")
            if year:
                if year not in papers_by_year:
                    papers_by_year[year] = []
                papers_by_year[year].append(paper)

        # Compute topics per year
        trajectory = {}
        for year in sorted(papers_by_year.keys()):
            year_papers = papers_by_year[year]
            year_expertise = self.compute_author_expertise(year_papers)
            # Keep only significant topics
            significant = {t: s for t, s in year_expertise.items() if s >= 0.3}
            trajectory[year] = significant

        # Detect recent activity (last 2 years)
        recent_years = sorted(papers_by_year.keys())[-2:] if papers_by_year else []
        recent_topics = set()
        for year in recent_years:
            recent_topics.update(trajectory.get(year, {}).keys())

        return {
            "trajectory": trajectory,
            "recent_topics": list(recent_topics),
            "is_active": len(recent_years) >= 2
        }

    def compute_paper_depth_score(self, paper: Dict, topic: str) -> float:
        """
        Score how central a topic is to a paper (not just mentioned)
        """
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()

        keywords = self.topic_keywords.get(topic, [])
        if not keywords:
            return 0.0

        score = 0.0

        # Title mentions (high weight)
        title_mentions = sum(1 for kw in keywords if kw in title)
        score += title_mentions * 3.0

        # Abstract mentions (medium weight)
        abstract_mentions = sum(1 for kw in keywords if kw in abstract)
        score += abstract_mentions * 1.0

        # Novel contribution bonus
        if any(phrase in abstract for phrase in ["we propose", "we introduce", "novel"]):
            if any(kw in abstract for kw in keywords):
                score += 5.0

        # Normalize
        max_possible = len(keywords) * 4.0 + 5.0
        normalized = min(score / max_possible, 1.0)

        return normalized

    def rank_candidates_by_expertise(
        self,
        candidates: List[Dict],
        required_topics: List[str],
        papers_lookup: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """
        Rank candidates by their expertise in required topics

        Args:
            candidates: List of author dicts
            required_topics: Topics that matter
            papers_lookup: Dict mapping author_name -> papers

        Returns:
            Ranked list with scores and explanations
        """
        ranked = []

        for candidate in candidates:
            author_name = candidate.get("name")
            papers = papers_lookup.get(author_name, [])

            if not papers:
                continue

            # Analyze interdisciplinary fit with adaptive thresholds
            is_match, details = self.analyze_interdisciplinary_fit(
                papers, required_topics, adaptive_threshold=True
            )

            # Analyze trajectory
            trajectory = self.analyze_research_trajectory(papers)

            # Check if active in required topics
            recent_active = any(
                topic in trajectory["recent_topics"]
                for topic in required_topics
            )

            # Compute final score
            base_score = details["combined_score"] * 100
            if recent_active:
                base_score *= 1.2  # Bonus for recent work
            if not details["meets_threshold"]:
                base_score *= 0.5  # Penalty for not meeting threshold

            ranked.append({
                **candidate,
                "intelligence_score": round(base_score, 1),
                "expertise": details["expertise"],
                "required_topic_scores": details["required_topics"],
                "meets_threshold": details["meets_threshold"],
                "recent_topics": trajectory["recent_topics"],
                "is_active": trajectory["is_active"]
            })

        # Sort by intelligence score
        ranked.sort(key=lambda x: x["intelligence_score"], reverse=True)

        return ranked


# Global instance
semantic_engine = None

def initialize(data_dir: Path):
    """Initialize the semantic search engine"""
    global semantic_engine
    semantic_engine = SemanticSearchEngine(data_dir)
    return semantic_engine
