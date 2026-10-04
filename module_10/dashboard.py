"""Single-page Dash dashboard for the mushroom edibility analysis.

Displays every visualization produced by ``visualization.py``: the
three exploratory charts (Cramer's V ranking, interactive per-feature
crosstab, top-feature heatmap) and the four Random Forest result
charts (feature importance, confusion matrix, classification metrics,
precision-recall curve).

Run ``python visualization.py`` first to generate the PNG/HTML assets
this dashboard reads, then run this file::

    python dashboard.py
"""

import base64
import os

from dash import Dash, dcc, html

from visualization import (
    build_interactive_crosstab_figure,
    compute_feature_associations,
    get_script_dir,
    load_and_clean_data,
)

RESEARCH_QUESTION = "Can We Determine Whether a Mushroom Is Edible Based on Its Features?"

# Matches visualization.py's ranking bar color, used here as an accent
# for section headings to keep the dashboard to chart consistency.
ACCENT_COLOR = "#009E73"

# Each entry pairs a saved PNG filename with a short chart label shown
# above it. Grouped into the same two stages as the written analysis:
# exploratory association analysis, then Random Forest model results.
EXPLORATORY_CHARTS = [
    ("cramers_v_association.png", "Feature Association Ranking (Cramer's V)"),
    ("top_feature_class_heatmap.png", "Top Feature Count Heatmap"),
]
MODEL_RESULT_CHARTS = [
    ("random_forest_feature_importance.png", "Random Forest Feature Importance"),
    ("confusion_matrix.png", "Confusion Matrix"),
    ("classification_metrics_by_class.png", "Precision, Recall, and F1-Score by Class"),
    ("precision_recall_curve.png", "Precision-Recall Curve (Poisonous)"),
]


def encode_image_as_data_uri(filename: str) -> str:
    """Read a PNG from the script's directory and encode it as a data URI.

    Embedding images as base64 data URIs (rather than referencing a
    file path) means the dashboard displays correctly regardless of
    the working directory it's launched from.

    :param filename: Name of the PNG file, expected to live in the same
        directory as this script.
    :type filename: str
    :return: A ``data:image/png;base64,...`` URI string usable directly
        as an ``html.Img`` ``src``.
    :rtype: str
    """
    file_path = os.path.join(get_script_dir(), filename)
    with open(file_path, "rb") as image_file:
        encoded_bytes = base64.b64encode(image_file.read()).decode("ascii")
    return f"data:image/png;base64,{encoded_bytes}"


def build_chart_card(filename: str, label: str) -> html.Div:
    """Build a labeled image card for one saved PNG chart.

    :param filename: Name of the PNG file to embed.
    :type filename: str
    :param label: Short label displayed above the image.
    :type label: str
    :return: A Dash HTML component containing the label and image.
    :rtype: dash.html.Div
    """
    return html.Div(
        [
            html.H4(label, style={"textAlign": "center", "marginBottom": "8px"}),
            html.Img(
                src=encode_image_as_data_uri(filename),
                style={"width": "100%", "borderRadius": "6px"},
            ),
        ],
        style={
            "flex": "1 1 420px",
            "maxWidth": "480px",
            "padding": "12px",
            "backgroundColor": "#ffffff",
            "borderRadius": "8px",
            "boxShadow": "0 1px 4px rgba(0, 0, 0, 0.12)",
        },
    )


def build_section(title: str, chart_specs: list[tuple[str, str]]) -> html.Div:
    """Build a titled section containing a row of chart cards.

    :param title: Section heading.
    :type title: str
    :param chart_specs: List of (filename, label) pairs for
        :func:`build_chart_card`.
    :type chart_specs: list[tuple[str, str]]
    :return: A Dash HTML component containing the section heading and
        chart cards.
    :rtype: dash.html.Div
    """
    return html.Div(
        [
            html.H2(
                title,
                style={"borderBottom": f"3px solid {ACCENT_COLOR}", "paddingBottom": "6px"},
            ),
            html.Div(
                [build_chart_card(filename, label) for filename, label in chart_specs],
                style={"display": "flex", "flexWrap": "wrap", "gap": "16px"},
            ),
        ],
        style={"marginBottom": "32px"},
    )


def build_app() -> Dash:
    """Assemble the single-page Dash application.

    :return: The configured Dash app, ready to run.
    :rtype: dash.Dash
    """
    dataframe = load_and_clean_data()
    associations_df = compute_feature_associations(dataframe)
    interactive_figure = build_interactive_crosstab_figure(dataframe, associations_df)

    dash_app = Dash(__name__)
    dash_app.title = "Mushroom Edibility Dashboard"

    dash_app.layout = html.Div(
        [
            html.H1(RESEARCH_QUESTION, style={"textAlign": "center"}),
            html.P(
                "Odor alone is an almost perfectly reliable indicator of edibility in this "
                "dataset, and a Random Forest trained on all features catches the large "
                "majority of poisonous mushrooms in testing. This analysis is "
                "exploratory, and no model here should be trusted as a real foraging guide.",
                style={
                    "textAlign": "center",
                    "maxWidth": "800px",
                    "margin": "0 auto 32px auto",
                    "color": "#333333",
                },
            ),
            build_section("Exploratory Analysis", EXPLORATORY_CHARTS),
            html.Div(
                [
                    html.H2(
                        "Interactive Edibility Breakdown by Feature",
                        style={
                            "borderBottom": f"3px solid {ACCENT_COLOR}",
                            "paddingBottom": "6px",
                        },
                    ),
                    dcc.Graph(figure=interactive_figure),
                ],
                style={"marginBottom": "32px"},
            ),
            build_section("Random Forest Model Results", MODEL_RESULT_CHARTS),
        ],
        style={
            "fontFamily": "Helvetica, Arial, sans-serif",
            "backgroundColor": "#f4f6f8",
            "padding": "24px 40px",
        },
    )

    return dash_app


app = build_app()
server = app.server

if __name__ == "__main__":
    app.run(debug=False)
