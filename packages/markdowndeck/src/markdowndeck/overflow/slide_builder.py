"""Slide builder for creating continuation slides with proper formatting."""

import logging
import uuid
from copy import deepcopy

from markdowndeck.models import ElementType, Slide, SlideLayout, TextElement
from markdowndeck.overflow.models import ContentGroup

logger = logging.getLogger(__name__)


class SlideBuilder:
    """
    Builds continuation slides with consistent formatting and metadata.

    Handles:
    - Title creation for continuation slides
    - Footer preservation and updates
    - Slide metadata consistency
    - Element ID generation
    """

    def __init__(
        self,
        slide_width: float = 720,
        slide_height: float = 405,
        margins: dict[str, float] = None,
    ):
        """
        Initialize slide builder.

        Args:
            slide_width: Width of slides in points
            slide_height: Height of slides in points
            margins: Slide margins
        """
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins or {"top": 50, "right": 50, "bottom": 50, "left": 50}

        # Calculate positioning constants
        self.header_height = 90.0
        self.footer_height = 30.0
        self.title_y = self.margins["top"] + 20
        self.footer_y = slide_height - margins["bottom"] - self.footer_height

        logger.debug("SlideBuilder initialized")

    def create_first_slide(self, original_slide: Slide, content_groups: list[ContentGroup]) -> Slide:
        """
        Create the first slide, preserving original title and adding selected content.

        Args:
            original_slide: Original slide to base on
            content_groups: Content groups for this slide

        Returns:
            First slide with original title and selected content
        """
        logger.debug(f"Creating first slide from {original_slide.object_id}")

        # Create new slide with same metadata
        new_slide = Slide(
            object_id=original_slide.object_id,  # Keep original ID for first slide
            layout=original_slide.layout,
            notes=original_slide.notes,
            background=original_slide.background,
            title=original_slide.title,
            sections=[],  # Clear sections - we're working with positioned elements
            elements=[],
        )

        # Copy header elements (title, subtitle)
        self._copy_header_elements(original_slide, new_slide)

        # Add content elements from groups
        self._add_content_elements(new_slide, content_groups)

        # Copy footer elements
        self._copy_footer_elements(original_slide, new_slide)

        logger.debug(f"First slide created with {len(new_slide.elements)} elements")
        return new_slide

    def create_continuation_slide(
        self,
        original_slide: Slide,
        content_groups: list[ContentGroup],
        slide_number: int,
    ) -> Slide:
        """
        Create a continuation slide with modified title and selected content.

        Args:
            original_slide: Original slide to base on
            content_groups: Content groups for this slide
            slide_number: Sequential number of this continuation slide

        Returns:
            Continuation slide with appropriate title and content
        """
        logger.debug(f"Creating continuation slide {slide_number} from {original_slide.object_id}")

        # Create new slide ID
        new_slide_id = f"{original_slide.object_id}_cont_{slide_number}"

        # Create new slide
        new_slide = Slide(
            object_id=new_slide_id,
            layout=SlideLayout.TITLE_AND_BODY,  # Standard layout for continuation
            notes=original_slide.notes,  # Keep original notes for reference
            background=original_slide.background,
            title=self._create_continuation_title(original_slide.title, slide_number),
            sections=[],  # Clear sections
            elements=[],
        )

        # Create continuation title
        self._create_continuation_header(original_slide, new_slide, slide_number)

        # Add content elements from groups
        self._add_content_elements(new_slide, content_groups)

        # Create continuation footer
        self._create_continuation_footer(original_slide, new_slide, slide_number)

        logger.debug(f"Continuation slide {slide_number} created with {len(new_slide.elements)} elements")
        return new_slide

    def _copy_header_elements(self, source_slide: Slide, target_slide: Slide) -> None:
        """Copy header elements (title, subtitle) from source to target slide."""
        for element in source_slide.elements:
            if element.element_type in (ElementType.TITLE, ElementType.SUBTITLE):
                # Deep copy to avoid modifying original
                copied_element = deepcopy(element)

                # Generate new object ID to avoid conflicts
                copied_element.object_id = self._generate_element_id(element.element_type)

                target_slide.elements.append(copied_element)

    def _create_continuation_header(self, original_slide: Slide, new_slide: Slide, slide_number: int) -> None:
        """Create header for continuation slide."""
        # Create continuation title
        continuation_title = self._create_continuation_title(original_slide.title, slide_number)

        title_element = TextElement(
            element_type=ElementType.TITLE,
            text=continuation_title,
            object_id=self._generate_element_id(ElementType.TITLE),
            position=(self._calculate_title_x(continuation_title), self.title_y),
            size=(self._calculate_title_width(continuation_title), 40),
        )

        new_slide.elements.append(title_element)

    def _copy_footer_elements(self, source_slide: Slide, target_slide: Slide) -> None:
        """Copy footer elements from source to target slide."""
        for element in source_slide.elements:
            if element.element_type == ElementType.FOOTER:
                # Deep copy footer
                copied_footer = deepcopy(element)

                # Generate new object ID
                copied_footer.object_id = self._generate_element_id(ElementType.FOOTER)

                # Update position to ensure it's at the bottom
                if copied_footer.size:
                    copied_footer.position = (
                        (copied_footer.position[0] if copied_footer.position else self.margins["left"]),
                        self.footer_y,
                    )

                target_slide.elements.append(copied_footer)

    def _create_continuation_footer(self, original_slide: Slide, new_slide: Slide, slide_number: int) -> None:
        """Create footer for continuation slide."""
        # Find original footer
        original_footer = None
        for element in original_slide.elements:
            if element.element_type == ElementType.FOOTER:
                original_footer = element
                break

        if original_footer:
            # Copy and modify footer
            footer_text = original_footer.text if hasattr(original_footer, "text") else "Page Footer"

            # Add continuation indicator if not already present
            if "(cont.)" not in footer_text:
                footer_text = f"{footer_text} (cont.)"

            footer_element = TextElement(
                element_type=ElementType.FOOTER,
                text=footer_text,
                object_id=self._generate_element_id(ElementType.FOOTER),
                position=(self.margins["left"], self.footer_y),
                size=(
                    self.slide_width - self.margins["left"] - self.margins["right"],
                    self.footer_height,
                ),
            )

            new_slide.elements.append(footer_element)

    def _add_content_elements(self, slide: Slide, content_groups: list[ContentGroup]) -> None:
        """Add content elements from groups to the slide."""
        for group in content_groups:
            for element in group.elements:
                # Deep copy to avoid modifying original
                copied_element = deepcopy(element)

                # Generate new object ID to avoid conflicts
                copied_element.object_id = self._generate_element_id(element.element_type)

                slide.elements.append(copied_element)

    def _create_continuation_title(self, original_title: str, slide_number: int) -> str:
        """Create title text for continuation slide."""
        if not original_title:
            return f"Content (cont. {slide_number})"

        # Remove existing continuation markers
        clean_title = original_title.replace("(cont.)", "").replace("(cont)", "").strip()

        return f"{clean_title} (cont.)"

    def _calculate_title_x(self, title_text: str) -> float:
        """Calculate X position for centered title."""
        # Estimate title width and center it
        char_width = 5.5  # Approximate character width for titles
        title_width = len(title_text) * char_width

        content_width = self.slide_width - self.margins["left"] - self.margins["right"]
        return self.margins["left"] + (content_width - title_width) / 2

    def _calculate_title_width(self, title_text: str) -> float:
        """Calculate width for title element."""
        char_width = 5.5
        return len(title_text) * char_width

    def _generate_element_id(self, element_type: ElementType) -> str:
        """Generate unique element ID."""
        type_prefix = {
            ElementType.TITLE: "title",
            ElementType.SUBTITLE: "subtitle",
            ElementType.TEXT: "text",
            ElementType.BULLET_LIST: "list",
            ElementType.ORDERED_LIST: "olist",
            ElementType.IMAGE: "img",
            ElementType.TABLE: "table",
            ElementType.CODE: "code",
            ElementType.QUOTE: "quote",
            ElementType.FOOTER: "footer",
        }.get(element_type, "elem")

        return f"{type_prefix}_{uuid.uuid4().hex[:8]}"
