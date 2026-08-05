"""The case taxonomy — practice area -> matter type.

The ten practice areas are the categories in the agent prompt's Step 1 and
live in `intake_fields.CATEGORIES`, next to the fields each one collects. This
module holds the second level: the matter type (`case_subcategory`) within
each area, which the dashboard filters on and the Gemini classifier fills from
the transcript.

Every matter type here is drawn from a distinction the prompt itself draws —
the triggering events it lists for securities fraud, the conduct it names for
a derivative claim, the deal shapes it names for a transaction. Nothing is
invented beyond what the agent is actually told to ask about, because the
classifier can only reliably pick a value the call contains the questions to
distinguish.

Labels are the source of truth; the stored value for each is derived from the
label by `slugify`, so a display label and a stored value can never drift.

Kept dependency-free apart from `intake_fields` so `validators` can import it
without a cycle — `validators` and `db` import from here, never the reverse.
"""
import re

from .intake_fields import CATEGORIES, CATEGORY_LABELS

# Dropped when slugifying so a human label and a stored value collapse to the
# same thing: "Hidden & Junk Fees" and "hidden_junk_fees" both become
# "hidden_junk_fees".
_SLUG_STOPWORDS = {"and", "or", "of", "the", "a", "an"}


def slugify(value: str) -> str:
    """Collapse a label to snake_case, dropping filler words and punctuation:
    "Accounting Fraud (FCPA)" -> "accounting_fraud_fcpa"."""
    tokens = re.split(r"[^a-z0-9]+", value.lower())
    kept = [t for t in tokens if t and t not in _SLUG_STOPWORDS]
    return "_".join(kept)


# category -> matter type labels, in the order the prompt lists them.
_MATTER_TYPES: dict[str, list[str]] = {
    "securities_fraud": [
        "False or Misleading Statements",
        "Financial Restatement",
        "Stock Drop After Disclosure",
        "SEC Investigation",
        "Short Seller Report",
        "Bankruptcy",
        "Offering or IPO Disclosures",
    ],
    "shareholder_derivative": [
        "Breach of Fiduciary Duty",
        "Corporate Waste",
        "Self Dealing",
        "Insider Trading",
        "Excessive Executive Compensation",
        "Board Oversight Failure",
    ],
    "merger_transaction": [
        "Merger",
        "Buyout",
        "Take Private",
        "SPAC",
        "Tender Offer",
        "Appraisal Rights",
    ],
    "whistleblower_sec": [
        "Securities Fraud",
        "Accounting Fraud",
        "FCPA Violations",
        "Market Manipulation",
    ],
    "whistleblower_qui_tam": [
        "Medicare or Medicaid Fraud",
        "Defense Contracting Fraud",
        "Grant Fraud",
        "Customs Fraud",
    ],
    "whistleblower_retaliation": [
        "Termination",
        "Demotion",
        "Suspension",
        "Blacklisting",
        "Other Adverse Action",
    ],
    "consumer_class": [
        "False Advertising",
        "Mislabeled Product",
        "Hidden or Junk Fees",
        "Auto Renewal or Subscription",
        "Defective Product",
        "Price Fixing",
    ],
    "data_privacy_class": [
        "Data Breach",
        "Unauthorized Sharing or Sale",
        "Biometric Privacy",
        "Session Recording or Tracking Pixels",
        "Call or Text Practices",
    ],
    "employment_class": [
        "Unpaid Wages",
        "Unpaid Overtime",
        "Off the Clock Work",
        "Missed Meal or Rest Breaks",
        "Misclassification",
        "Unreimbursed Expenses",
    ],
    # "other" is what didn't fit an area, so it has no matter types by
    # definition — the detail goes in additional_details instead.
}

# category -> [(slug, label)], derived once at import.
MATTER_TYPES: dict[str, list[tuple[str, str]]] = {
    category: [(slugify(label), label) for label in labels]
    for category, labels in _MATTER_TYPES.items()
}

# Flat slug -> label, for display where the category isn't handy. A slug used
# by two areas ("securities_fraud" is both a category and a whistleblower
# matter type) maps to the same words either way, so the collision is safe.
SUBCATEGORY_LABELS: dict[str, str] = {
    slug: label for types in MATTER_TYPES.values() for slug, label in types
}


def subcategory_choices(category: str | None) -> list[tuple[str, str]]:
    """(slug, label) matter-type options within a practice area. Empty for
    "other" and for anything unrecognized."""
    return MATTER_TYPES.get(category or "", [])


def category_choices() -> list[tuple[str, str]]:
    """(slug, label) for the ten practice areas, in the prompt's order."""
    return list(CATEGORIES)


__all__ = [
    "CATEGORIES",
    "CATEGORY_LABELS",
    "MATTER_TYPES",
    "SUBCATEGORY_LABELS",
    "category_choices",
    "slugify",
    "subcategory_choices",
]
