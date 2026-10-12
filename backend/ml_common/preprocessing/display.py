"""Turn model feature tokens back into words people can read.

The text cleaner replaces every URL with ``__url__`` and every number with
``__num__`` so the model learns that *a* link or number was present, not a
specific one. Those placeholders are feature names, not words, so anything
that shows a token to a person (explanations, Copilot answers, UI chips)
goes through :func:`display_token` first. Exported data (JSON/CSV reports)
keeps the raw feature names on purpose.
"""

_PLACEHOLDER_WORDS = {"__url__": "link", "__num__": "number"}


def display_token(token: str) -> str:
    for placeholder, word in _PLACEHOLDER_WORDS.items():
        token = token.replace(placeholder, word)
    return token
