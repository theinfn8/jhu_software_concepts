// Client-side validation for the "Will You Get In?" form.
//
// GPA, GRE, GRE V, and GRE AW are optional -- a blank field is always
// valid (it means "not reported", handled server-side as such). If a
// value IS entered, it must be a plain number (no letters, no stray
// punctuation) or the form is blocked from submitting and an inline
// error is shown next to the offending field.
//
// This is a UX convenience layer only. The server (see routes.py's
// _parse_optional_float) already handles blank/invalid numeric input
// gracefully on its own, so this script intentionally fails "open":
// if anything here doesn't run (JS disabled, script error), the form
// still submits and the server-side handling still applies.

const NUMERIC_FIELD_IDS = ["gpa", "gre", "gre_v", "gre_aw"];

// Fields that can genuinely be left empty by the user. "degree" and
// "citizenship" are <select> dropdowns, which always carry a value
// (a default option), so they can't meaningfully be "blank" and are
// excluded from this check.
const ALL_FIELD_IDS = ["program", "university", "gpa", "gre", "gre_v", "gre_aw", "comments"];

function isFormEntirelyBlank() {
    return ALL_FIELD_IDS.every((fieldId) => {
        const input = document.getElementById(fieldId);
        return !input || input.value.trim() === "";
    });
}

function isValidOptionalNumber(rawValue) {
    const trimmed = rawValue.trim();
    if (trimmed === "") {
        return true; // blank is fine -- "not reported"
    }
    // Number("") is 0, so blank is checked separately above.
    // Number.isFinite (not just !isNaN) also rejects "Infinity" /
    // "-Infinity", which Number() parses as real (non-NaN) values but
    // which are meaningless as a GPA/GRE score. This requires the
    // ENTIRE string to be numeric (unlike parseFloat, which would
    // happily accept "3.5abc" as 3.5).
    return Number.isFinite(Number(trimmed));
}

function showFieldError(input, errorEl, message) {
    input.classList.add("input-invalid");
    if (errorEl) {
        errorEl.textContent = message;
    }
}

function clearFieldError(input, errorEl) {
    input.classList.remove("input-invalid");
    if (errorEl) {
        errorEl.textContent = "";
    }
}

function showFormError(message) {
    const formErrorEl = document.getElementById("form-error");
    if (formErrorEl) {
        formErrorEl.textContent = message;
    }
}

function clearFormError() {
    showFormError("");
}

function validatePredictForm(event) {
    let firstInvalidInput = null;

    if (isFormEntirelyBlank()) {
        showFormError("Please fill in at least one field before submitting.");
        event.preventDefault();
        const programInput = document.getElementById("program");
        if (programInput) {
            programInput.focus();
        }
        return;
    }
    clearFormError();

    NUMERIC_FIELD_IDS.forEach((fieldId) => {
        const input = document.getElementById(fieldId);
        if (!input) {
            return;
        }
        const errorEl = document.getElementById(fieldId + "-error");

        if (isValidOptionalNumber(input.value)) {
            clearFieldError(input, errorEl);
        } else {
            showFieldError(input, errorEl, "Please enter a number, or leave this field blank.");
            if (!firstInvalidInput) {
                firstInvalidInput = input;
            }
        }
    });

    if (firstInvalidInput) {
        event.preventDefault();
        firstInvalidInput.focus();
    }
}

function initPredictFormValidation() {
    const form = document.querySelector(".predict-form");
    if (!form) {
        return;
    }

    form.addEventListener("submit", validatePredictForm);

    ALL_FIELD_IDS.forEach((fieldId) => {
        const input = document.getElementById(fieldId);
        if (!input) {
            return;
        }
        input.addEventListener("input", () => {
            if (!isFormEntirelyBlank()) {
                clearFormError();
            }
        });
    });

    // Clear a field's error as soon as the user starts fixing it,
    // rather than waiting for the next submit attempt.
    NUMERIC_FIELD_IDS.forEach((fieldId) => {
        const input = document.getElementById(fieldId);
        if (!input) {
            return;
        }
        const errorEl = document.getElementById(fieldId + "-error");
        input.addEventListener("input", () => {
            if (isValidOptionalNumber(input.value)) {
                clearFieldError(input, errorEl);
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", initPredictFormValidation);
