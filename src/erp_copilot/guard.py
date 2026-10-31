import re

REFUSAL = (
    "I'm a read-only assistant, so I can't create, change, or delete any records. "
    "I can look up customers, invoices, and sales totals if you'd like."
)

_WRITE_VERBS = re.compile(
    r"\b(delete|remove|drop|truncate|update|modify|edit|insert|cancel|overwrite|erase|destroy)\b",
    re.IGNORECASE,
)
_CREATE_RECORD = re.compile(
    r"\b(create|add|make|register)\s+(me\s+)?(a\s+|an\s+|the\s+)?(new\s+)?"
    r"(invoice|customer|order|product|record|entry)\b",
    re.IGNORECASE,
)
_CURRENCY = re.compile(r"[$₹€£]\s?")


def is_write_request(text: str) -> bool:
    """True if the text looks like a request to change data."""
    return bool(_WRITE_VERBS.search(text) or _CREATE_RECORD.search(text))


def clean_answer(text: str) -> str:
    """The data has no currency, so strip currency symbols the model invents."""
    return _CURRENCY.sub("", text)