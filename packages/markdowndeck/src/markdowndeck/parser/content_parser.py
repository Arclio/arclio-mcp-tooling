import logging
import re

from markdown_it import MarkdownIt
from markdown_it.token import Token

from ..models import (
    AlignmentType,
    CodeElement,
    Element,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
    VerticalAlignmentType,
)

logger = logging.getLogger(__name__)


class ContentParser:
    """Parse markdown content into slide elements."""

    def __init__(self):
        """Initialize the content parser."""
        # Initialize markdown parser
        opts = {
            "html": False,  # Don't allow HTML in the markdown
            "typographer": True,  # Enable typographic replacements
            "linkify": True,  # Auto-convert URLs to links
        }
        self.md = MarkdownIt("commonmark", opts)

        # Register plugins if needed
        # self.md.use(markdown_it.plugins.somePlugin)

    def parse_content(
        self, title: str | None, sections: list[dict], footer: str | None
    ) -> list[Element]:
        """
        Parse markdown content into slide elements.

        Args:
            title: Slide title (if any)
            sections: List of parsed sections
            footer: Slide footer (if any)

        Returns:
            List of Element objects
        """
        logger.debug("Parsing content into slide elements")
        elements = []

        # Add title element if present
        if title:
            title_element = TextElement(
                element_type=ElementType.TITLE,
                text=title,
                formatting=self._extract_formatting_from_text(title),
            )
            elements.append(title_element)
            logger.debug(f"Added title element: {title[:30]}")

        # Process each section
        for section in sections:
            section_elements = self._parse_section(section)
            elements.extend(section_elements)

        # Add footer if present
        if footer:
            footer_element = TextElement(
                element_type=ElementType.FOOTER,
                text=footer,
                formatting=self._extract_formatting_from_text(footer),
            )
            elements.append(footer_element)
            logger.debug(f"Added footer element: {footer[:30]}")

        logger.info(f"Created {len(elements)} elements from content")
        return elements

    def _parse_section(self, section: dict) -> list[Element]:
        """
        Parse a section into elements.

        Args:
            section: Section dictionary

        Returns:
            List of elements
        """
        if section["type"] == "section":
            return self._parse_simple_section(section)
        if section["type"] == "row":
            return self._parse_row_section(section)
        logger.warning(f"Unknown section type: {section['type']}")
        return []

    def _parse_simple_section(self, section: dict) -> list[Element]:
        """
        Parse a simple section into elements.

        Args:
            section: Section dictionary

        Returns:
            List of elements
        """
        content = section["content"]
        directives = section["directives"]

        # Parse markdown to tokens
        tokens = self.md.parse(content)

        # Process tokens into elements
        elements = self._process_tokens(tokens, directives)

        # Apply section directives to elements
        for element in elements:
            # Apply alignment if specified
            if "align" in directives and isinstance(element, TextElement):
                element.horizontal_alignment = AlignmentType(directives["align"])

            # Apply vertical alignment if specified
            if "valign" in directives and isinstance(element, TextElement):
                element.vertical_alignment = VerticalAlignmentType(directives["valign"])

            # Apply other directives
            for key, value in directives.items():
                if key not in ["align", "valign"]:
                    element.directives[key] = value

        return elements

    def _parse_row_section(self, section: dict) -> list[Element]:
        """
        Parse a row section with subsections.

        Args:
            section: Row section dictionary

        Returns:
            List of elements
        """
        elements = []

        # Process each subsection
        for subsection in section.get("subsections", []):
            subsection_elements = self._parse_simple_section(subsection)
            elements.extend(subsection_elements)

        return elements

    def _process_tokens(self, tokens: list[Token], directives: dict) -> list[Element]:
        """
        Process markdown tokens into slide elements.

        Args:
            tokens: List of markdown tokens
            directives: Section directives

        Returns:
            List of elements
        """
        elements = []

        # Keep track of current position in token list
        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Process different token types
            if token.type == "heading_open":
                element, i = self._process_heading(tokens, i, directives)
                if element:
                    elements.append(element)

            elif token.type == "paragraph_open":
                element, i = self._process_paragraph(tokens, i, directives)
                if element:
                    elements.append(element)

            elif token.type == "bullet_list_open":
                element, i = self._process_bullet_list(tokens, i, directives)
                if element:
                    elements.append(element)

            elif token.type == "ordered_list_open":
                element, i = self._process_ordered_list(tokens, i, directives)
                if element:
                    elements.append(element)

            elif token.type == "fence":
                element = self._process_code_block(token, directives)
                if element:
                    elements.append(element)

            elif token.type == "table_open":
                element, i = self._process_table(tokens, i, directives)
                if element:
                    elements.append(element)

            # Move to next token
            i += 1

        # Process images separately since markdown-it handles them differently
        images = self._process_images(tokens, directives)
        if images:
            elements.extend(images)

        return elements

    def _process_images(self, tokens: list[Token], directives: dict) -> list[Element]:
        """
        Process image tokens into image elements.

        Args:
            tokens: List of markdown tokens
            directives: Section directives

        Returns:
            List of image elements
        """
        images = []

        # Look for image tokens within inline tokens
        for token in tokens:
            if token.type == "inline" and hasattr(token, "children"):
                for child in token.children:
                    if child.type == "image":
                        # Extract image attributes
                        image_attrs = {}
                        if hasattr(child, "attrs") and isinstance(child.attrs, dict):
                            image_attrs = child.attrs

                        # Get src and alt attributes
                        src = image_attrs.get("src", "")
                        alt = image_attrs.get("alt", "")

                        # Extract alt text from markdown syntax if not found in attrs
                        if not alt and token.content:
                            # Try to extract alt text from markdown syntax: ![Alt text](url)
                            alt_match = re.search(r"!\[(.*?)\]", token.content)
                            if alt_match:
                                alt = alt_match.group(1)

                        if src:
                            # Create image element
                            image = ImageElement(
                                element_type=ElementType.IMAGE,
                                url=src,
                                alt_text=alt,
                            )
                            images.append(image)
                            logger.debug(f"Created image element: {src} (alt: {alt})")

        # Also look for direct image tokens (some markdown-it versions handle them differently)
        for token in tokens:
            if token.type == "image":
                image_attrs = {}
                if hasattr(token, "attrs") and isinstance(token.attrs, dict):
                    image_attrs = token.attrs

                src = image_attrs.get("src", "")
                alt = image_attrs.get("alt", "")

                if src:
                    image = ImageElement(
                        element_type=ElementType.IMAGE,
                        url=src,
                        alt_text=alt,
                    )
                    images.append(image)
                    logger.debug(f"Created image element from direct token: {src} (alt: {alt})")

        return images

    def _process_heading(
        self, tokens: list[Token], start_index: int, directives: dict
    ) -> tuple[Element | None, int]:
        """
        Process a heading token into a text element.

        Args:
            tokens: List of tokens
            start_index: Starting index in token list
            directives: Section directives

        Returns:
            Tuple of (Element or None, new_index)
        """
        token = tokens[start_index]
        level = int(token.tag[1])  # h1, h2, etc.

        # Find the inline token with heading text
        inline_index = start_index + 1
        end_index = start_index

        if inline_index < len(tokens) and tokens[inline_index].type == "inline":
            text = tokens[inline_index].content
            formatting = self._extract_formatting(tokens[inline_index])

            # Find heading close token
            for j in range(inline_index + 1, len(tokens)):
                if tokens[j].type == "heading_close":
                    end_index = j
                    break

            # Determine element type based on heading level
            if level == 1:
                element_type = ElementType.TITLE
            elif level == 2:
                element_type = ElementType.SUBTITLE
            else:
                element_type = ElementType.TEXT

            # Create element
            element = TextElement(
                element_type=element_type,
                text=text,
                formatting=formatting,
            )

            # Apply horizontal alignment
            if "align" in directives:
                element.horizontal_alignment = AlignmentType(directives["align"])

            return element, end_index

        return None, start_index

    def _process_paragraph(
        self, tokens: list[Token], start_index: int, directives: dict
    ) -> tuple[Element | None, int]:
        """
        Process a paragraph token into a text element.

        Args:
            tokens: List of tokens
            start_index: Starting index in token list
            directives: Section directives

        Returns:
            Tuple of (Element or None, new_index)
        """
        # Find the inline token with paragraph text
        inline_index = start_index + 1
        end_index = start_index

        if inline_index < len(tokens) and tokens[inline_index].type == "inline":
            text = tokens[inline_index].content
            formatting = self._extract_formatting(tokens[inline_index])

            # Find paragraph close token
            for j in range(inline_index + 1, len(tokens)):
                if tokens[j].type == "paragraph_close":
                    end_index = j
                    break

            # Check if paragraph is an image only paragraph
            contains_image = False
            if hasattr(tokens[inline_index], "children"):
                for child in tokens[inline_index].children:
                    if child.type == "image":
                        contains_image = True
                        break

            # Skip if this is just an image (we'll handle images separately)
            if contains_image:
                # Check if paragraph content is mostly just the image
                image_pattern = r"!\[.*?\]\([^)]+\)"
                clean_content = re.sub(image_pattern, "", text).strip()
                if not clean_content:
                    return None, end_index

            # Create text element
            element = TextElement(
                element_type=ElementType.TEXT,
                text=text,
                formatting=formatting,
            )

            # Apply horizontal alignment
            if "align" in directives:
                element.horizontal_alignment = AlignmentType(directives["align"])

            return element, end_index

        return None, start_index

    def _process_bullet_list(
        self, tokens: list[Token], start_index: int, directives: dict
    ) -> tuple[Element | None, int]:
        """
        Process a bullet list into a list element.

        Args:
            tokens: List of tokens
            start_index: Starting index in token list
            directives: Section directives

        Returns:
            Tuple of (Element or None, new_index)
        """
        return self._process_list(tokens, start_index, directives, ordered=False)

    def _process_ordered_list(
        self, tokens: list[Token], start_index: int, directives: dict
    ) -> tuple[Element | None, int]:
        """
        Process an ordered list into a list element.

        Args:
            tokens: List of tokens
            start_index: Starting index in token list
            directives: Section directives

        Returns:
            Tuple of (Element or None, new_index)
        """
        return self._process_list(tokens, start_index, directives, ordered=True)

    def _process_list(
        self, tokens: list[Token], start_index: int, directives: dict, ordered: bool
    ) -> tuple[Element | None, int]:
        """
        Process a list into a list element.

        Args:
            tokens: List of tokens
            start_index: Starting index in token list
            directives: Section directives
            ordered: Whether this is an ordered list

        Returns:
            Tuple of (Element or None, new_index)
        """
        # Find the end of the list
        token = tokens[start_index]
        list_type = "ordered_list" if ordered else "bullet_list"
        end_tag = f"{list_type}_close"

        end_index = start_index
        depth = 1

        for j in range(start_index + 1, len(tokens)):
            if tokens[j].type == token.type:
                depth += 1
            elif tokens[j].type == end_tag:
                depth -= 1
                if depth == 0:
                    end_index = j
                    break

        # Extract items
        items = self._extract_list_items(tokens, start_index + 1, end_index, 0)

        # Create element
        element = ListElement(
            element_type=(ElementType.ORDERED_LIST if ordered else ElementType.BULLET_LIST),
            items=items,
        )

        return element, end_index

    def _extract_list_items(
        self, tokens: list[Token], start_index: int, end_index: int, level: int
    ) -> list[ListItem]:
        """
        Extract list items from tokens.

        Args:
            tokens: List of tokens
            start_index: Starting index in token list
            end_index: Ending index in token list
            level: Nesting level

        Returns:
            List of ListItem objects
        """
        items = []
        i = start_index

        while i < end_index:
            token = tokens[i]

            if token.type == "list_item_open":
                # Find the inline token with item text
                item_text = ""
                item_formatting = []

                # Look for content in this item
                j = i + 1
                while j < end_index and tokens[j].type != "list_item_close":
                    if tokens[j].type == "paragraph_open":
                        k = j + 1
                        if k < end_index and tokens[k].type == "inline":
                            item_text = tokens[k].content
                            item_formatting = self._extract_formatting(tokens[k])
                        j = k  # Skip past paragraph contents

                    # Skip over nested lists (they'll be processed recursively)
                    elif tokens[j].type in ["bullet_list_open", "ordered_list_open"]:
                        level + 1
                        nested_start = j + 1

                        # Find the end of the nested list
                        nested_end = nested_start
                        nested_depth = 1

                        for k in range(nested_start, end_index):
                            if tokens[k].type == tokens[j].type:
                                nested_depth += 1
                            elif tokens[k].type == tokens[j].type.replace("_open", "_close"):
                                nested_depth -= 1
                                if nested_depth == 0:
                                    nested_end = k
                                    break

                        # Skip the entire nested list
                        j = nested_end

                    j += 1

                # Create list item
                item = ListItem(
                    text=item_text,
                    level=level,
                    formatting=item_formatting,
                )

                # Look for nested lists
                j = i + 1
                while j < end_index and tokens[j].type != "list_item_close":
                    if tokens[j].type in ["bullet_list_open", "ordered_list_open"]:
                        nested_start = j + 1

                        # Find the end of the nested list
                        nested_end = nested_start
                        nested_depth = 1

                        for k in range(nested_start, end_index):
                            if tokens[k].type == tokens[j].type:
                                nested_depth += 1
                            elif tokens[k].type == tokens[j].type.replace("_open", "_close"):
                                nested_depth -= 1
                                if nested_depth == 0:
                                    nested_end = k
                                    break

                        # Process nested list items
                        nested_items = self._extract_list_items(
                            tokens, nested_start, nested_end, level + 1
                        )

                        # Add as children
                        item.children.extend(nested_items)

                        # Skip the entire nested list
                        j = nested_end

                    j += 1

                items.append(item)
                i = j  # Move to list_item_close

            i += 1

        return items

    def _process_code_block(self, token: Token, directives: dict) -> Element | None:
        """
        Process a code block token into a code element.

        Args:
            token: Code block token
            directives: Section directives

        Returns:
            Code element or None
        """
        if token.type != "fence":
            return None

        # Get code and language
        code = token.content
        language = token.info or "text"

        # Create element
        return CodeElement(
            element_type=ElementType.CODE,
            code=code,
            language=language,
        )

    def _process_table(
        self, tokens: list[Token], start_index: int, directives: dict
    ) -> tuple[Element | None, int]:
        """
        Process a table into a table element.

        Args:
            tokens: List of tokens
            start_index: Starting index in token list
            directives: Section directives

        Returns:
            Tuple of (Element or None, new_index)
        """
        # Find the end of the table
        end_index = start_index

        for j in range(start_index + 1, len(tokens)):
            if tokens[j].type == "table_close":
                end_index = j
                break

        # Extract headers and rows
        headers = []
        rows = []

        # Process table
        in_head = False
        in_body = False
        current_row = []

        i = start_index + 1
        while i < end_index:
            token = tokens[i]

            if token.type == "thead_open":
                in_head = True
            elif token.type == "thead_close":
                in_head = False
            elif token.type == "tbody_open":
                in_body = True
            elif token.type == "tbody_close":
                in_body = False
            elif token.type == "tr_open":
                current_row = []
            elif token.type == "tr_close":
                if in_head:
                    headers = current_row.copy()
                elif in_body:
                    rows.append(current_row.copy())
                current_row = []
            elif token.type == "th_open":
                # Get the header cell content
                if i + 1 < end_index and tokens[i + 1].type == "inline":
                    current_row.append(tokens[i + 1].content)
            elif token.type == "td_open" and i + 1 < end_index and tokens[i + 1].type == "inline":
                # Get the data cell content
                current_row.append(tokens[i + 1].content)

            i += 1

        # Create table element
        element = TableElement(
            element_type=ElementType.TABLE,
            headers=headers,
            rows=rows,
        )

        return element, end_index

    def _extract_formatting(self, token: Token) -> list[TextFormat]:
        """
        Extract text formatting from an inline token.

        Args:
            token: Inline token

        Returns:
            List of TextFormat objects
        """
        if token.type != "inline" or not hasattr(token, "children"):
            return []

        formatting = []

        # Track text positions for formatting
        text = token.content
        pos = 0
        format_stack = []

        for child in token.children:
            child_content = getattr(child, "content", "")
            getattr(child, "markup", "")
            child_type = getattr(child, "type", "")

            # Opening formatting tags
            if child_type.endswith("_open"):
                base_type = child_type.split("_")[0]
                format_type = None

                if base_type == "strong":
                    format_type = TextFormatType.BOLD
                elif base_type == "em":
                    format_type = TextFormatType.ITALIC
                elif base_type == "s":
                    format_type = TextFormatType.STRIKETHROUGH
                elif base_type == "link":
                    format_type = TextFormatType.LINK
                    value = child.attrs.get("href", "") if hasattr(child, "attrs") else ""
                else:
                    format_type = None

                if format_type:
                    format_stack.append((format_type, pos, value if base_type == "link" else True))

            # Closing formatting tags
            elif child_type.endswith("_close"):
                if format_stack:
                    base_type = child_type.split("_")[0]
                    for i in range(len(format_stack) - 1, -1, -1):
                        format_info = format_stack[i]
                        stack_type = format_info[0]

                        if (
                            (base_type == "strong" and stack_type == TextFormatType.BOLD)
                            or (base_type == "em" and stack_type == TextFormatType.ITALIC)
                            or (base_type == "s" and stack_type == TextFormatType.STRIKETHROUGH)
                            or (base_type == "link" and stack_type == TextFormatType.LINK)
                        ):
                            format_type, start_pos, value = format_stack.pop(i)
                            formatting.append(
                                TextFormat(
                                    start=start_pos,
                                    end=pos,
                                    format_type=format_type,
                                    value=value,
                                )
                            )
                            break

            # Inline code
            elif child_type == "code_inline":
                start_pos = pos
                end_pos = pos + len(child_content)
                formatting.append(
                    TextFormat(start=start_pos, end=end_pos, format_type=TextFormatType.CODE)
                )
                pos = end_pos
                continue

            # Plain text
            elif child_type == "text":
                pos += len(child_content)

            # Image - skip over image markdown in formatting
            elif child_type == "image":
                # Skip over image markup in formatting
                img_pattern = r"!\[.*?\]\([^)]+\)"
                img_match = re.search(img_pattern, text[pos:])
                if img_match:
                    pos += len(img_match.group(0))

        return formatting

    def _extract_formatting_from_text(self, text: str) -> list[TextFormat]:
        """
        Extract formatting from plain text.

        Args:
            text: Plain text

        Returns:
            List of TextFormat objects
        """
        # Parse text as markdown
        tokens = self.md.parse(text)

        # Find the inline token
        for token in tokens:
            if token.type == "inline":
                return self._extract_formatting(token)

        return []
