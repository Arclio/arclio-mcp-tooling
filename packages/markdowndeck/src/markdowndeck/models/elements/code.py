"""Code block element models."""

from dataclasses import dataclass

from markdowndeck.models.elements.base import Element


@dataclass
class CodeElement(Element):
    """Code block element."""

    code: str = ""
    language: str = "text"

    def count_lines(self) -> int:
        """
        Count the number of lines in the code block.

        Returns:
            Number of lines in the code
        """
        if not self.code:
            return 0
        return self.code.count("\n") + 1

    def get_display_language(self) -> str:
        """
        Get a display-friendly language name.

        Returns:
            Display language name
        """
        if self.language == "text" or not self.language:
            return "Text"

        # Map common language ids to display names
        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "html": "HTML",
            "css": "CSS",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "csharp": "C#",
            "go": "Go",
            "rust": "Rust",
            "ruby": "Ruby",
            "php": "PHP",
            "shell": "Shell",
            "bash": "Bash",
            "sql": "SQL",
            "json": "JSON",
            "xml": "XML",
            "yaml": "YAML",
            "md": "Markdown",
        }

        # Return mapped name or capitalize the language
        return language_map.get(self.language.lower(), self.language.capitalize())
