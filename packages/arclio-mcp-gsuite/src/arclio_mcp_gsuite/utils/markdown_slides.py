"""
Utilities for converting markdown to Google Slides presentations.
Provides advanced markdown parsing and formatting for slide creation.
"""

import logging
import re
from typing import Any

# Third-party dependencies for proper markdown parsing
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MarkdownSlidesConverter:
    """
    Utility class for converting markdown content to Google Slides.
    Handles parsing, element extraction, and formatting for slides.
    """

    # Define available slide layouts
    LAYOUTS = {
        "TITLE": "TITLE",
        "TITLE_AND_BODY": "TITLE_AND_BODY",
        "TITLE_AND_TWO_COLUMNS": "TITLE_AND_TWO_COLUMNS",
        "TITLE_ONLY": "TITLE_ONLY",
        "BLANK": "BLANK",
        "SECTION_HEADER": "SECTION_HEADER",
        "CAPTION_ONLY": "CAPTION_ONLY",
        "BIG_NUMBER": "BIG_NUMBER",
    }

    def __init__(self):
        """Initialize the converter."""
        # Extensions to enable in the markdown parser
        self.markdown_extensions = [
            "extra",  # Tables, attr_list, etc.
            "codehilite",  # Code highlighting
            "sane_lists",  # Better list handling
            "smarty",  # Smart quotes
            "meta",  # Metadata
        ]

    def split_slides(self, markdown_content: str) -> list[str]:
        """
        Split markdown content into individual slide sections.

        Args:
            markdown_content: Full markdown content

        Returns:
            List of slide section strings
        """
        # Normalize line endings first
        normalized_content = markdown_content.replace("\r\n", "\n").replace("\r", "\n")

        # Log input
        logger.info(f"Splitting markdown of length {len(normalized_content)} into slides")
        # logger.debug(f"Normalized content preview:\n{normalized_content[:500]}...") # Optional: log content preview

        # First, try splitting by horizontal rule markers (---, ***) respecting blank lines around them
        hr_pattern = r"\n\s*[-*]{3,}\s*\n"
        sections_by_hr = re.split(hr_pattern, normalized_content)

        # Log split results
        logger.info(f"Split by horizontal rules found {len(sections_by_hr)} sections")
        for i, section in enumerate(sections_by_hr):
            logger.info(f"HR Section {i} length: {len(section)}")
            logger.info(f"HR Section {i} preview: {section[:100]}...")

        # If we found multiple sections using horizontal rules, use them
        if len(sections_by_hr) > 1:
            logger.info(f"Split by horizontal rule (---, ***) into {len(sections_by_hr)} sections")
            return [s.strip() for s in sections_by_hr if s.strip()]

        # If HR split didn't work, try splitting by H2 headers (##)
        # But we need to keep the # in the content
        h2_pattern = r"(?:^|\n)(?=## )"  # Look for ## at beginning of a line
        sections_by_h2 = re.split(h2_pattern, normalized_content)

        # Restore the '## ' prefix to the subsequent sections
        processed_sections_by_h2 = []
        if sections_by_h2:
            # The first section might not start with ##, keep it as is
            if sections_by_h2[0].strip():
                processed_sections_by_h2.append(sections_by_h2[0])
            # For subsequent sections, prepend '## ' if split occurred
            for section in sections_by_h2[1:]:
                if section.strip():  # Avoid adding prefix to potentially empty trailing sections
                    processed_sections_by_h2.append(f"## {section}")

        # If we found multiple sections using h2 headers, use them
        if len(processed_sections_by_h2) > 1:
            logger.info(f"Split by H2 headers (##) into {len(processed_sections_by_h2)} sections")
            return [s.strip() for s in processed_sections_by_h2 if s.strip()]

        # If we get here, we couldn't find multiple slides, so return the whole content as one slide
        logger.info(
            "Could not find slide separators (HR or H2), treating content as a single slide"
        )
        return [normalized_content.strip()] if normalized_content.strip() else []

    def parse_slide_markdown(self, markdown_section: str) -> tuple[str, list[dict[str, Any]]]:
        """
        Parse a markdown section into slide elements with proper formatting.

        Args:
            markdown_section: Markdown content for a single slide

        Returns:
            Tuple of (layout, elements)
        """
        logger.info(f"Parsing slide section of length {len(markdown_section)}")
        logger.info(f"Section preview: {markdown_section[:200]}...")

        try:
            # Convert markdown to HTML
            html = markdown.markdown(markdown_section, extensions=self.markdown_extensions)

            # Log the generated HTML
            logger.info(f"Generated HTML of length {len(html)}")
            logger.info(f"HTML preview: {html[:200]}...")

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Extract slide elements
            elements = []

            # Track if we've processed standard elements
            has_title = False
            has_subtitle = False
            has_bullets = False
            has_image = False
            has_table = False

            # Track current Y position for element placement
            current_y = 50  # Start position for first element

            # Process headings
            h1 = soup.find("h1")
            if h1:
                elements.append(
                    {
                        "type": "title",
                        "content": h1.get_text(),
                        "position": (100, current_y),  # Use tracked Y position
                        "size": (600, 50),
                    }
                )
                has_title = True
                current_y += 70  # Increment Y position for next element
                # Remove the h1 from soup so we don't process it again
                h1.extract()

            h2 = soup.find("h2")
            if h2:
                elements.append(
                    {
                        "type": "subtitle",
                        "content": h2.get_text(),
                        "position": (100, current_y),  # Use tracked Y position
                        "size": (600, 40),
                    }
                )
                has_subtitle = True
                current_y += 50  # Increment Y position for next element
                h2.extract()

            # Process h3 (subheadings)
            h3_elements = soup.find_all("h3")
            for h3 in h3_elements:
                elements.append(
                    {
                        "type": "text",
                        "content": h3.get_text(),
                        "position": (100, current_y),  # Use tracked Y position
                        "size": (600, 40),
                    }
                )
                current_y += 50  # Increment Y position for next element
                h3.extract()

            # Process lists (ul, ol)
            lists = soup.find_all(["ul", "ol"])
            for list_elem in lists:
                list_items = []
                list_type = "bullets" if list_elem.name == "ul" else "numbered"

                for li in list_elem.find_all("li", recursive=False):
                    # Extract text from li, handling nested formatting
                    item_text = self._extract_formatted_text(li)
                    list_items.append(item_text)

                    # Handle nested lists
                    nested_lists = li.find_all(["ul", "ol"], recursive=False)
                    for nested_list in nested_lists:
                        nested_items = []
                        for nested_li in nested_list.find_all("li"):
                            nested_text = self._extract_formatted_text(nested_li)
                            nested_items.append(
                                {"text": nested_text, "level": 1}  # Nested level
                            )
                        if nested_items:
                            list_items[-1] = {
                                "text": item_text,
                                "level": 0,
                                "children": nested_items,
                            }

                if list_items:
                    elements.append(
                        {
                            "type": list_type,
                            "items": list_items,
                            "position": (100, current_y),  # Use tracked Y position
                            "size": (
                                600,
                                max(200, len(list_items) * 25),
                            ),  # Scale height based on items
                        }
                    )
                    has_bullets = True
                    current_y += max(200, len(list_items) * 25) + 20  # Add padding between elements
                    list_elem.extract()

            # Process images
            images = soup.find_all("img")
            for img in images:
                elements.append(
                    {
                        "type": "image",
                        "alt": img.get("alt", ""),
                        "url": img.get("src", ""),
                        "position": (250, current_y),  # Use tracked Y position
                        "size": (300, 200),  # Default image size
                    }
                )
                has_image = True
                current_y += 220  # Increment Y position for next element
                img.extract()

            # Process tables
            tables = soup.find_all("table")
            for table in tables:
                rows = []

                # Process headers
                headers = []
                thead = table.find("thead")
                if thead:
                    th_row = thead.find("tr")
                    if th_row:
                        for th in th_row.find_all("th"):
                            headers.append(self._extract_formatted_text(th))

                # Process body rows
                tbody = table.find("tbody") or table
                for tr in tbody.find_all("tr"):
                    row = []
                    for td in tr.find_all(["td", "th"]):
                        row.append(self._extract_formatted_text(td))
                    if row:
                        rows.append(row)

                if headers or rows:
                    elements.append(
                        {
                            "type": "table",
                            "headers": headers,
                            "rows": rows,
                            "position": (100, current_y),  # Use tracked Y position
                            "size": (600, 200),
                        }
                    )
                    has_table = True
                    current_y += 220  # Increment Y position for next element
                    table.extract()

            # Process remaining paragraphs as text
            paragraphs = []
            for p in soup.find_all("p"):
                paragraphs.append(self._extract_formatted_text(p))

            if paragraphs:
                elements.append(
                    {
                        "type": "text",
                        "content": "\n\n".join(paragraphs),
                        "position": (100, current_y),  # Use tracked Y position
                        "size": (600, 100),
                    }
                )
                current_y += 120  # Increment Y position for next element

            # Determine best layout based on content
            layout = self._determine_layout(
                has_title, has_subtitle, has_bullets, has_image, has_table
            )

            # Check for speaker notes (special syntax: <!-- notes: ... -->)
            notes_match = re.search(r"<!--\s*notes:\s*(.*?)\s*-->", markdown_section, re.DOTALL)
            if notes_match:
                elements.append({"type": "notes", "content": notes_match.group(1).strip()})

            return layout, elements
        except Exception as e:
            logger.warning(f"Error parsing markdown: {str(e)}")
            # Return a fallback layout and simple text element
            return self.LAYOUTS["BLANK"], [
                {
                    "type": "text",
                    "content": markdown_section,
                    "position": (100, 100),
                    "size": (600, 300),
                }
            ]

    def _extract_formatted_text(self, element) -> str:
        """
        Extract text with formatting from BeautifulSoup element.

        Args:
            element: BeautifulSoup element

        Returns:
            Formatted text string with formatting markers for later processing
        """
        # If element is just a string, return it
        if isinstance(element, str):
            return element

        formatted_text = ""
        logger.info(
            f"Extracting formatted text from element: {element.name if hasattr(element, 'name') else 'text node'}"
        )

        # Process all nested elements to preserve formatting
        for child in element.children:
            if child.name is None:  # Text node
                formatted_text += child.string or ""
            elif child.name == "strong" or child.name == "b":
                child_text = self._extract_formatted_text(child)
                formatted_text += f"**{child_text}**"
                logger.info(f"Found BOLD text: '{child_text}'")
            elif child.name == "em" or child.name == "i":
                child_text = self._extract_formatted_text(child)
                formatted_text += f"*{child_text}*"
                logger.info(f"Found ITALIC text: '{child_text}'")
            elif child.name == "code":
                child_text = self._extract_formatted_text(child)
                formatted_text += f"`{child_text}`"
            elif child.name == "a":
                child_text = self._extract_formatted_text(child)
                formatted_text += child_text
            elif child.name in ["p", "div", "li", "td", "th"]:
                formatted_text += self._extract_formatted_text(child)
            else:
                # For any other element, just get its text
                formatted_text += child.get_text()

        return formatted_text.strip()

    def _determine_layout(
        self,
        has_title: bool,
        has_subtitle: bool,
        has_bullets: bool,
        has_image: bool,
        has_table: bool,
    ) -> str:
        """
        Determine the best slide layout based on content.

        Args:
            has_title: Whether slide has a title
            has_subtitle: Whether slide has a subtitle
            has_bullets: Whether slide has bullet points
            has_image: Whether slide has an image
            has_table: Whether slide has a table

        Returns:
            Slide layout name
        """
        if has_title:
            if has_subtitle and (has_bullets or has_table):
                return self.LAYOUTS["TITLE_AND_BODY"]
            if has_image and not has_bullets and not has_table:
                return self.LAYOUTS["CAPTION_ONLY"]
            if has_bullets or has_table:
                return self.LAYOUTS["TITLE_AND_BODY"]
            return self.LAYOUTS["TITLE_ONLY"]
        return self.LAYOUTS["BLANK"]

    def create_text_style_requests(
        self, formatted_text: str, element_id: str, start_index: int = 0
    ) -> tuple[str, list[dict]]:
        """
        Create requests to apply text styling for formatted text.

        Args:
            formatted_text: Text with markdown-style formatting markers
            element_id: ID of the text element
            start_index: Starting character index

        Returns:
            Tuple of (plain_text, style_requests)
        """
        # Don't try to style if no formatting is detected
        if (
            "**" not in formatted_text
            and "*" not in formatted_text  # Only handle bold/italic for now
            # and "`" not in formatted_text # Code handling TBD
        ):
            return formatted_text, []

        # plain_text will be generated, style_requests will be populated
        style_requests = []

        try:
            # First, build the plain text by removing all formatting
            plain_text = formatted_text
            # Remove bold markers first (important for correct offset calculation)
            plain_text = re.sub(r"\*\*(.*?)\*\*", r"\1", plain_text)
            # Remove italic markers
            plain_text = re.sub(r"\*(.*?)\*", r"\1", plain_text)
            # Remove code markers (if implemented)
            # plain_text = re.sub(r"`(.*?)`", r"\1", plain_text)

            # Helper function to calculate plain text index from original index
            def get_plain_index(original_index, original_text):
                text_before = original_text[:original_index]
                # Count markers removed before this index
                # bold_markers_removed = len(re.findall(r'\*\*', text_before)) * 2
                # italic_markers_removed = len(re.findall(r'\*', text_before)) * 2 # Assumes * is only for italic
                # code_markers_removed = len(re.findall(r'`', text_before)) * 2
                # Need to be careful about nested/overlapping markers, this simple count might be insufficient
                # A more robust way is to build the plain text incrementally and map indices

                # Let's try the simplified approach first based on user code:
                plain_equivalent_before = text_before
                plain_equivalent_before = re.sub(r"\*\*(.*?)\*\*", r"\1", plain_equivalent_before)
                plain_equivalent_before = re.sub(r"\*(.*?)\*", r"\1", plain_equivalent_before)
                # plain_equivalent_before = re.sub(r"`(.*?)`", r"\1", plain_equivalent_before)
                return len(plain_equivalent_before)

            # Generate style requests for bold formatting
            bold_matches = list(re.finditer(r"\*\*(.*?)\*\*", formatted_text))
            for match in bold_matches:
                content = match.group(1)  # Text inside ** markers
                # Calculate start index in plain text
                start_idx = get_plain_index(match.start(), formatted_text)
                end_idx = start_idx + len(content)

                style_requests.append(
                    {
                        "updateTextStyle": {
                            "objectId": element_id,
                            "textRange": {"startIndex": start_idx, "endIndex": end_idx},
                            "style": {"bold": True},
                            "fields": "bold",
                        }
                    }
                )

            # Generate style requests for italic formatting
            italic_matches = list(re.finditer(r"\*(.*?)\*", formatted_text))
            for match in italic_matches:
                # Skip if this is part of a bold marker (e.g., ** *italic* **) - simplistic check
                is_part_of_bold = False
                for bold_match in bold_matches:
                    # Check if italic is *inside* bold markers
                    if bold_match.start() < match.start() and match.end() < bold_match.end():
                        is_part_of_bold = True
                        break

                if not is_part_of_bold:
                    content = match.group(1)  # Text inside * markers
                    # Calculate position in plain text
                    start_idx = get_plain_index(match.start(), formatted_text)
                    end_idx = start_idx + len(content)

                    style_requests.append(
                        {
                            "updateTextStyle": {
                                "objectId": element_id,
                                "textRange": {
                                    "startIndex": start_idx,
                                    "endIndex": end_idx,
                                },
                                "style": {"italic": True},
                                "fields": "italic",
                            }
                        }
                    )

            # Add logger info if needed
            logger.info(f"Generated {len(style_requests)} style requests for element {element_id}")
            return plain_text, style_requests

        except Exception as e:
            # If there's any error in formatting, just return the original text
            logger.warning(f"Error processing text formatting: {str(e)}")
            return (
                formatted_text.replace("**", "").replace("*", "").replace("`", ""),
                [],
            )

    def generate_slide_requests(self, presentation_id: str, elements: list[dict]) -> list[dict]:
        # Implementation of generate_slide_requests method
        pass
