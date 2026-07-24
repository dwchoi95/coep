"""Structural featurization and clustering of programs.

Two things live here, both built on the same *structural view* of a program:

* ``structural_features`` — a TF-IDF vector over normalized-AST path n-grams.
  Identifiers and literals are folded to their node type (as in the RPS labeler),
  so two programs are close when they have the same *shape*, regardless of names.

* ``cluster`` — group a set of programs by that view and return, per cluster, a
  medoid (the most central real program).

This is the substrate for (a) Stage-1 build-set / reference selection and
(b) the fallback's strategy-matched reference pick. Correct programs are
behaviorally identical, so structure is the only thing that distinguishes their
solution strategies, which is why reference selection uses this view alone.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import pairwise_distances


# --------------------------------------------------------------- featurization
def _node_label(node: ast.AST) -> str:
    """Node type, with names/literals folded away (shape, not identity)."""
    return type(node).__name__


def _paths(node: ast.AST, prefix: tuple[str, ...], out: list[str], depth: int) -> None:
    """Root-to-node label paths of length <= 3, as underscore-joined tokens."""
    label = _node_label(node)
    path = (prefix + (label,))[-3:]
    out.append("_".join(path))
    for child in ast.iter_child_nodes(node):
        _paths(child, path, out, depth + 1)


def ast_paths(source: str) -> str:
    """Space-joined AST path n-grams for one program; '' if it does not parse."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    out: list[str] = []
    _paths(tree, (), out, 0)
    return " ".join(out)


def structural_features(sources: list[str]):
    """TF-IDF matrix over AST path n-grams. Returns (matrix, vectorizer)."""
    docs = [ast_paths(s) for s in sources]
    vec = TfidfVectorizer(token_pattern=r"[^\s]+", min_df=1)
    # guard: all-empty corpus (all unparseable) would raise
    if not any(docs):
        return np.zeros((len(sources), 1)), None
    matrix = vec.fit_transform(docs)
    return matrix, vec


# --------------------------------------------------------------- clustering
@dataclass
class Cluster:
    label: int
    members: list[int]          # indices into the input list
    medoid: int                 # index of the most central member


def _medoid(indices: list[int], dist: np.ndarray) -> int:
    """Member minimizing summed distance to the rest of its cluster."""
    if len(indices) == 1:
        return indices[0]
    sub = dist[np.ix_(indices, indices)]
    return indices[int(sub.sum(axis=1).argmin())]


def cluster(sources: list[str], min_cluster_size: int = 2,
            max_clusters: int | None = None) -> tuple[list[Cluster], np.ndarray]:
    """Cluster programs by structure; return clusters (with medoids) and the
    pairwise cosine-distance matrix used, so callers can reuse it.

    Cluster count is chosen from the data: we merge with average-linkage
    agglomerative clustering under a cosine-distance threshold, which needs no
    ``k``. ``max_clusters`` optionally caps the count (largest clusters kept).
    """
    n = len(sources)
    if n == 0:
        return [], np.zeros((0, 0))
    matrix, vec = structural_features(sources)
    X = matrix.toarray() if hasattr(matrix, "toarray") else matrix
    if n == 1 or vec is None:
        return [Cluster(0, list(range(n)), 0)], np.zeros((n, n))
    dist = pairwise_distances(X, metric="cosine")
    # distance_threshold=0 would put every unique shape in its own cluster;
    # 0.5 cosine merges programs sharing most of their AST-path vocabulary.
    model = AgglomerativeClustering(
        n_clusters=None, distance_threshold=0.5,
        metric="precomputed", linkage="average")
    labels = model.fit_predict(dist)

    clusters: list[Cluster] = []
    for lab in sorted(set(labels)):
        members = [i for i in range(n) if labels[i] == lab]
        clusters.append(Cluster(int(lab), members, _medoid(members, dist)))
    clusters.sort(key=lambda c: -len(c.members))
    if max_clusters is not None:
        clusters = clusters[:max_clusters]
    return clusters, dist


# --------------------------------------------------------------- reference pick
def nearest_reference(buggy: str, reference_pool: list[str],
                      rng=None, min_cluster_size: int = 2) -> str | None:
    """Pick a strategy-matched reference for a buggy program.

    Cluster the reference pool on the structural view; find the cluster whose
    medoid is structurally closest to ``buggy``; return one member of that
    cluster at random. Local, no LLM cost.
    """
    import random
    rng = rng or random.Random(7)
    pool = [r for r in reference_pool if r.strip()]
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]

    clusters, _ = cluster(pool, min_cluster_size=min_cluster_size)
    if not clusters:
        return rng.choice(pool)

    # embed buggy + medoids together so they share a vocabulary, then compare
    medoid_srcs = [pool[c.medoid] for c in clusters]
    matrix, vec = structural_features([buggy] + medoid_srcs)
    if vec is None:
        return rng.choice(pool)
    X = matrix.toarray() if hasattr(matrix, "toarray") else matrix
    d = pairwise_distances(X[:1], X[1:], metric="cosine")[0]
    nearest = clusters[int(d.argmin())]
    return pool[rng.choice(nearest.members)]
