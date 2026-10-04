"""MLOps-tracked K-Means clustering pipeline for Grad Cafe program names.

Adapts the Module 9 clustering workflow (TF-IDF vectorization, PCA
dimensionality reduction, K-Means clustering) into a single pipeline
that trains one K-Means model with a fixed, required set of
hyperparameters and tracks the run with MLflow: parameters, the
resulting inertia metric, and the fitted model artifact are all logged
to an MLflow tracking server for later inspection in the MLflow UI.

Typical usage example::

    python kmeans_mlops_pipeline.py

Expects a file named ``cleaned_gradcafe.json`` in the same directory as
this script, and an MLflow tracking server already running and
reachable at the URI configured in ``MLFLOW_TRACKING_URI`` below
(defaults to a local server on port 8080; see README.md for how to
start one).
"""

import json
import os

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline
from scipy.sparse import csr_matrix
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

# MLflow tracking server configuration. "localhost" is used since this
# pipeline is intended to run against a locally started MLflow server;
# swap in a remote IP address here if tracking against a shared server.
MLFLOW_TRACKING_URI = "http://localhost:8080"
MLFLOW_EXPERIMENT_NAME = "gradcafe-kmeans-clustering"
MLFLOW_RUN_NAME = "kmeans-required-params"

# Registered model name used when logging the fitted model to MLflow,
# so it's easy to identify among other models in the registry.
MODEL_NAME = "Clustering"

# Required K-Means hyperparameters for this assignment. Passed directly
# into KMeans(**CLUSTERING_PARAMS) below, and logged to MLflow exactly
# as used, so the tracked parameters always reflect what actually
# trained the model rather than a separately maintained record.
CLUSTERING_PARAMS = {
    "max_iter": 500,
    "n_clusters": 25,
    "n_init": 5,
    "random_state": 42,
}

# Number of PCA components the TF-IDF features are reduced to before
# clustering. Kept well above 2 (which would only suit 2D
# visualization) so K-Means has enough retained variance to work with.
PCA_COMPONENTS = 50


def get_script_dir() -> str:
    """Return the absolute path of the directory containing this script.

    Used so the data file is loaded relative to the script's own
    location rather than the current working directory, avoiding any
    machine-specific absolute paths.

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
    file_path = os.path.join(get_script_dir(), filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Could not find '{filename}' in '{get_script_dir()}'. "
            "Place the Grad Cafe JSON file alongside kmeans_mlops_pipeline.py."
        )

    with open(file_path, "r", encoding="utf-8") as json_file:
        records = json.load(json_file)

    return pd.DataFrame(records)


def clean_program_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Clean the Program column and drop unusable rows.

    Mirrors the Module 9 approach: the LLM-normalized
    ``llm-generated-program`` field is used as the source for the
    working ``Program`` column, since it's cleaner and more consistent
    than the raw scraped field. Rows are dropped when the resulting
    ``Program`` value is missing, empty, the literal string ``"None"``,
    or blank after stripping whitespace, and remaining values are
    whitespace-normalized for consistent TF-IDF vectorization.

    :param dataframe: Raw Grad Cafe DataFrame containing an
        ``llm-generated-program`` column.
    :type dataframe: pandas.DataFrame
    :return: Cleaned copy of the DataFrame with invalid program rows
        removed and text normalized, exposing a ``Program`` column.
    :rtype: pandas.DataFrame
    """
    cleaned = dataframe.copy()

    cleaned["Program"] = cleaned["llm-generated-program"]
    cleaned["Program"] = cleaned["Program"].replace(["None", ""], pd.NA)
    cleaned = cleaned.dropna(subset=["Program"])

    cleaned["Program"] = (
        cleaned["Program"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )
    cleaned = cleaned[cleaned["Program"] != ""]

    return cleaned.reset_index(drop=True)


def vectorize_programs(dataframe: pd.DataFrame) -> tuple[csr_matrix, TfidfVectorizer]:
    """Vectorize the cleaned ``Program`` column into TF-IDF features.

    :param dataframe: Cleaned Grad Cafe DataFrame containing a
        ``Program`` column of normalized program-name text.
    :type dataframe: pandas.DataFrame
    :return: A tuple of the resulting sparse TF-IDF feature matrix and
        the fitted vectorizer instance.
    :rtype: tuple[scipy.sparse.csr_matrix, sklearn.feature_extraction.text.TfidfVectorizer]
    """
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(dataframe["Program"])
    return tfidf_matrix, vectorizer


def reduce_dimensions_with_pca(
    tfidf_matrix: csr_matrix, n_components: int = PCA_COMPONENTS, random_state: int = 42
) -> tuple[np.ndarray, PCA]:
    """Reduce TF-IDF features to a lower-dimensional PCA representation.

    :param tfidf_matrix: Sparse TF-IDF feature matrix produced by
        :func:`vectorize_programs`.
    :type tfidf_matrix: scipy.sparse.csr_matrix
    :param n_components: Number of PCA components to keep.
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


def compute_elbow_inertias(
    pca_features: np.ndarray, max_k: int = 100, step: int = 1, random_state: int = 42
) -> tuple[list[int], list[float]]:
    """Fit K-Means across a range of cluster counts and record inertia.

    Reused from the Module 9 pipeline: cluster counts are swept from 1
    through ``max_k`` inclusive in increments of ``step`` (k=0 is
    invalid for K-Means and is therefore never attempted), fitting a
    fresh K-Means model at each step and recording its inertia (the sum
    of squared distances from each point to its assigned centroid).

    :param pca_features: PCA feature array to sweep cluster counts over.
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

    Reused from the Module 9 pipeline: fits a smoothing cubic spline to
    the (k, inertia) points, then uses its analytic first and second
    derivatives to compute curvature at a fine grid of k values:

        curvature(k) = |inertia''(k)| / (1 + inertia'(k)**2) ** 1.5

    Curvature is high where the "velocity" of inertia decline
    (inertia'(k)) is changing sharply - i.e. where the curve bends most
    tightly, from fast decline to a near-flat tail. The elbow is taken
    to be the k value with maximum curvature.

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

    smoothing_factor = len(k_array)
    spline = UnivariateSpline(k_array, inertia_array, k=3, s=smoothing_factor)

    fine_k = np.linspace(k_array.min(), k_array.max(), num=500)
    first_derivative = spline.derivative(n=1)(fine_k)
    second_derivative = spline.derivative(n=2)(fine_k)
    curvature = np.abs(second_derivative) / np.power(1 + first_derivative**2, 1.5)

    elbow_k = fine_k[np.argmax(curvature)]
    return int(round(elbow_k))


def train_kmeans_with_tracking(
    pca_features: np.ndarray, params: dict
) -> tuple[np.ndarray, KMeans]:
    """Train K-Means with the given parameters and log the run to MLflow.

    Starts an MLflow run, logs the exact hyperparameters K-Means is
    trained with, fits the model, logs its resulting inertia as a
    tracked metric, and logs (and registers) the fitted model as an
    MLflow model artifact under :data:`MODEL_NAME`, so the run,
    metric, and model are all visible together in the MLflow UI.

    :param pca_features: PCA-reduced feature array to cluster.
    :type pca_features: numpy.ndarray
    :param params: K-Means hyperparameters (``max_iter``,
        ``n_clusters``, ``n_init``, ``random_state``), passed directly
        into :class:`~sklearn.cluster.KMeans`.
    :type params: dict
    :return: A tuple of the cluster label assigned to each row and the
        fitted K-Means model.
    :rtype: tuple[numpy.ndarray, sklearn.cluster.KMeans]
    """
    with mlflow.start_run(run_name=MLFLOW_RUN_NAME):
        # Log the exact parameters the model below is trained with,
        # rather than a separately maintained record, so tracked values
        # can never drift from what actually trained the model.
        mlflow.log_params(params)

        kmeans_model = KMeans(**params)
        cluster_labels = kmeans_model.fit_predict(pca_features)

        # inertia_ only exists after fitting, so it's logged as a
        # metric (a measured result) rather than a parameter (a
        # pre-chosen input).
        mlflow.log_metric("inertia", kmeans_model.inertia_)

        mlflow.sklearn.log_model(
            kmeans_model,
            name=MODEL_NAME,
            registered_model_name=MODEL_NAME,
        )

        run_id = mlflow.active_run().info.run_id
        print(f"Logged MLflow run: {run_id}")
        print(f"Inertia for this run: {kmeans_model.inertia_:.4f}")

    return cluster_labels, kmeans_model


def main() -> None:
    """Run the Grad Cafe K-Means clustering pipeline with MLflow tracking.

    :return: None.
    :rtype: None
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    raw_data = load_data()
    cleaned_data = clean_program_data(raw_data)
    print(f"Cleaned dataset entry count: {len(cleaned_data)}")

    tfidf_matrix, _vectorizer = vectorize_programs(cleaned_data)
    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

    pca_features, _pca_model = reduce_dimensions_with_pca(tfidf_matrix)
    print(f"PCA feature shape: {pca_features.shape}")

    # Find the elbow before training, as in Module 9. The estimate is
    # printed for reference, but the tracked model below still trains
    # with the assignment's required n_clusters=25 regardless of what
    # the elbow suggests, since that parameter is fixed by the rubric.
    k_values, inertias = compute_elbow_inertias(pca_features)
    estimated_k = estimate_elbow_k(k_values, inertias)
    print(f"Elbow-estimated optimal cluster count: {estimated_k}")
    print(f"Proceeding with required n_clusters={CLUSTERING_PARAMS['n_clusters']} for tracking.")

    _cluster_labels, kmeans_model = train_kmeans_with_tracking(
        pca_features, CLUSTERING_PARAMS
    )
    print(f"Trained KMeans with {kmeans_model.n_clusters} clusters.")


if __name__ == "__main__":
    main()
