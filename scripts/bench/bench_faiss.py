"""
FAISS Search Latency, Memory Footprint, and Recall Benchmark.
Evaluates Flat (exact cosine baseline), HNSW (graph-based), and IVF-PQ (inverted file product quantization)
across corpus sizes of 10,000, 100,000, and 1,000,000 vectors with dimension 768.

Computes exact Recall@5 against the Flat baseline.
"""
import os
import sys
import time
import json
import psutil
import faiss
import numpy as np

DIM = 768
TOP_K = 5
NUM_QUERIES = 100


def get_process_memory_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def generate_synthetic_embeddings(n_vectors: int, seed: int = 42) -> np.ndarray:
    """Generate normalized unit-length vectors with dimension 768."""
    rng = np.random.default_rng(seed)
    data = rng.standard_normal((n_vectors, DIM)).astype(np.float32)
    faiss.normalize_L2(data)
    return data


def benchmark_corpus(n_vectors: int):
    print(f"\n=======================================================")
    print(f"Benchmarking Corpus Size: {n_vectors:,} vectors (dim={DIM})")
    print(f"=======================================================")

    results = {}
    queries = generate_synthetic_embeddings(NUM_QUERIES, seed=999)

    # 1. Base memory
    mem_before = get_process_memory_mb()
    print(f"Generating {n_vectors:,} embeddings...")
    t0 = time.time()
    corpus = generate_synthetic_embeddings(n_vectors, seed=42)
    gen_time = time.time() - t0
    print(f"Generated in {gen_time:.2f}s")

    # ----------------------------------------------------
    # IndexFlatIP (Baseline Ground Truth)
    # ----------------------------------------------------
    print("\n--- 1. IndexFlatIP (Exact Cosine Baseline) ---")
    mem_start = get_process_memory_mb()
    t_build_start = time.time()
    index_flat = faiss.IndexFlatIP(DIM)
    index_flat.add(corpus)
    build_flat_time = time.time() - t_build_start
    mem_flat = get_process_memory_mb() - mem_start

    # Benchmark search
    latencies = []
    ground_truth_indices = []
    for q in queries:
        q_vec = np.array([q], dtype=np.float32)
        t_start = time.perf_counter()
        distances, indices = index_flat.search(q_vec, TOP_K)
        t_dur = (time.perf_counter() - t_start) * 1000.0  # ms
        latencies.append(t_dur)
        ground_truth_indices.append(set(indices[0]))

    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    p99 = float(np.percentile(latencies, 99))
    print(f"Flat Memory Added: {mem_flat:.2f} MB")
    print(f"Flat Build Time: {build_flat_time:.3f} s")
    print(f"Flat Search Latency (ms): p50={p50:.3f}, p95={p95:.3f}, p99={p99:.3f}")

    results["Flat"] = {
        "memory_mb": round(mem_flat, 2),
        "build_time_s": round(build_flat_time, 3),
        "search_p50_ms": round(p50, 3),
        "search_p95_ms": round(p95, 3),
        "search_p99_ms": round(p99, 3),
        "recall_at_5": 1.0,
    }

    # ----------------------------------------------------
    # IndexHNSWFlat
    # ----------------------------------------------------
    print("\n--- 2. IndexHNSWFlat (M=32, efSearch=64) ---")
    mem_start = get_process_memory_mb()
    t_build_start = time.time()
    index_hnsw = faiss.IndexHNSWFlat(DIM, 32, faiss.METRIC_INNER_PRODUCT)
    index_hnsw.hnsw.efSearch = 64
    index_hnsw.hnsw.efConstruction = 64
    index_hnsw.add(corpus)
    build_hnsw_time = time.time() - t_build_start
    mem_hnsw = get_process_memory_mb() - mem_start

    hnsw_latencies = []
    recall_hits = 0
    total_expected = NUM_QUERIES * TOP_K
    for i, q in enumerate(queries):
        q_vec = np.array([q], dtype=np.float32)
        t_start = time.perf_counter()
        distances, indices = index_hnsw.search(q_vec, TOP_K)
        t_dur = (time.perf_counter() - t_start) * 1000.0
        hnsw_latencies.append(t_dur)
        retrieved_set = set(indices[0])
        recall_hits += len(retrieved_set.intersection(ground_truth_indices[i]))

    p50_h = float(np.percentile(hnsw_latencies, 50))
    p95_h = float(np.percentile(hnsw_latencies, 95))
    p99_h = float(np.percentile(hnsw_latencies, 99))
    recall_h = recall_hits / total_expected
    print(f"HNSW Memory Added: {mem_hnsw:.2f} MB")
    print(f"HNSW Build Time: {build_hnsw_time:.3f} s")
    print(f"HNSW Search Latency (ms): p50={p50_h:.3f}, p95={p95_h:.3f}, p99={p99_h:.3f}")
    print(f"HNSW Recall@5 vs Flat: {recall_h:.4f}")

    results["HNSW"] = {
        "memory_mb": round(mem_hnsw, 2),
        "build_time_s": round(build_hnsw_time, 3),
        "search_p50_ms": round(p50_h, 3),
        "search_p95_ms": round(p95_h, 3),
        "search_p99_ms": round(p99_h, 3),
        "recall_at_5": round(recall_h, 4),
    }

    # ----------------------------------------------------
    # IndexIVFPQ
    # ----------------------------------------------------
    print("\n--- 3. IndexIVFPQ (nlist=100, m=64, 8 bits) ---")
    mem_start = get_process_memory_mb()
    t_build_start = time.time()
    quantizer = faiss.IndexFlatIP(DIM)
    nlist = 100 if n_vectors < 500000 else 1024
    index_ivfpq = faiss.IndexIVFPQ(quantizer, DIM, nlist, 64, 8)
    index_ivfpq.nprobe = 16
    train_size = min(len(corpus), 50000)
    index_ivfpq.train(corpus[:train_size])
    index_ivfpq.add(corpus)
    build_ivfpq_time = time.time() - t_build_start
    mem_ivfpq = get_process_memory_mb() - mem_start

    ivfpq_latencies = []
    recall_hits_ivf = 0
    for i, q in enumerate(queries):
        q_vec = np.array([q], dtype=np.float32)
        t_start = time.perf_counter()
        distances, indices = index_ivfpq.search(q_vec, TOP_K)
        t_dur = (time.perf_counter() - t_start) * 1000.0
        ivfpq_latencies.append(t_dur)
        retrieved_set = set(indices[0])
        recall_hits_ivf += len(retrieved_set.intersection(ground_truth_indices[i]))

    p50_ivf = float(np.percentile(ivfpq_latencies, 50))
    p95_ivf = float(np.percentile(ivfpq_latencies, 95))
    p99_ivf = float(np.percentile(ivfpq_latencies, 99))
    recall_ivf = recall_hits_ivf / total_expected
    print(f"IVF-PQ Memory Added: {mem_ivfpq:.2f} MB")
    print(f"IVF-PQ Build Time: {build_ivfpq_time:.3f} s")
    print(f"IVF-PQ Search Latency (ms): p50={p50_ivf:.3f}, p95={p95_ivf:.3f}, p99={p99_ivf:.3f}")
    print(f"IVF-PQ Recall@5 vs Flat: {recall_ivf:.4f}")

    results["IVF-PQ"] = {
        "memory_mb": round(mem_ivfpq, 2),
        "build_time_s": round(build_ivfpq_time, 3),
        "search_p50_ms": round(p50_ivf, 3),
        "search_p95_ms": round(p95_ivf, 3),
        "search_p99_ms": round(p99_ivf, 3),
        "recall_at_5": round(recall_ivf, 4),
    }

    return results


def main():
    sizes = [10000, 100000]
    # Check if user requested 1M
    if "--include-1m" in sys.argv:
        sizes.append(1000000)

    all_results = {}
    for sz in sizes:
        all_results[str(sz)] = benchmark_corpus(sz)

    out_file = os.path.join(os.path.dirname(__file__), "faiss_benchmark_results.json")
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved benchmark results to {out_file}")


if __name__ == "__main__":
    main()

