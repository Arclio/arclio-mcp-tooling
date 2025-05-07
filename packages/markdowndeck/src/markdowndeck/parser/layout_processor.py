import logging

from ..models import Element, ElementType, SlideLayout

logger = logging.getLogger(__name__)


class LayoutProcessor:
    """Process layout information for slides and sections."""

    def __init__(self):
        """Initialize the layout processor."""
        # Slide dimensions (in points)
        self.slide_width = 720
        self.slide_height = 405

        # Default margins
        self.margins = {
            "top": 50,
            "right": 50,
            "bottom": 50,
            "left": 50,
        }

        # Default spacing
        self.spacing = {
            "vertical": 20,  # Spacing between vertical sections
            "horizontal": 10,  # Spacing between horizontal sections
        }

    def calculate_implicit_dimensions(self, sections: list[dict]) -> None:
        """
        Calculate implicit widths and heights for sections.

        Args:
            sections: List of section dictionaries to be modified in-place
        """
        logger.debug("Calculating implicit dimensions for sections")

        # Handle horizontal sections (row sections with subsections)
        for section in sections:
            if section["type"] == "row" and section.get("subsections"):
                self._calculate_implicit_widths(section["subsections"])
                logger.debug(f"Calculated widths for row section: {section['id']}")

        # Handle vertical sections (implicit heights)
        self._calculate_implicit_heights(sections)
        logger.debug("Calculated heights for all sections")

    def _calculate_implicit_widths(self, sections: list[dict]) -> None:
        """
        Calculate widths for horizontal sections when not all have explicit widths.

        Args:
            sections: List of section dictionaries to be modified in-place
        """
        # Find sections with explicit and implicit widths
        explicit_sections = [s for s in sections if "width" in s["directives"]]
        implicit_sections = [s for s in sections if "width" not in s["directives"]]

        if not implicit_sections:
            logger.debug("No implicit width sections to calculate")
            return

        # Calculate total explicit width
        total_explicit_width = sum(float(s["directives"]["width"]) for s in explicit_sections)

        # Keep width within valid range
        total_explicit_width = min(1.0, max(0.0, total_explicit_width))

        # Calculate remaining width for implicit sections
        remaining_width = 1.0 - total_explicit_width

        # Distribute remaining width equally
        if remaining_width > 0 and implicit_sections:
            implicit_width = remaining_width / len(implicit_sections)
            for section in implicit_sections:
                section["directives"]["width"] = implicit_width
                logger.debug(
                    f"Assigned implicit width {implicit_width:.2f} to section {section['id']}"
                )
        else:
            # Handle case when total exceeds 1.0 or no remaining width
            for section in implicit_sections:
                section["directives"]["width"] = 0.0
                logger.debug(f"Assigned zero width to section {section['id']} (no remaining space)")

    def _calculate_implicit_heights(self, sections: list[dict]) -> None:
        """
        Calculate heights for vertical sections when not all have explicit heights.

        Args:
            sections: List of section dictionaries to be modified in-place
        """
        # Find sections with explicit and implicit heights
        explicit_sections = [s for s in sections if "height" in s["directives"]]
        implicit_sections = [s for s in sections if "height" not in s["directives"]]

        if not implicit_sections:
            logger.debug("No implicit height sections to calculate")
            return

        # Calculate total explicit height
        total_explicit_height = sum(float(s["directives"]["height"]) for s in explicit_sections)

        # Keep height within valid range
        total_explicit_height = min(1.0, max(0.0, total_explicit_height))

        # Calculate remaining height for implicit sections
        remaining_height = 1.0 - total_explicit_height

        # Distribute remaining height based on estimated content size
        if remaining_height > 0 and implicit_sections:
            # Estimate content size based on content length as a heuristic
            content_sizes = [
                self._estimate_content_size(s.get("content", "")) for s in implicit_sections
            ]
            total_content_size = sum(content_sizes) or 1  # Avoid division by zero

            # Assign heights proportionally
            for i, section in enumerate(implicit_sections):
                proportion = content_sizes[i] / total_content_size
                section["directives"]["height"] = remaining_height * proportion
                logger.debug(
                    f"Assigned implicit height {section['directives']['height']:.2f} to section {section['id']}"
                )
        else:
            # Handle case when total exceeds 1.0 or no remaining height
            for section in implicit_sections:
                section["directives"]["height"] = 0.0
                logger.debug(
                    f"Assigned zero height to section {section['id']} (no remaining space)"
                )

    def _estimate_content_size(self, content: str) -> float:
        """
        Estimate the relative size of content based on length and structure.

        Args:
            content: Section content

        Returns:
            Estimated relative size
        """
        # Base size on content length with adjustments for certain types
        size = len(content) or 1  # Minimum size

        # Increase size for code blocks and tables (they need more space)
        if "```" in content:
            code_blocks = content.count("```") // 2
            size += code_blocks * 100  # Add extra size for code blocks

        if "|" in content and "-|-" in content:
            # Likely a table
            rows = content.count("\n")
            size += rows * 30  # Add extra size for tables

        # Lists take more space
        list_items = content.count("\n* ") + content.count("\n- ") + content.count("\n1. ")
        size += list_items * 20

        return size

    def determine_layout(self, elements: list[Element | dict]) -> SlideLayout:
        """
        Determine the most appropriate slide layout based on elements.

        Args:
            elements: List of slide elements (either Element objects or dicts for testing)

        Returns:
            The determined slide layout
        """

        # Handle both Element objects and test dictionaries
        def get_element_type(e):
            if hasattr(e, "element_type"):
                return e.element_type
            if isinstance(e, dict) and "element_type" in e:
                return e["element_type"]
            return None

        # Count element types
        has_title = any(get_element_type(e) == ElementType.TITLE for e in elements)
        has_subtitle = any(get_element_type(e) == ElementType.SUBTITLE for e in elements)
        has_image = any(get_element_type(e) == ElementType.IMAGE for e in elements)
        has_table = any(get_element_type(e) == ElementType.TABLE for e in elements)
        has_list = any(
            get_element_type(e) in (ElementType.BULLET_LIST, ElementType.ORDERED_LIST)
            for e in elements
        )
        has_code = any(get_element_type(e) == ElementType.CODE for e in elements)

        logger.debug(
            f"Determining layout: title={has_title}, subtitle={has_subtitle}, "
            f"image={has_image}, table={has_table}, list={has_list}, code={has_code}"
        )

        # Determine layout based on content
        if has_title:
            if has_subtitle and not has_image and not has_table and not has_list and not has_code:
                return SlideLayout.TITLE
            if has_subtitle and (has_list or has_table or has_code):
                return SlideLayout.TITLE_AND_BODY
            if has_image and not (has_list or has_table or has_code):
                return SlideLayout.CAPTION_ONLY
            if not has_subtitle and (has_list or has_table or has_code):
                return SlideLayout.TITLE_AND_BODY
            return SlideLayout.TITLE_ONLY

        # Default to blank layout if no title
        logger.debug(f"Selected layout: {SlideLayout.BLANK}")
        return SlideLayout.BLANK

    def calculate_section_positions(
        self, sections: list[dict], content_area: tuple[float, float, float, float]
    ) -> list[dict]:
        """
        Calculate positions for sections based on directives and content area.

        Args:
            sections: List of section dictionaries
            content_area: Tuple of (left, top, width, height) defining content area

        Returns:
            Updated list of section dictionaries
        """
        logger.debug("Calculating section positions")

        # Unpack content area
        left, top, width, height = content_area

        # Handle section positions
        current_y = top

        for section in sections:
            if section["type"] == "row":
                # Position row with subsections
                row_height = height * float(
                    section["directives"].get("height", 1.0 / len(sections))
                )
                self._position_row_sections(
                    section["subsections"], (left, current_y, width, row_height)
                )

                # Update section position
                section["position"] = (left, current_y)
                section["size"] = (width, row_height)

                # Advance vertical position
                current_y += row_height + self.spacing["vertical"]
            else:
                # Single column section
                section_height = height * float(
                    section["directives"].get("height", 1.0 / len(sections))
                )
                section["position"] = (left, current_y)
                section["size"] = (width, section_height)

                # Advance vertical position
                current_y += section_height + self.spacing["vertical"]

        return sections

    def _position_row_sections(
        self, sections: list[dict], row_area: tuple[float, float, float, float]
    ) -> None:
        """
        Position sections within a row.

        Args:
            sections: List of section dictionaries
            row_area: Tuple of (left, top, width, height) defining row area
        """
        # Unpack row area
        left, top, width, height = row_area

        # Calculate positions for each section in the row
        current_x = left

        for section in sections:
            # Calculate section width
            section_width = width * float(section["directives"].get("width", 1.0 / len(sections)))

            # Set position and size
            section["position"] = (current_x, top)
            section["size"] = (section_width, height)

            # Advance horizontal position
            current_x += section_width + self.spacing["horizontal"]
