"""K-Means clustering analysis of Grad Cafe graduate program names.

This module loads the Grad Cafe results dataset, cleans and inspects it,
vectorizes program names with TF-IDF, reduces dimensionality with PCA,
clusters programs with K-Means, determines an optimal cluster count via
the elbow method, and analyzes GRE score distributions across selected
program clusters (Computer Science-like vs. Philosophy-like).

Typical usage example::

    python kmeans.py

Expects a file named ``cleaned_gradcafe.json`` in the same directory as
this script.
"""

import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from scipy.sparse import csr_matrix
from scipy.interpolate import UnivariateSpline
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

# Use a non-interactive backend since plots are saved to file, not shown.
matplotlib.use("Agg")

def get_script_dir() -> str:
    """Return the absolute path of the directory containing this script.

    Used so that data files are loaded, and output artifacts (plots,
    etc.) are saved, relative to the script's own location rather than
    the current working directory.

    :return: Absolute path of this script's parent directory.
    :rtype: str
    """
    return os.path.dirname(os.path.abspath(__file__))

def load_data(filename: str = "cleaned_gradcafe.json") -> pd.DataFrame:
    """Load the Grad Cafe dataset from a JSON file in the script's folder.

    :param filename: Name of the JSON file to load, expected to live in
        the same directory as this script.
    :type filename: str
    :return: Raw Grad Cafe records as a DataFrame.
    :rtype: pandas.DataFrame
    :raises FileNotFoundError: If the JSON file cannot be located.
    """
    script_dir = get_script_dir()
    file_path = os.path.join(script_dir, filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Could not find '{filename}' in '{script_dir}'. "
            "Place the Grad Cafe JSON file alongside kmeans.py."
        )

    with open(file_path, "r", encoding="utf-8") as json_file:
        records = json.load(json_file)

    return pd.DataFrame(records)

def clean_program_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Clean the Program/University columns and drop unusable rows.

    Per instructor guidance, the LLM-normalized ``llm-generated-program``
    and ``llm-generated-university`` fields are used as the source for
    the working ``Program`` and ``University`` columns, since they are
    cleaner and more consistent than the raw scraped fields. Rows are
    dropped when the resulting ``Program`` value is missing (``NaN``),
    empty, the literal string ``"None"``, or blank after stripping
    whitespace. Remaining ``Program`` and ``University`` values are
    stripped of leading/trailing whitespace and collapsed internal
    whitespace is normalized to single spaces for consistent TF-IDF
    vectorization.

    :param dataframe: Raw Grad Cafe DataFrame containing
        ``llm-generated-program`` and, when available,
        ``llm-generated-university`` columns.
    :type dataframe: pandas.DataFrame
    :return: Cleaned copy of the DataFrame with invalid program rows
        removed and text fields normalized, exposing ``Program`` and
        ``University`` columns sourced from the LLM-generated fields.
    :rtype: pandas.DataFrame
    """
    cleaned = dataframe.copy()

    # Use the LLM-normalized data per instructor preference.
    # Program and University are already split individually.
    # Copy to Program and University to match the instructions
    cleaned["Program"] = cleaned["llm-generated-program"]
    cleaned["University"] = cleaned["llm-generated-university"]

    # Treat missing values, empty strings, and the literal string "None"
    # as missing.
    cleaned["Program"] = cleaned["Program"].replace(["None", ""], pd.NA)
    cleaned = cleaned.dropna(subset=["Program"])

    # Normalize whitespace so near-duplicate labels vectorize consistently.
    cleaned["Program"] = (
        cleaned["Program"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )

    # Drop rows that became blank after stripping whitespace.
    cleaned = cleaned[cleaned["Program"] != ""]

    cleaned["University"] = cleaned["University"].replace(["None", ""], pd.NA)
    cleaned["University"] = (
        cleaned["University"]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    cleaned = cleaned.reset_index(drop=True)
    return cleaned

def vectorize_programs(dataframe: pd.DataFrame) -> tuple[csr_matrix, TfidfVectorizer]:
    """Vectorize the cleaned ``Program`` column into TF-IDF features.

    Fits a :class:`~sklearn.feature_extraction.text.TfidfVectorizer` on
    the cleaned program-name text so that each program name becomes a
    row in a sparse TF-IDF feature matrix, suitable as input to PCA and
    K-Means clustering.

    :param dataframe: Cleaned Grad Cafe DataFrame containing a
        ``Program`` column of normalized program-name text.
    :type dataframe: pandas.DataFrame
    :return: A tuple of the resulting sparse TF-IDF feature matrix and
        the fitted vectorizer instance (retained for inspecting learned
        vocabulary and for use in downstream re-vectorization if needed).
    :rtype: tuple[scipy.sparse.csr_matrix, sklearn.feature_extraction.text.TfidfVectorizer]
    """
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(dataframe["Program"])
    return tfidf_matrix, vectorizer

def run_pca_model(
    tfidf_matrix: csr_matrix, n_components: int, random_state: int = 42
) -> tuple[np.ndarray, PCA]:
    """Reduce TF-IDF features to a given number of PCA components.
 
    Used both for the 2-component representation needed for the initial
    cluster visualization, and for the higher-dimensional (50-100
    component) representation needed for elbow analysis and final
    clustering, since two components alone are too flattened to capture
    the variability elbow analysis relies on.
 
    :param tfidf_matrix: Sparse TF-IDF feature matrix produced by
        :func:`vectorize_programs`.
    :type tfidf_matrix: scipy.sparse.csr_matrix
    :param n_components: Number of PCA components to keep (e.g. 2 for
        visualization, or 50-100 for elbow analysis and final clustering).
    :type n_components: int
    :param random_state: Seed controlling PCA's internal randomized SVD
        solver, for reproducible results across runs.
    :type random_state: int
    :return: A tuple of the resulting PCA feature array and the fitted
        PCA model.
    :rtype: tuple[numpy.ndarray, sklearn.decomposition.PCA]
    """
    pca_model = PCA(n_components=n_components, random_state=random_state)
    pca_features = pca_model.fit_transform(tfidf_matrix.toarray())
    return pca_features, pca_model

def cluster_programs(
    pca_features: np.ndarray, n_clusters: int, random_state: int = 42
) -> tuple[np.ndarray, KMeans]:
    """Cluster PCA-reduced program features with K-Means.

    Used both for the initial 50-cluster fit on 2D PCA features (for
    visualization) and the final fit on higher-dimensional PCA features
    at the cluster count selected from elbow analysis; both stages use
    identical K-Means settings and differ only in the PCA features and
    cluster count passed in.

    :param pca_features: PCA feature array to cluster (2D for the
        initial visualization, higher-dimensional for final clustering).
    :type pca_features: numpy.ndarray
    :param n_clusters: Number of clusters to fit.
    :type n_clusters: int
    :param random_state: Seed controlling K-Means centroid initialization,
        for reproducible cluster assignments across runs.
    :type random_state: int
    :return: A tuple of the cluster label assigned to each row and the
        fitted K-Means model.
    :rtype: tuple[numpy.ndarray, sklearn.cluster.KMeans]
    """
    kmeans_model = KMeans(
        n_clusters=n_clusters, max_iter=100, n_init=5, random_state=random_state
    )
    cluster_labels = kmeans_model.fit_predict(pca_features)
    return cluster_labels, kmeans_model

def plot_initial_clusters(pca_features: np.ndarray, cluster_labels: np.ndarray) -> None:
    """Plot and save the initial 50-cluster K-Means result.

    Produces a 2D scatter plot of the PCA-reduced program features,
    colored by K-Means cluster assignment, and saves it as
    ``initial_cluster.png`` in the script's directory.

    :param pca_features: 2D PCA feature array produced by
        :func:`reduce_to_two_dimensions`.
    :type pca_features: numpy.ndarray
    :param cluster_labels: Cluster label assigned to each row, produced
        by :func:`cluster_initial_programs`.
    :type cluster_labels: numpy.ndarray
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    figure, axes = plt.subplots(figsize=(10, 8))
    scatter = axes.scatter(
        pca_features[:, 0],
        pca_features[:, 1],
        c=cluster_labels,
        cmap="nipy_spectral",
        s=10,
        alpha=0.7,
    )

    axes.set_title("Initial K-Means Clustering of Grad Cafe Programs (k=50)")
    axes.set_xlabel("Principal Component 1 (unitless)")
    axes.set_ylabel("Principal Component 2 (unitless)")

    # A colorbar acts as the legend here since a 50-entry discrete legend
    # would be unreadable; it maps point color back to cluster ID.
    colorbar = figure.colorbar(scatter, ax=axes)
    colorbar.set_label("Cluster ID")

    output_path = os.path.join(get_script_dir(), "initial_cluster.png")
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)

def attach_cluster_labels(
    dataframe: pd.DataFrame, cluster_labels: np.ndarray, column_name: str = "Cluster"
) -> pd.DataFrame:
    """Return cluster assignments to a copy of the cleaned DataFrame.

    Cluster labels are assigned by simple positional alignment: row *i*
    of ``cluster_labels`` corresponds to row *i* of ``dataframe``. This
    holds correctly here because ``cluster_labels`` was produced from
    features derived, in order, from this same DataFrame (via TF-IDF
    vectorization and PCA), with no intermediate sorting or shuffling.

    :param dataframe: Cleaned Grad Cafe DataFrame (or a superset of it)
        whose row order matches the order used to compute
        ``cluster_labels``.
    :type dataframe: pandas.DataFrame
    :param cluster_labels: Cluster label assigned to each row, produced
        by :func:`cluster_initial_programs` or :func:`cluster_final_programs`.
    :type cluster_labels: numpy.ndarray
    :param column_name: Name of the column to store cluster labels under,
        allowing initial and final cluster assignments to coexist on the
        same DataFrame under different column names.
    :type column_name: str
    :return: Copy of ``dataframe`` with an added cluster-label column.
    :rtype: pandas.DataFrame
    """
    clustered = dataframe.copy()
    clustered[column_name] = cluster_labels
    return clustered

def save_clustered_dataframe_sample(
    clustered_dataframe: pd.DataFrame, sample_size: int = 100, random_state: int = 42
) -> pd.DataFrame:
    """Display and save a sample of the clustered DataFrame as an image.

    Selects a random sample of rows showing the program name, university,
    and assigned cluster, prints it, and renders it as a table image
    saved to ``clustered_dataFrame.png`` in the script's directory.

    :param clustered_dataframe: DataFrame produced by
        :func:`attach_cluster_labels`, containing ``Program``,
        ``University``, and ``Cluster`` columns.
    :type clustered_dataframe: pandas.DataFrame
    :param sample_size: Number of rows to sample and display.
    :type sample_size: int
    :param random_state: Seed controlling row sampling, for a
        reproducible sample across runs.
    :type random_state: int
    :return: The sampled DataFrame that was displayed and saved.
    :rtype: pandas.DataFrame
    """
    columns = ["Program", "University", "Cluster"]
    row_count = min(sample_size, len(clustered_dataframe))
    sample = (
        clustered_dataframe[columns]
        .sample(n=row_count, random_state=random_state)
        .sort_index()
        .reset_index(drop=True)
    )

    print(f"Creating Clustered DataFrame sample ({row_count} rows)")
    # print(sample.to_string())

    figure_height = max(4.0, 0.22 * row_count)
    figure, axes = plt.subplots(figsize=(10, figure_height))
    axes.axis("off")
    axes.set_title(f"Sample of Clustered Grad Cafe Programs ({row_count} rows)", pad=20)

    table = axes.table(
        cellText=sample.values,
        colLabels=sample.columns,
        cellLoc="left",
        # Pin the table to the axes bounds so scaling row height below
        # can't push rows past the top edge and into the title.
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.2)

    output_path = os.path.join(get_script_dir(), "clustered_dataFrame.png")
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)

    return sample

def compute_elbow_inertias(
    pca_features: np.ndarray, max_k: int = 100, step: int = 1, random_state: int = 42
) -> tuple[list[int], list[float]]:
    """Fit K-Means across a range of cluster counts and record inertia.

    Cluster counts are swept from 1 through ``max_k`` inclusive in
    increments of ``step`` (k=0 is invalid for K-Means and is therefore
    never attempted), fitting a fresh K-Means model at each step and
    recording its inertia (the sum of squared distances from each point
    to its assigned centroid). A coarser ``step`` trades a small amount
    of precision in the estimated elbow location for a proportional
    reduction in runtime, since the elbow method only needs the overall
    shape of the inertia curve rather than every individual k value.

    :param pca_features: Higher-dimensional PCA feature array produced
        by :func:`expand_pca_dimensions`.
    :type pca_features: numpy.ndarray
    :param max_k: Largest cluster count to try, inclusive.
    :type max_k: int
    :param step: Increment between successive cluster counts tried.
        A step of 1 checks every k; larger steps reduce runtime at the
        cost of coarser resolution in the resulting elbow estimate.
    :type step: int
    :param random_state: Seed controlling K-Means centroid initialization,
        for reproducible inertia values across runs.
    :type random_state: int
    :return: A tuple of the list of cluster counts tried and the
        corresponding list of inertia values, in matching order.
    :rtype: tuple[list[int], list[float]]
    """
    k_values = list(range(1, max_k + 1, step))
    if k_values[-1] != max_k:
        k_values.append(max_k)
    inertias = []

    for k in k_values:
        kmeans_model = KMeans(n_clusters=k, max_iter=100, n_init=5, random_state=random_state)
        kmeans_model.fit(pca_features)
        inertias.append(kmeans_model.inertia_)

    return k_values, inertias

def estimate_elbow_k(k_values: list[int], inertias: list[float]) -> int:
    """Estimate the elbow point of an inertia curve via maximum curvature.

    Fits a smoothing cubic spline to the (k, inertia) points, then uses
    its analytic first and second derivatives to compute curvature at a
    fine grid of k values:

        curvature(k) = |inertia''(k)| / (1 + inertia'(k)**2) ** 1.5

    Curvature is high where the "velocity" of inertia decline
    (inertia'(k)) is changing sharply — i.e. where the curve bends most
    tightly, from fast decline to a near-flat tail. The elbow is taken
    to be the k value with maximum curvature, which requires no
    arbitrary slope or distance threshold; the point of sharpest bend is
    well-defined regardless of the curve's absolute scale.

    :param k_values: Cluster counts tried, as returned by
        :func:`compute_elbow_inertias`.
    :type k_values: list[int]
    :param inertias: Inertia values corresponding to each cluster count,
        as returned by :func:`compute_elbow_inertias`.
    :type inertias: list[float]
    :return: The estimated optimal number of clusters.
    :rtype: int
    """
    k_array = np.array(k_values, dtype=float)
    inertia_array = np.array(inertias, dtype=float)

    # A small amount of smoothing (scipy's suggested rule-of-thumb range
    # is roughly len(x) +/- sqrt(2*len(x))) keeps the fitted curve from
    # chasing small run-to-run fluctuations in K-Means inertia while
    # still tracking the curve's overall shape.
    smoothing_factor = len(k_array)
    spline = UnivariateSpline(k_array, inertia_array, k=3, s=smoothing_factor)

    fine_k = np.linspace(k_array.min(), k_array.max(), num=500)
    first_derivative = spline.derivative(n=1)(fine_k)
    second_derivative = spline.derivative(n=2)(fine_k)
    curvature = np.abs(second_derivative) / np.power(1 + first_derivative**2, 1.5)

    elbow_k = fine_k[np.argmax(curvature)]
    return int(round(elbow_k))


def plot_elbow_curve(k_values: list[int], inertias: list[float], estimated_k: int) -> None:
    """Plot and save the elbow-method inertia curve.

    Produces a line plot of inertia versus cluster count, marks the
    estimated elbow point, and saves it as ``elbow.png`` in the script's
    directory.

    :param k_values: Cluster counts tried, as returned by
        :func:`compute_elbow_inertias`.
    :type k_values: list[int]
    :param inertias: Inertia values corresponding to each cluster count,
        as returned by :func:`compute_elbow_inertias`.
    :type inertias: list[float]
    :param estimated_k: The estimated optimal number of clusters, as
        returned by :func:`estimate_elbow_k`, highlighted on the plot.
    :type estimated_k: int
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    figure, axes = plt.subplots(figsize=(10, 6))
    axes.plot(k_values, inertias, marker="o", markersize=3, label="Inertia per k")
    axes.axvline(
        estimated_k,
        color="red",
        linestyle="--",
        label=f"Estimated elbow (k={estimated_k})",
    )

    axes.set_title("Elbow Method for Optimal Number of Clusters")
    axes.set_xlabel("Number of Clusters (k)")
    axes.set_ylabel("Inertia (Sum of Squared Distances)")
    axes.legend()

    output_path = os.path.join(get_script_dir(), "elbow.png")
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)

def find_dominant_cluster(
    dataframe: pd.DataFrame, keyword: str, cluster_column: str = "cluster"
) -> int:
    """Identify the cluster most associated with a program-name keyword.

    Finds all rows whose ``Program`` value contains ``keyword``
    (case-insensitive), then returns the cluster ID that keyword-matching
    rows most frequently belong to. This gives a code-supported way to
    locate a "Computer Science-like" or "Philosophy-like" cluster without
    hardcoding a specific cluster ID.

    :param dataframe: Clustered DataFrame containing ``Program`` and the
        specified cluster-label column.
    :type dataframe: pandas.DataFrame
    :param keyword: Substring to search for within program names, such
        as ``"computer science"`` or ``"philosophy"``.
    :type keyword: str
    :param cluster_column: Name of the column holding final cluster
        labels.
    :type cluster_column: str
    :return: The cluster ID most associated with the keyword.
    :rtype: int
    :raises ValueError: If no program names contain the keyword.
    """
    matches = dataframe[dataframe["Program"].str.contains(keyword, case=False, na=False)]

    if matches.empty:
        raise ValueError(f"No program names contain the keyword '{keyword}'.")

    return int(matches[cluster_column].value_counts().idxmax())

def get_cluster_subset(
    dataframe: pd.DataFrame, cluster_id: int, cluster_column: str = "cluster"
) -> pd.DataFrame:
    """Return all rows belonging to a given cluster.

    :param dataframe: Clustered DataFrame containing the specified
        cluster-label column.
    :type dataframe: pandas.DataFrame
    :param cluster_id: The cluster ID to filter for.
    :type cluster_id: int
    :param cluster_column: Name of the column holding final cluster
        labels.
    :type cluster_column: str
    :return: Rows belonging to ``cluster_id``.
    :rtype: pandas.DataFrame
    """
    return dataframe[dataframe[cluster_column] == cluster_id]

def report_gre_cluster_summary(cluster_label: str, cluster_subset: pd.DataFrame) -> None:
    """Print GRE and GRE V summary statistics for a program cluster.

    :param cluster_label: Human-readable name for the cluster, used in
        printed output (e.g. ``"Computer Science-like"``).
    :type cluster_label: str
    :param cluster_subset: Rows belonging to the cluster, as returned by
        :func:`get_cluster_subset`.
    :type cluster_subset: pandas.DataFrame
    :return: None. Summary statistics are printed to stdout.
    :rtype: None
    """
    gre_scores = cluster_subset["GRE"].dropna()
    gre_v_scores = cluster_subset["GRE V"].dropna()

    print(f"{cluster_label} cluster ({len(cluster_subset)} entries):")
    print(
        f"  GRE (Quant): n={len(gre_scores)}, "
        f"range={gre_scores.min() if len(gre_scores) else 'N/A'}-"
        f"{gre_scores.max() if len(gre_scores) else 'N/A'}, "
        f"median={gre_scores.median() if len(gre_scores) else float('nan'):.1f}"
    )
    print(
        f"  GRE V (Verbal): n={len(gre_v_scores)}, "
        f"range={gre_v_scores.min() if len(gre_v_scores) else 'N/A'}-"
        f"{gre_v_scores.max() if len(gre_v_scores) else 'N/A'}, "
        f"median={gre_v_scores.median() if len(gre_v_scores) else float('nan'):.1f}"
    )

def plot_gre_boxplot(
    cluster_subset: pd.DataFrame, cluster_label: str, output_filename: str
) -> None:
    """Plot and save a GRE / GRE V box plot for a single program cluster.

    :param cluster_subset: Rows belonging to the cluster, as returned by
        :func:`get_cluster_subset`.
    :type cluster_subset: pandas.DataFrame
    :param cluster_label: Human-readable name for the cluster, used in
        the plot title (e.g. ``"Computer Science-like"``).
    :type cluster_label: str
    :param output_filename: Filename to save the plot under, in the
        script's directory (e.g. ``"philosophy.png"``).
    :type output_filename: str
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    gre_scores = cluster_subset["GRE"].dropna()
    gre_v_scores = cluster_subset["GRE V"].dropna()
    box_colors = ["#4C72B0", "#DD8452"]

    figure, axes = plt.subplots(figsize=(6, 6))
    box = axes.boxplot(
        [gre_scores, gre_v_scores],
        tick_labels=["GRE (Quant)", "GRE V (Verbal)"],
        patch_artist=True,
        widths=0.5,
    )
    for patch, color in zip(box["boxes"], box_colors):
        patch.set_facecolor(color)

    axes.set_title(f"GRE Score Distribution: {cluster_label} Cluster")
    axes.set_xlabel("GRE Section")
    axes.set_ylabel("Score (points)")

    legend_handles = [
        Patch(facecolor=box_colors[0], label="GRE (Quant)"),
        Patch(facecolor=box_colors[1], label="GRE V (Verbal)"),
    ]
    axes.legend(handles=legend_handles)

    output_path = os.path.join(get_script_dir(), output_filename)
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)

def run_clustering_pipeline(
    cleaned_data: pd.DataFrame, tfidf_matrix: csr_matrix
) -> tuple[pd.DataFrame, np.ndarray]:
    """Run PCA, initial clustering, elbow analysis, and final clustering.

    :param cleaned_data: Cleaned Grad Cafe DataFrame.
    :type cleaned_data: pandas.DataFrame
    :param tfidf_matrix: Sparse TF-IDF feature matrix produced by
        :func:`vectorize_programs`.
    :type tfidf_matrix: scipy.sparse.csr_matrix
    :return: A tuple of the DataFrame with final cluster labels attached
        and the higher-dimensional PCA feature array used to produce
        them.
    :rtype: tuple[pandas.DataFrame, numpy.ndarray]
    """
    pca_features, pca_model = run_pca_model(tfidf_matrix, n_components=2)

    print(f"PCA feature shape: {pca_features.shape}")
    print(f"PCA configuration: {pca_model}")

    cluster_labels, _kmeans_model = cluster_programs(pca_features, n_clusters=50)
    plot_initial_clusters(pca_features, cluster_labels)

    clustered_data = attach_cluster_labels(cleaned_data, cluster_labels)
    save_clustered_dataframe_sample(clustered_data)

    print("Starting PCA expansion and elbow analysis for final cluster count estimation...")
    # Expand PCA to a higher-dimensional representation (50-100 components)
    expanded_pca_features, _expanded_pca_model = run_pca_model(
        tfidf_matrix, n_components=75
    )

    k_values, inertias = compute_elbow_inertias(expanded_pca_features)

    print("Estimating...")
    estimated_k = estimate_elbow_k(k_values, inertias)
    print(f"Estimated optimal number of clusters (elbow method): {estimated_k}")
    plot_elbow_curve(k_values, inertias, estimated_k)

    # Final clustering uses the higher-dimensional PCA representation
    final_cluster_labels, _final_kmeans_model = cluster_programs(
        expanded_pca_features, n_clusters=estimated_k
    )

    final_clustered_data = attach_cluster_labels(
        cleaned_data, final_cluster_labels, column_name="cluster"
    )

    return final_clustered_data, expanded_pca_features


def run_gre_cluster_analysis(final_clustered_data: pd.DataFrame) -> None:
    """Identify CS-like and Philosophy-like clusters and analyze GRE scores.

    :param final_clustered_data: DataFrame with a ``cluster`` column,
        as returned by :func:`run_clustering_pipeline`.
    :type final_clustered_data: pandas.DataFrame
    :return: None.
    :rtype: None
    """
    cs_cluster_id = find_dominant_cluster(final_clustered_data, "computer science")
    philosophy_cluster_id = find_dominant_cluster(final_clustered_data, "philosophy")

    cs_subset = get_cluster_subset(final_clustered_data, cs_cluster_id)
    philosophy_subset = get_cluster_subset(final_clustered_data, philosophy_cluster_id)

    print(f"Computer Science-like cluster label: {cs_cluster_id}")
    print(f"Philosophy-like cluster label: {philosophy_cluster_id}")

    report_gre_cluster_summary("Computer Science-like", cs_subset)
    report_gre_cluster_summary("Philosophy-like", philosophy_subset)

    plot_gre_boxplot(cs_subset, "Computer Science-like", "computer_science.png")
    plot_gre_boxplot(philosophy_subset, "Philosophy-like", "philosophy.png")

    print("""
          Analysis of the GRE data for the two clusters seems to be a reasonable spread.
          Both clusters demonstrate the "GRE total" vs "GRE-Q only" problem that I identified
          earlier. Both plots also show that there are still some items within the data that are
          out of bounds for our expected return (an item in the 600 range, for example).
          Data cleaning would need to drop the invalid scores, if there is a valid GRE V, then
          it would be possible to figure out the GRE Q score from the combined score. Otherwise,
          it might be necessary to divide the column data into two separate columns, one for
          combined, one for GRE Q.
          """)


def main() -> None:
    """Run the full Grad Cafe program-clustering and GRE analysis pipeline.

    :return: None.
    :rtype: None
    """
    raw_data = load_data()
    cleaned_data = clean_program_data(raw_data)

    print(f"Cleaned dataset entry count: {len(cleaned_data)}")
    print(f"Unique program input names: {len(sorted(cleaned_data['Program'].unique()))}")

    tfidf_matrix, _vectorizer = vectorize_programs(cleaned_data)

    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")
    print(f"TF-IDF matrix type: {type(tfidf_matrix)}")
    print(tfidf_matrix)

    final_clustered_data, _expanded_pca_features = run_clustering_pipeline(
        cleaned_data, tfidf_matrix
    )
    run_gre_cluster_analysis(final_clustered_data)


if __name__ == "__main__":
    main()
