"""
Model loading and inference helper for the "Will You Get In?" page.

This module loads the fine-tuned admissions classifier exactly once,
at first use (not on every request, and not by retraining), and
exposes a single :func:`predict_applicant` function that reuses the
*exact* unified-text-building and inference code from
:mod:`train_model` -- the same code path proven out during training
and in ``inference.py`` -- so the web form can never silently drift
from the format the model was actually trained on.

**Module contents:**

+-----------------------------+------------------------------------------+
| Name                        | Description                               |
+==============================+============================================+
| :func:`model_available`     | Whether the saved model loaded successfully|
+-----------------------------+------------------------------------------+
| :func:`predict_applicant`   | Run inference on one raw applicant dict   |
+-----------------------------+------------------------------------------+

**Dependencies:**

* :mod:`pandas` -- third-party, used to wrap the raw applicant dict as
  a :class:`pandas.Series` for :func:`train_model.build_unified_text`.
* :mod:`train_model` -- the top-level module (sibling to the ``src``
  package) that defines ``build_unified_text``, ``load_saved_model``,
  ``predict_single``, and ``DEVICE``.

.. note::
    The model is loaded lazily on first call (not at import time), and
    cached at module level afterward, so importing this module (e.g.
    during test collection) never triggers a model load or requires
    ``saved_model/`` to exist. If loading fails (e.g. the model hasn't
    been trained/saved yet), the error is cached and re-raised on
    every subsequent call via :func:`predict_applicant`, rather than
    retried on every request.
"""

import pandas as pd
import train_model as tm


class _ModelCache:  # pylint: disable=too-few-public-methods
    """Lazily-loaded, process-wide cache for the saved model artifacts.

    Using a small class (rather than bare module-level globals) avoids
    needing a ``global`` statement in :func:`_ensure_loaded` to update
    these values from within a function.
    """
    model = None
    tokenizer = None
    metadata = None
    load_error = None


def _ensure_loaded():
    """Load the saved model/tokenizer/metadata once, caching the result."""
    if _ModelCache.model is not None or _ModelCache.load_error is not None:
        return

    try:
        _ModelCache.model, _ModelCache.tokenizer, _ModelCache.metadata = (
            tm.load_saved_model()
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Broad catch is intentional here: this is a startup/availability
        # check for an external artifact (saved_model/ on disk), not a
        # request-handling path, and any failure (missing directory,
        # corrupted weights, etc.) should be reported the same way --
        # "model unavailable" -- rather than crash the app.
        _ModelCache.load_error = str(exc)


def model_available() -> bool:
    """Check whether the saved model is loaded and ready for inference.

    :return: ``True`` if the model loaded successfully, ``False`` if
        loading failed (e.g. ``saved_model/`` doesn't exist yet).
    :rtype: bool
    """
    _ensure_loaded()
    return _ModelCache.model is not None


def predict_applicant(applicant: dict) -> dict:
    """Run the fine-tuned model on one applicant's raw field values.

    :param applicant: Raw field values keyed exactly as
        :func:`train_model.build_unified_text` expects (e.g.
        ``"llm-generated-program"``, ``"llm-generated-university"``,
        ``"comments"``, ``"Degree"``, ``"US/International"``,
        ``"GPA"``, ``"GRE"``, ``"GRE V"``, ``"GRE AW"``).
    :type applicant: dict
    :return: A dict with keys ``"label"`` (``"Accepted"``/``"Rejected"``),
        ``"confidence"`` (probability of the predicted class), and
        ``"p_accepted"`` (probability specifically of "Accepted").
    :rtype: dict

    :raises RuntimeError: If the saved model could not be loaded (see
        :func:`model_available` to check this ahead of time and avoid
        the exception entirely).
    """
    _ensure_loaded()
    if _ModelCache.model is None:
        raise RuntimeError(f"Model unavailable: {_ModelCache.load_error}")

    text = tm.build_unified_text(pd.Series(applicant))
    label, confidence, p_accepted = tm.predict_single(
        _ModelCache.model, _ModelCache.tokenizer, text, _ModelCache.metadata,
        tm.DEVICE
    )
    return {"label": label, "confidence": confidence, "p_accepted": p_accepted}
