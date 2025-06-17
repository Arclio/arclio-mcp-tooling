"""Custom exception types for the MarkdownDeck parser."""


class MarkdownDeckParserError(Exception):
    """Base exception for all parser-related errors."""

    pass


class GrammarError(MarkdownDeckParserError):
    """
    Raised for violations of MarkdownDeck's Grammar V2.0.

    This error indicates that the source markdown does not follow the strict
    structural rules required for parsing, such as incorrect nesting of
    fenced blocks or content outside of required containers.
    """

    pass
