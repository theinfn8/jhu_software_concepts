"""Exploratory visualizations for the mushroom edibility dataset.

This module loads a mushroom characteristics dataset (categorical
features plus a binary ``class`` target of edible/poisonous), measures
how strongly each feature is associated with edibility using a
bias-corrected Cramer's V, and produces three linked visualizations:

1. A Seaborn bar chart ranking every feature's association strength
   with edibility (``cramers_v_association.png``).
2. An interactive Plotly chart letting the viewer pick any feature from
   a dropdown to see its edibility breakdown by category
   (``edibility_by_feature.html``). It defaults to whichever feature
   ranked highest in the Cramer's V chart, tying the two visualizations
   together.
3. A Seaborn heatmap of raw edible/poisonous counts for that same
   top-ranked feature (``top_feature_class_heatmap.png``).

Typical usage example::

    python visualization.py

Expects a file named ``mushrooms.csv`` in the same directory as this
script, with a ``class`` column containing ``"e"`` (edible) or ``"p"``
(poisonous), and other columns holding single-letter categorical codes
(following the standard UCI Mushroom dataset schema). All codes are
decoded to full words before plotting.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from scipy.stats import chi2_contingency
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

# Target column
TARGET_COLUMN = "Class"

# Single-letter-code-to-word mappings for every column
COLUMN_VALUE_MAPS = {
    "class": {"e": "Edible", "p": "Poisonous"},
    "cap-shape": {
        "b": "Bell", "c": "Conical", "x": "Convex",
        "f": "Flat", "k": "Knobbed", "s": "Sunken",
    },
    "cap-surface": {"f": "Fibrous", "g": "Grooves", "y": "Scaly", "s": "Smooth"},
    "cap-color": {
        "n": "Brown", "b": "Buff", "c": "Cinnamon", "g": "Gray", "r": "Green",
        "p": "Pink", "u": "Purple", "e": "Red", "w": "White", "y": "Yellow",
    },
    "bruises": {"t": "Bruises", "f": "No bruises"},
    "odor": {
        "a": "Almond", "l": "Anise", "c": "Creosote", "y": "Fishy",
        "f": "Foul", "m": "Musty", "n": "None", "p": "Pungent", "s": "Spicy",
    },
    "gill-attachment": {
        "a": "Attached", "d": "Descending", "f": "Free", "n": "Notched",
    },
    "gill-spacing": {"c": "Close", "w": "Crowded", "d": "Distant"},
    "gill-size": {"b": "Broad", "n": "Narrow"},
    "gill-color": {
        "k": "Black", "n": "Brown", "b": "Buff", "h": "Chocolate",
        "g": "Gray", "r": "Green", "o": "Orange", "p": "Pink",
        "u": "Purple", "e": "Red", "w": "White", "y": "Yellow",
    },
    "stalk-shape": {"e": "Enlarging", "t": "Tapering"},
    "stalk-root": {
        "b": "Bulbous", "c": "Club", "u": "Cup", "e": "Equal",
        "z": "Rhizomorphs", "r": "Rooted", "?": "Missing",
    },
    "stalk-surface-above-ring": {"f": "Fibrous", "y": "Scaly", "k": "Silky", "s": "Smooth"},
    "stalk-surface-below-ring": {"f": "Fibrous", "y": "Scaly", "k": "Silky", "s": "Smooth"},
    "stalk-color-above-ring": {
        "n": "Brown", "b": "Buff", "c": "Cinnamon", "g": "Gray", "o": "Orange",
        "p": "Pink", "e": "Red", "w": "White", "y": "Yellow",
    },
    "stalk-color-below-ring": {
        "n": "Brown", "b": "Buff", "c": "Cinnamon", "g": "Gray", "o": "Orange",
        "p": "Pink", "e": "Red", "w": "White", "y": "Yellow",
    },
    "veil-type": {"p": "Partial", "u": "Universal"},
    "veil-color": {"n": "Brown", "o": "Orange", "w": "White", "y": "Yellow"},
    "ring-number": {"n": "None", "o": "One", "t": "Two"},
    "ring-type": {
        "c": "Cobwebby", "e": "Evanescent", "f": "Flaring", "l": "Large",
        "n": "None", "p": "Pendant", "s": "Sheathing", "z": "Zone",
    },
    "spore-print-color": {
        "k": "Black", "n": "Brown", "b": "Buff", "h": "Chocolate",
        "r": "Green", "o": "Orange", "u": "Purple", "w": "White", "y": "Yellow",
    },
    "population": {
        "a": "Abundant", "n": "Numerous", "c": "Clustered",
        "s": "Scattered", "v": "Several", "y": "Solitary",
    },
    "habitat": {
        "g": "Grasses", "l": "Leaves", "m": "Meadows", "p": "Paths",
        "u": "Urban", "w": "Waste", "d": "Woods",
    },
}

# Colorblind-friendly palette (Okabe-Ito), used consistently across all
# three visualizations (cause I'm colorblind and bad color choices annoy me).
# A single accent color is used for the ranking chart, and the same
# two edibility colors are used everywhere edible/poisonous appears.
COLOR_RANKING_BARS = "#009E73"  # bluish green
COLOR_EDIBLE = "#0072B2"  # blue
COLOR_POISONOUS = "#D55E00"  # vermillion
HEATMAP_CMAP = "viridis"  # perceptually uniform, colorblind-safe


def get_script_dir() -> str:
    """Return the absolute path of the directory containing this script.

    Used so the dataset is loaded, and output files are saved, relative
    to the script's own location rather than the current working
    directory.

    :return: Absolute path of this script's parent directory.
    :rtype: str
    """
    return os.path.dirname(os.path.abspath(__file__))


def load_data(filename: str = "mushrooms.csv") -> pd.DataFrame:
    """Load the mushroom dataset from a CSV file in the script's folder.

    :param filename: Name of the CSV file to load, expected to live in
        the same directory as this script.
    :type filename: str
    :return: Raw mushroom characteristics DataFrame.
    :rtype: pandas.DataFrame
    :raises FileNotFoundError: If the CSV file cannot be located.
    """
    file_path = os.path.join(get_script_dir(), filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Could not find '{filename}' in '{get_script_dir()}'. "
            "Place the mushroom CSV file alongside visualization.py."
        )

    return pd.read_csv(file_path)

def drop_unmapped_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Drop rows containing a value not present in its column's mapping.
 
    Checks every column that has an entry in :data:`COLUMN_VALUE_MAPS`
    and keeps only rows where that column's raw value is a recognized
    key. A row is dropped if *any* mapped column contains an
    unrecognized code, since such a row can't be fully and correctly
    decoded. Prints the row count before and after, so any data quality
    issues (unexpected codes) are immediately visible.
 
    :param dataframe: Raw mushroom DataFrame with single-letter category
        codes.
    :type dataframe: pandas.DataFrame
    :return: Copy of ``dataframe`` containing only rows whose mapped
        columns are all recognized codes.
    :rtype: pandas.DataFrame
    """
    rows_before = len(dataframe)

    valid_mask = pd.Series(True, index=dataframe.index)
    for column, value_map in COLUMN_VALUE_MAPS.items():
        if column in dataframe.columns:
            valid_mask &= dataframe[column].isin(value_map.keys())

    filtered = dataframe[valid_mask].reset_index(drop=True)
    rows_after = len(filtered)

    print(f"Rows before dropping unmapped values: {rows_before}")
    print(f"Rows after dropping unmapped values: {rows_after}")
    if rows_after < rows_before:
        print(f"Dropped {rows_before - rows_after} row(s) containing an unrecognized code.")

    return filtered

def decode_categorical_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Decode single-letter category codes into full, readable words.
 
    Applies :data:`COLUMN_VALUE_MAPS` to every matching column. Values
    in the mapping are already capitalized (e.g. ``"Almond"``), so no
    further formatting is needed. This should be called after
    :func:`drop_unmapped_rows`, so every remaining value is guaranteed
    to have a corresponding entry in its column's mapping.
 
    :param dataframe: Mushroom DataFrame with single-letter category
        codes, already filtered by :func:`drop_unmapped_rows`.
    :type dataframe: pandas.DataFrame
    :return: Copy of ``dataframe`` with decoded category labels in every
        column present in :data:`COLUMN_VALUE_MAPS`.
    :rtype: pandas.DataFrame
    """
    decoded = dataframe.copy()

    for column, value_map in COLUMN_VALUE_MAPS.items():
        if column in decoded.columns:
            decoded[column] = decoded[column].replace(value_map)

    return decoded

def rename_columns_to_title_case(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to title case with hyphens replaced by spaces.

    :param dataframe: DataFrame with hyphenated, lowercase column names.
    :type dataframe: pandas.DataFrame
    :return: Copy of ``dataframe`` with renamed columns.
    :rtype: pandas.DataFrame
    """
    renamed = dataframe.copy()
    renamed.columns = renamed.columns.str.replace("-", " ").str.title()
    return renamed

def compute_cramers_v(dataframe: pd.DataFrame, feature: str) -> float:
    """Compute bias-corrected Cramer's V between a feature and the target.

    Uses the Bergsma (2013) bias correction, which adjusts for the fact
    that uncorrected Cramer's V is upwardly biased for small samples or
    tables with many categories, so association strength can be fairly
    compared across features with differing numbers of categories.

    :param dataframe: Mushroom DataFrame containing ``feature`` and the
        target column.
    :type dataframe: pandas.DataFrame
    :param feature: Name of the categorical feature column to test.
    :type feature: str
    :return: Bias-corrected Cramer's V, ranging from 0 (no association)
        to 1 (perfect association).
    :rtype: float
    """
    contingency_table = pd.crosstab(dataframe[feature], dataframe[TARGET_COLUMN])
    chi2_stat = chi2_contingency(contingency_table)[0]

    n_obs = contingency_table.to_numpy().sum()
    n_rows, n_cols = contingency_table.shape
    phi2 = chi2_stat / n_obs

    # Bias correction terms.
    phi2_corrected = max(0.0, phi2 - ((n_cols - 1) * (n_rows - 1)) / (n_obs - 1))
    rows_corrected = n_rows - ((n_rows - 1) ** 2) / (n_obs - 1)
    cols_corrected = n_cols - ((n_cols - 1) ** 2) / (n_obs - 1)
    denominator = min(cols_corrected - 1, rows_corrected - 1)

    if denominator <= 0:
        return 0.0

    return float((phi2_corrected / denominator) ** 0.5)


def compute_feature_associations(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Rank every categorical feature by its association with edibility.

    :param dataframe: Mushroom DataFrame containing the target column
        and one or more categorical feature columns.
    :type dataframe: pandas.DataFrame
    :return: DataFrame with ``feature`` and ``cramers_v`` columns,
        sorted by association strength, strongest first.
    :rtype: pandas.DataFrame
    """
    # Loop the column names for generality, rather than hardcoding the feature list
    feature_columns = [col for col in dataframe.columns if col != TARGET_COLUMN]

    # Run Cramer's V computation for every feature
    associations = [
        {"feature": feature, "cramers_v": compute_cramers_v(dataframe, feature)}
        for feature in feature_columns
    ]
    associations_df = pd.DataFrame(associations)
    return associations_df.sort_values("cramers_v", ascending=False).reset_index(drop=True)


def plot_cramers_v_bar_chart(associations_df: pd.DataFrame) -> None:
    """Plot and save a ranked bar chart of feature/edibility associations.
 
    Produces a horizontal bar chart (Seaborn) ranking every feature by
    its bias-corrected Cramer's V with edibility, saved as
    ``cramers_v_association.png`` in the script's directory. A single
    consistent bar color is used throughout, since color is not needed
    to encode a second variable here.
 
    :param associations_df: DataFrame produced by
        :func:`compute_feature_associations`.
    :type associations_df: pandas.DataFrame
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    # Cramer's V is bounded in [0, 1]; displaying it as a percentage
    # (0-100%) reads more intuitively than a raw decimal.
    plot_data = associations_df.copy()
    plot_data["cramers_v_pct"] = plot_data["cramers_v"] * 100

    figure, axes = plt.subplots(figsize=(9, max(4.0, 0.35 * len(plot_data))))
    sns.barplot(
        data=plot_data,
        x="cramers_v_pct",
        y="feature",
        color=COLOR_RANKING_BARS,
        ax=axes,
    )

    axes.set_title("Association Between Mushroom Features and Edibility (Cramer's V)")
    axes.set_xlabel("Bias-Corrected Cramer's V (0% = no association, 100% = perfect association)")
    axes.set_ylabel("Feature")
    # Cramer's V is bounded in [0, 1] (0-100%); keep the full range
    # visible rather than truncating to the tightest range of the
    # observed values.
    axes.set_xlim(0, 100)

    figure.tight_layout()
    output_path = os.path.join(get_script_dir(), "cramers_v_association.png")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

def build_feature_percentage_breakdown(dataframe: pd.DataFrame, feature: str) -> pd.DataFrame:
    """Compute the percentage edible/poisonous split for each category.
 
    :param dataframe: Mushroom DataFrame containing ``feature`` and the
        target column.
    :type dataframe: pandas.DataFrame
    :param feature: Name of the categorical feature column to break
        down.
    :type feature: str
    :return: DataFrame indexed by category, with ``Edible`` and
        ``Poisonous`` columns holding percentages that sum to 100 per
        row.
    :rtype: pandas.DataFrame
    """
    # The class column is already decoded to "Edible"/"Poisonous" by
    # decode_categorical_columns, so no rename is needed here.
    counts = pd.crosstab(dataframe[feature], dataframe[TARGET_COLUMN])
    percentages = counts.div(counts.sum(axis=1), axis=0) * 100
    return percentages[["Edible", "Poisonous"]]

def build_interactive_crosstab_figure(
    dataframe: pd.DataFrame, associations_df: pd.DataFrame
) -> go.Figure:
    """Build the interactive per-feature edibility breakdown figure.

    Produces a Plotly 100%-stacked bar chart with a dropdown menu that
    switches which feature is displayed. Only two trace groups are ever
    visible at once, keeping each view focused on a single feature's
    relationship with edibility. The feature ranked highest in
    ``associations_df`` (i.e. by :func:`compute_feature_associations`)
    is shown by default, tying this chart to the Cramer's V ranking
    chart. Returns the figure object directly (rather than saving it),
    so it can be embedded live in a Dash app via ``dcc.Graph`` as well
    as saved to an HTML file by :func:`plot_interactive_crosstab`.

    :param dataframe: Mushroom DataFrame containing the target column
        and one or more categorical feature columns.
    :type dataframe: pandas.DataFrame
    :param associations_df: DataFrame produced by
        :func:`compute_feature_associations`, used to order dropdown
        options and choose the default feature.
    :type associations_df: pandas.DataFrame
    :return: The interactive Plotly figure.
    :rtype: plotly.graph_objects.Figure
    """
    features = associations_df["feature"].tolist()
    figure = go.Figure()

    for index, feature in enumerate(features):
        breakdown = build_feature_percentage_breakdown(dataframe, feature)
        is_default = index == 0

        figure.add_trace(
            go.Bar(
                x=breakdown.index,
                y=breakdown["Edible"],
                name="Edible",
                marker_color=COLOR_EDIBLE,
                visible=is_default,
                legendgroup="Edible",
            )
        )
        figure.add_trace(
            go.Bar(
                x=breakdown.index,
                y=breakdown["Poisonous"],
                name="Poisonous",
                marker_color=COLOR_POISONOUS,
                visible=is_default,
                legendgroup="Poisonous",
            )
        )

    # Build one dropdown button per feature. Each button toggles on the
    # two traces (Edible, Poisonous) belonging to that feature and off
    # every other feature's traces, and updates the axis title so the
    # selected category is always clear.
    buttons = []
    for index, feature in enumerate(features):
        visibility = [False] * (2 * len(features))
        visibility[2 * index] = True
        visibility[2 * index + 1] = True
        buttons.append(
            {
                "label": feature,
                "method": "update",
                "args": [
                    {"visible": visibility},
                    {
                        "title.text": f"Edibility Breakdown by {feature}",
                        "xaxis": {"title": feature},
                    },
                ],
            }
        )

    figure.update_layout(
        title={
            "text": f"Edibility Breakdown by {features[0]}",
            "x": 0.5,
            "xanchor": "center",
            "y": 0.95,
            "yanchor": "top",
        },
        xaxis_title=features[0],
        yaxis_title="Percentage of Mushrooms (%)",
        yaxis_range=[0, 100],
        barmode="stack",
        legend_title="Edibility",
        # Extra top margin reserves clear space so the dropdown (above
        # the plot area) and the title don't overlap.
        margin={"t": 140},
        updatemenus=[
            {
                "buttons": buttons,
                "direction": "down",
                "x": 0.0,
                "y": 1.25,
                "xanchor": "left",
                "showactive": True,
            }
        ],
    )

    return figure

def plot_interactive_crosstab(dataframe: pd.DataFrame, associations_df: pd.DataFrame) -> None:
    """Build and save the interactive per-feature edibility breakdown.

    Saved as ``edibility_by_feature.html`` in the script's directory.
    See :func:`build_interactive_crosstab_figure` for the figure
    construction details.

    :param dataframe: Mushroom DataFrame containing the target column
        and one or more categorical feature columns.
    :type dataframe: pandas.DataFrame
    :param associations_df: DataFrame produced by
        :func:`compute_feature_associations`, used to order dropdown
        options and choose the default feature.
    :type associations_df: pandas.DataFrame
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    figure = build_interactive_crosstab_figure(dataframe, associations_df)
    output_path = os.path.join(get_script_dir(), "edibility_by_feature.html")
    figure.write_html(output_path, include_plotlyjs="cdn")

def plot_top_feature_heatmap(dataframe: pd.DataFrame, feature: str) -> None:
    """Plot and save a heatmap of raw edible/poisonous counts for a feature.

    Produces a Seaborn heatmap of category-by-class counts for a single
    feature (typically the top-ranked one from
    :func:`compute_feature_associations`), giving concrete counts to
    complement the percentage view in the interactive crosstab chart.
    Saved as ``top_feature_class_heatmap.png`` in the script's
    directory.

    :param dataframe: Mushroom DataFrame containing ``feature`` and the
        target column.
    :type dataframe: pandas.DataFrame
    :param feature: Name of the categorical feature column to display.
    :type feature: str
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    # The class column is already decoded to "Edible"/"Poisonous" by
    # decode_categorical_columns, so no rename is needed here.
    counts = pd.crosstab(dataframe[feature], dataframe[TARGET_COLUMN])
    counts = counts[["Edible", "Poisonous"]]

    figure, axes = plt.subplots(figsize=(6, max(4.0, 0.5 * len(counts))))
    sns.heatmap(
        counts,
        annot=True,
        fmt="d",
        cmap=HEATMAP_CMAP,
        cbar_kws={"label": "Number of Mushrooms"},
        ax=axes,
    )

    axes.set_title(f"Mushroom Counts by {feature} and Edibility")
    axes.set_xlabel("Edibility")
    axes.set_ylabel(feature)

    figure.tight_layout()
    output_path = os.path.join(get_script_dir(), "top_feature_class_heatmap.png")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

def one_hot_encode_features(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """One-hot encode all categorical mushroom features.

    :param dataframe: Cleaned, decoded mushroom DataFrame containing the
        target column and one or more categorical feature columns.
    :type dataframe: pandas.DataFrame
    :return: A tuple of the one-hot encoded feature matrix, the target
        label series, and the list of original (pre-encoding) feature
        column names.
    :rtype: tuple[pandas.DataFrame, pandas.Series, list[str]]
    """
    feature_columns = [col for col in dataframe.columns if col != TARGET_COLUMN]
    features = pd.get_dummies(dataframe[feature_columns])
    target = dataframe[TARGET_COLUMN]
    return features, target, feature_columns

def aggregate_feature_importances(
    model: RandomForestClassifier, features: pd.DataFrame, original_feature_columns: list[str]
) -> pd.DataFrame:
    """Aggregate one-hot column importances back to their original feature.

    One-hot encoding splits each original categorical feature (e.g.
    ``odor``) into several binary columns (e.g. ``odor_Foul``,
    ``odor_Almond``). ``RandomForestClassifier.feature_importances_``
    reports importance per encoded column, which isn't directly
    readable; this sums those per-column importances back up to the
    original feature they came from, so results are comparable to the
    Cramer's V association ranking computed earlier.

    :param model: A fitted Random Forest classifier.
    :type model: sklearn.ensemble.RandomForestClassifier
    :param features: The one-hot encoded feature matrix the model was
        trained on, as returned by :func:`one_hot_encode_features`.
    :type features: pandas.DataFrame
    :param original_feature_columns: Names of the original (pre-encoding)
        feature columns, as returned by :func:`one_hot_encode_features`.
    :type original_feature_columns: list[str]
    :return: DataFrame with ``feature`` and ``importance`` columns,
        sorted by importance, strongest first.
    :rtype: pandas.DataFrame
    """
    importance_by_column = pd.Series(model.feature_importances_, index=features.columns)

    aggregated_importances = []
    for original_feature in original_feature_columns:
        prefix = f"{original_feature}_"
        matching_columns = [col for col in features.columns if col.startswith(prefix)]
        aggregated_importances.append(
            {
                "feature": original_feature,
                "importance": importance_by_column[matching_columns].sum(),
            }
        )

    importance_df = pd.DataFrame(aggregated_importances)
    return importance_df.sort_values("importance", ascending=False).reset_index(drop=True)

def plot_feature_importance(importance_df: pd.DataFrame) -> None:
    """Plot and save a ranked bar chart of Random Forest feature importance.
 
    Produces a horizontal bar chart (Seaborn) ranking every original
    feature by its aggregated importance in the trained Random Forest,
    saved as ``random_forest_feature_importance.png`` in the script's
    directory. Uses the same bar color as the Cramer's V association
    chart, since both are single-variable ranking charts and this keeps
    the two directly visually comparable.
 
    :param importance_df: DataFrame produced by
        :func:`aggregate_feature_importances`.
    :type importance_df: pandas.DataFrame
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    # Importances sum to 1 across all features; displaying as a
    # percentage of total importance reads more intuitively.
    plot_data = importance_df.copy()
    plot_data["importance_pct"] = plot_data["importance"] * 100

    figure, axes = plt.subplots(figsize=(9, max(4.0, 0.35 * len(plot_data))))
    sns.barplot(
        data=plot_data,
        x="importance_pct",
        y="feature",
        color=COLOR_RANKING_BARS,
        ax=axes,
    )

    axes.set_title("Random Forest Feature Importance for Predicting Edibility")
    axes.set_xlabel("Aggregated Feature Importance (% of total, summed across one-hot columns)")
    axes.set_ylabel("Feature")
    axes.set_xlim(0, plot_data["importance_pct"].max() * 1.1)

    figure.tight_layout()
    output_path = os.path.join(get_script_dir(), "random_forest_feature_importance.png")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

def plot_confusion_matrix_heatmap(
    y_test: pd.Series, predictions: pd.Series, class_labels: list[str]
) -> None:
    """Plot and save a heatmap of the test-set confusion matrix.

    Produces a Seaborn heatmap of actual vs. predicted class counts on
    the held-out test set, saved as ``confusion_matrix.png`` in the
    script's directory.

    :param y_test: True class labels for the test set.
    :type y_test: pandas.Series
    :param predictions: Predicted class labels for the test set, as
        returned by the model's ``.predict()``.
    :type predictions: pandas.Series
    :param class_labels: Ordered class labels to use for both axes
        (typically the model's ``.classes_``).
    :type class_labels: list[str]
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    matrix = confusion_matrix(y_test, predictions, labels=class_labels)

    figure, axes = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap=HEATMAP_CMAP,
        xticklabels=class_labels,
        yticklabels=class_labels,
        cbar_kws={"label": "Number of Mushrooms"},
        ax=axes,
    )

    axes.set_title("Random Forest Test Set Confusion Matrix")
    axes.set_xlabel("Predicted Class")
    axes.set_ylabel("Actual Class")

    figure.tight_layout()
    output_path = os.path.join(get_script_dir(), "confusion_matrix.png")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

def plot_classification_metrics_bar_chart(y_test: pd.Series, predictions: pd.Series) -> None:
    """Plot and save a grouped bar chart of per-class precision/recall/F1.
 
    Produces a Seaborn grouped bar chart showing precision, recall, and
    F1-score for each class, saved as
    ``classification_metrics_by_class.png`` in the script's directory.
    This is a standalone, independent chart from
    :func:`plot_confusion_matrix_heatmap` - remove the call to either
    one without affecting the other if one doesn't earn its place.
 
    :param y_test: True class labels for the test set.
    :type y_test: pandas.Series
    :param predictions: Predicted class labels for the test set, as
        returned by the model's ``.predict()``.
    :type predictions: pandas.Series
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    report = classification_report(y_test, predictions, output_dict=True)

    # Keep only the per-class rows (drop "accuracy", "macro avg", etc.),
    # and only the three rate-based metrics (drop "support", a raw count
    # that's on a totally different scale from the 0-1 rate metrics).
    class_labels = sorted(set(y_test))
    metrics_df = (
        pd.DataFrame(report)[class_labels]
        .loc[["precision", "recall", "f1-score"]]
        .reset_index()
        .rename(columns={"index": "metric"})
        .melt(id_vars="metric", var_name="class", value_name="score")
    )
    # Display as a percentage (0-100%) rather than a raw 0-1 decimal.
    metrics_df["score"] = metrics_df["score"] * 100

    figure, axes = plt.subplots(figsize=(8, 5))
    sns.barplot(
        data=metrics_df,
        x="metric",
        y="score",
        hue="class",
        palette={"Edible": COLOR_EDIBLE, "Poisonous": COLOR_POISONOUS},
        ax=axes,
    )

    axes.set_title("Random Forest Precision, Recall, and F1-Score by Class")
    axes.set_xlabel("Metric")
    axes.set_ylabel("Score (%)")
    axes.set_ylim(0, 100)
    axes.legend(title="Edibility")

    figure.tight_layout()
    output_path = os.path.join(get_script_dir(), "classification_metrics_by_class.png")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

def plot_precision_recall_curve(
    model: RandomForestClassifier, x_test: pd.DataFrame, y_test: pd.Series
) -> None:
    """Plot and save a precision-recall curve for the Poisonous class.
 
    Traces precision vs. recall across every possible classification
    threshold for the Poisonous class specifically (rather than Edible),
    since a missed poisonous mushroom (a false negative) is the costlier
    mistake here. Saved as ``precision_recall_curve.png`` in the
    script's directory. This is a standalone, independent chart from
    :func:`plot_classification_metrics_bar_chart` and
    :func:`plot_confusion_matrix_heatmap` - remove the call to any one
    of them without affecting the others if one doesn't earn its place.
 
    :param model: A fitted Random Forest classifier.
    :type model: sklearn.ensemble.RandomForestClassifier
    :param x_test: One-hot encoded test-set feature matrix.
    :type x_test: pandas.DataFrame
    :param y_test: True class labels for the test set.
    :type y_test: pandas.Series
    :return: None. The plot is saved to disk as a side effect.
    :rtype: None
    """
    positive_class = "Poisonous"
    class_index = list(model.classes_).index(positive_class)
    positive_class_probabilities = model.predict_proba(x_test)[:, class_index]

    precision, recall, _ = precision_recall_curve(
        y_test, positive_class_probabilities, pos_label=positive_class
    )
    average_precision = average_precision_score(
        y_test, positive_class_probabilities, pos_label=positive_class
    )

    # Display precision, recall, and average precision as percentages
    # (0-100%) rather than raw 0-1 decimals.
    precision_pct = precision * 100
    recall_pct = recall * 100
    average_precision_pct = average_precision * 100

    figure, axes = plt.subplots(figsize=(7, 6))
    axes.plot(
        recall_pct,
        precision_pct,
        color=COLOR_POISONOUS,
        linewidth=2,
        label=f"Poisonous (AP = {average_precision_pct:.1f}%)",
    )

    axes.set_title("Precision-Recall Curve for Detecting Poisonous Mushrooms")
    axes.set_xlabel("Recall (% of Actual Poisonous Mushrooms Caught)")
    axes.set_ylabel("Precision (% of Poisonous Calls That Were Correct)")
    axes.set_xlim(0, 100)
    axes.set_ylim(0, 105)
    axes.legend(loc="lower left")

    figure.tight_layout()
    output_path = os.path.join(get_script_dir(), "precision_recall_curve.png")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

def load_and_clean_data() -> pd.DataFrame:
    """Load, filter, decode, and rename the mushroom dataset.
 
    Runs the full data preparation pipeline: load the raw CSV, drop any
    rows containing an unrecognized category code, decode remaining
    codes into readable words, and rename columns to title case with
    hyphens replaced by spaces.
 
    :return: Fully cleaned mushroom DataFrame, ready for analysis.
    :rtype: pandas.DataFrame
    """
    dataframe = load_data()
    # Just in case the website was wrong about the mappings
    dataframe = drop_unmapped_rows(dataframe)
    dataframe = decode_categorical_columns(dataframe)
    # Clean up column names for nicer titles in the plots
    dataframe = rename_columns_to_title_case(dataframe)
    return dataframe

def create_initial_analysis(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Rank feature associations and generate the exploratory visualizations.
 
    Computes each feature's association with edibility, prints the
    ranking, and produces all three exploratory charts: the Cramer's V
    ranking bar chart, the interactive per-feature crosstab, and the
    top-ranked feature's count heatmap.
 
    :param dataframe: Cleaned mushroom DataFrame, as returned by
        :func:`load_and_clean_data`.
    :type dataframe: pandas.DataFrame
    :return: DataFrame of feature associations, as returned by
        :func:`compute_feature_associations`.
    :rtype: pandas.DataFrame
    """
    # Which characteristics are most strongly associated with edibility?
    associations_df = compute_feature_associations(dataframe)
    print("Feature associations with edibility (bias-corrected Cramer's V):")
    print(associations_df.to_string(index=False))

    # Generate the three visualizations
    plot_cramers_v_bar_chart(associations_df)
    plot_interactive_crosstab(dataframe, associations_df)

    top_feature = associations_df.iloc[0]["feature"]
    print(f"Top-ranked feature (used as default/heatmap focus): {top_feature}\n")
    plot_top_feature_heatmap(dataframe, top_feature)

    # Return the associations DataFrame for potential further use
    return associations_df

def train_and_evaluate_model(dataframe: pd.DataFrame) -> None:
    """Train and evaluate a Random Forest classifier on mushroom features.

    One-hot encodes the categorical features, splits the data into an
    80/20 train/test split (stratified by class, with a fixed random
    state for reproducibility), fits a Random Forest classifier, and
    reports test-set accuracy plus a 5-fold cross-validation accuracy
    to check the single split's result isn't a lucky fluke.

    :param dataframe: Cleaned, decoded mushroom DataFrame containing the
        target column and one or more categorical feature columns.
    :type dataframe: pandas.DataFrame
    :return: None. Results are printed to stdout.
    :rtype: None
    """
    print("\nOne-hot encoding categorical features and splitting into train/test sets...")
    features, target, original_feature_columns = one_hot_encode_features(dataframe)

    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, stratify=target, random_state=42
    )
    print(f"Training set size: {len(x_train)} mushrooms")
    print("\nRunning Random Forest classifier on training set...")
    model = RandomForestClassifier(random_state=42)
    model.fit(x_train, y_train)

    print("\nEvaluating model on test set...")
    predictions = model.predict(x_test)
    test_accuracy = accuracy_score(y_test, predictions)
    correct_predictions = int((predictions == y_test).sum())
    total_predictions = len(y_test)

    print(f"Test set accuracy: {test_accuracy:.4f}")
    print(
        f"Correctly predicted {correct_predictions} of {total_predictions} "
        f"test mushrooms ({test_accuracy * 100:.2f}% accuracy)."
    )
    print("Classification report:")
    print(classification_report(y_test, predictions))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions))

    cross_val_scores = cross_val_score(
        model, features, target, cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    )
    print(
        f"\n5-fold cross-validation accuracy: {cross_val_scores.mean():.4f} "
        f"(+/- {cross_val_scores.std():.4f})"
    )

    print("\nGenerating feature importance and evaluation visualizations...")
    importance_df = aggregate_feature_importances(model, features, original_feature_columns)
    plot_feature_importance(importance_df)
    plot_confusion_matrix_heatmap(y_test, predictions, model.classes_)

    plot_classification_metrics_bar_chart(y_test, predictions)
    plot_precision_recall_curve(model, x_test, y_test)
    print("All visualizations saved to the script's directory.")

def main() -> None:
    """Run the full exploratory visualization pipeline.

    :return: None.
    :rtype: None
    """

    dataframe = load_and_clean_data()
    create_initial_analysis(dataframe)
    train_and_evaluate_model(dataframe)

if __name__ == "__main__":
    main()
