"""Overflow detection and handling for slides."""

import logging
import uuid
from copy import deepcopy

from markdowndeck.models import (
    Element,
    ElementType,
    Slide,
    SlideLayout,
    TextElement,
)

logger = logging.getLogger(__name__)


class OverflowHandler:
    """Detects and handles overflow content using a fixed body zone model."""

    def __init__(self, slide_width: float, slide_height: float, margins: dict[str, float]):
        """
        Initialize the overflow handler with fixed body zone dimensions.

        Args:
            slide_width: Width of the slide in points
            slide_height: Height of the slide in points
            margins: Dictionary with margin values for top, right, bottom, left
        """
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins

        # OPTIMIZATION: Reduced vertical spacing to match PositionCalculator
        self.vertical_spacing = 8.0  # Reduced from 10.0

        # OPTIMIZATION: Fixed zone constants - MUST EXACTLY MATCH PositionCalculator
        self.HEADER_HEIGHT = 90.0  # Reduced from 100.0 to match PositionCalculator
        self.FOOTER_HEIGHT = 30.0

        # OPTIMIZATION: Calculate fixed body zone boundaries in EXACTLY the same way as PositionCalculator
        self.body_top = self.margins["top"] + self.HEADER_HEIGHT
        self.body_left = self.margins["left"]
        self.body_width = self.slide_width - self.margins["left"] - self.margins["right"]
        self.body_height = (
            self.slide_height - self.body_top - self.FOOTER_HEIGHT - self.margins["bottom"]
        )
        self.body_bottom = self.body_top + self.body_height

        logger.debug(
            f"Fixed body zone for overflow detection: top={self.body_top}, "
            f"bottom={self.body_bottom}, height={self.body_height}"
        )

    def has_overflow(self, slide: Slide) -> bool:
        """
        Check if any body elements overflow the slide's fixed body zone.

        Args:
            slide: The slide to check for overflow

        Returns:
            True if overflow is detected, False otherwise
        """
        # Use the fixed body zone boundary for bottom check
        body_bottom = self.body_bottom

        # Check each body element for overflow
        for element in self._get_body_elements(slide):
            if (
                not hasattr(element, "position")
                or not element.position
                or not hasattr(element, "size")
                or not element.size
            ):
                logger.warning(
                    f"Element {getattr(element, 'object_id', 'unknown')} type {element.element_type} lacks position/size for overflow check."
                )
                continue

            # Calculate element bottom
            element_bottom = element.position[1] + element.size[1]

            # Check if element extends beyond body zone
            if element_bottom > body_bottom + 1:  # 1 point tolerance
                logger.debug(
                    f"Overflow detected: Element {getattr(element, 'object_id', 'unknown')} ({element.element_type}) "
                    f"extends to y={element_bottom:.2f}, exceeding fixed body zone bottom at y={body_bottom:.2f}"
                )
                return True

        return False

    def handle_overflow(self, original_slide: Slide) -> list[Slide]:
        """
        Handle overflow by creating continuation slides as needed.
        Ensures all content stays within fixed body zones.

        Args:
            original_slide: The slide to handle overflow for

        Returns:
            List of slides (original slide plus any continuation slides)
        """
        logger.info(f"Handling overflow for slide: {original_slide.object_id}")

        result_slides = []
        remaining_elements = self._get_body_elements(original_slide)

        # Create first slide (with original header/footer)
        current_slide = self._create_base_slide(original_slide, is_first=True)
        result_slides.append(current_slide)

        # Process elements until all are placed
        while remaining_elements:
            # Always use the fixed body zone boundaries
            body_top = self.body_top
            body_bottom = self.body_bottom

            # Try to place elements in the current slide
            elements_to_place = []
            # OPTIMIZATION: Apply same adjustment as in zone_layout.py
            body_top_adjustment = 5.0
            current_y = body_top - body_top_adjustment

            # First analyze elements to identify logical groups that should stay together
            i = 0
            while i < len(remaining_elements):
                element = remaining_elements[i]

                # Check if this element is related to the next one
                keep_with_next = hasattr(element, "keep_with_next") and element.keep_with_next

                # If it's related and not the last element, calculate the combined height
                combined_height = 0
                group_elements = []

                if keep_with_next and i < len(remaining_elements) - 1:
                    # Start a new logical group
                    j = i
                    while j < len(remaining_elements):
                        current_element = remaining_elements[j]
                        if not hasattr(current_element, "size") or not current_element.size:
                            logger.warning(
                                f"Element {getattr(current_element, 'object_id', 'unknown')} has no size"
                            )
                            j += 1
                            continue

                        # Add this element to the current group
                        group_elements.append(current_element)
                        combined_height += current_element.size[1]

                        # Add spacing between elements
                        if j < len(remaining_elements) - 1:
                            combined_height += self.vertical_spacing

                        # Check if we should continue the group
                        keep_group_going = (
                            j < len(remaining_elements) - 1
                            and hasattr(current_element, "keep_with_next")
                            and current_element.keep_with_next
                        )

                        if not keep_group_going:
                            break

                        j += 1

                    # Move i to the end of the group
                    i = j + 1

                    # Check if the entire group fits
                    if current_y + combined_height <= body_bottom:
                        # If the group fits, add all its elements
                        for group_element in group_elements:
                            # Create a copy of the element for the new slide
                            copied_element = deepcopy(group_element)

                            # Update the position to the current y
                            if hasattr(copied_element, "position") and copied_element.position:
                                x_pos = copied_element.position[0]
                                copied_element.position = (x_pos, current_y)
                            else:
                                copied_element.position = (self.body_left, current_y)

                            # Add to elements to place
                            elements_to_place.append(copied_element)

                            # Update current_y for the next element
                            # OPTIMIZATION: Apply same spacing optimizations as in zone_layout.py
                            next_spacing = self.vertical_spacing
                            # Reduce spacing before related elements
                            if (
                                hasattr(copied_element, "related_to_next")
                                and copied_element.related_to_next
                            ):
                                next_spacing *= 0.7  # Reduce spacing by 30%

                            current_y += copied_element.size[1] + next_spacing

                        # Remove the spacing after the last element
                        if elements_to_place:
                            current_y -= self.vertical_spacing
                    else:
                        # Group doesn't fit, don't add anything and move to next slide
                        logger.debug(
                            f"Logical group of {len(group_elements)} elements doesn't fit "
                            f"(height={combined_height:.1f}, available={body_bottom - current_y:.1f}). "
                            f"Moving group to next slide."
                        )
                        break
                else:
                    # Handle individual element
                    if not hasattr(element, "size") or not element.size:
                        logger.warning(
                            f"Element {getattr(element, 'object_id', 'unknown')} has no size, cannot place in overflow."
                        )
                        i += 1
                        continue

                    element_height = element.size[1]

                    # Check if this element fits in the fixed body zone
                    if current_y + element_height <= body_bottom:
                        # Element fits - add it to this slide
                        copied_element = deepcopy(element)

                        # Preserve horizontal alignment but update vertical position
                        if hasattr(copied_element, "position") and copied_element.position:
                            x_pos = copied_element.position[0]
                            copied_element.position = (x_pos, current_y)
                        else:
                            # Default positioning if none exists
                            copied_element.position = (self.body_left, current_y)

                        elements_to_place.append(copied_element)

                        # OPTIMIZATION: Apply same spacing optimizations as in zone_layout.py
                        next_spacing = self.vertical_spacing
                        # Reduce spacing before related elements
                        if (
                            i < len(remaining_elements) - 1
                            and hasattr(element, "related_to_next")
                            and element.related_to_next
                        ):
                            next_spacing *= 0.7  # Reduce spacing by 30%

                        current_y += element_height + next_spacing
                    else:
                        # This element doesn't fit - keep for next slide
                        break

                    # Move to next element
                    i += 1

            # Add elements to current slide
            current_slide.elements.extend(elements_to_place)

            # Remove placed elements from remaining list
            if elements_to_place:
                remaining_elements = remaining_elements[len(elements_to_place) :]
                logger.debug(
                    f"Placed {len(elements_to_place)} elements on slide {current_slide.object_id}. "
                    f"{len(remaining_elements)} elements remaining."
                )
            else:
                # If element is clearly too large for a slide, reduce its size to ensure it can be placed
                # This is a safety mechanism to prevent infinite loops
                if remaining_elements:
                    logger.warning(
                        f"Element {getattr(remaining_elements[0], 'object_id', 'unknown')} appears too large "
                        f"for a single slide. Adjusting size to fit."
                    )
                    element = deepcopy(remaining_elements[0])

                    # More aggressive size reduction for oversized elements
                    max_height = self.body_bottom - self.body_top - 10  # 10 points buffer
                    if element.size[1] > max_height:
                        # Scale height while preserving aspect ratio if possible
                        if hasattr(element, "size") and element.size[0] > 0:
                            scale_factor = max_height / element.size[1]
                            # Preserve aspect ratio for images, tables, etc.
                            if element.element_type in [
                                ElementType.IMAGE,
                                ElementType.TABLE,
                                ElementType.CODE,
                            ]:
                                new_width = element.size[0] * scale_factor
                                element.size = (new_width, max_height)
                            else:
                                element.size = (element.size[0], max_height)
                        else:
                            element.size = (element.size[0], max_height)

                        logger.debug(f"Resized oversized element to fit: new height={max_height}")

                    # Position at top of body zone
                    if hasattr(element, "position") and element.position:
                        x_pos = element.position[0]
                        element.position = (x_pos, body_top)
                    else:
                        element.position = (self.body_left, body_top)

                    current_slide.elements.append(element)
                    remaining_elements = remaining_elements[1:]
                else:
                    # Should never happen, but just in case
                    break

            # If there are still elements to place, create a new continuation slide
            if remaining_elements:
                current_slide = self._create_base_slide(
                    original_slide,
                    is_first=False,
                    continuation_number=len(result_slides),
                )
                result_slides.append(current_slide)

        logger.info(
            f"Created {len(result_slides)} slides from original slide {original_slide.object_id}"
        )
        return result_slides

    def _create_base_slide(
        self, original_slide: Slide, is_first: bool, continuation_number: int = 0
    ) -> Slide:
        """
        Create a base slide with header and footer elements.

        Args:
            original_slide: The original slide to base the new slide on
            is_first: True if this is the first slide, False for continuation slides
            continuation_number: Number to use in the continuation slide ID

        Returns:
            A new slide with header and footer elements
        """
        # Create new slide object
        slide_id = original_slide.object_id
        if not is_first:
            slide_id = f"{original_slide.object_id}_cont_{continuation_number}"

        new_slide = Slide(
            object_id=slide_id,
            layout=original_slide.layout if is_first else SlideLayout.BLANK,
            notes=original_slide.notes,  # Keep notes for all slides
            background=original_slide.background,
            sections=[],  # No sections in continuation slides
            elements=[],
        )

        # Copy title/subtitle (first slide) or create continuation title
        title_el = original_slide.get_title_element()
        if title_el:
            if is_first:
                # Copy original title for first slide
                new_slide.elements.append(deepcopy(title_el))
            else:
                # Create continuation title
                cont_title = deepcopy(title_el)

                if isinstance(cont_title, TextElement):
                    # Make continuation title more identifiable
                    cont_title.text = f"{original_slide.title or 'Content'} (cont.)"

                # Assign a new ID to avoid conflicts
                cont_title.object_id = f"title_{uuid.uuid4().hex[:8]}"
                new_slide.elements.append(cont_title)

            # Set slide title
            if isinstance(new_slide.elements[0], TextElement):
                new_slide.title = new_slide.elements[0].text

        # Copy footer element
        footer_el = original_slide.get_footer_element()
        if footer_el:
            copied_footer = deepcopy(footer_el)
            # Assign a new ID to avoid conflicts
            copied_footer.object_id = f"footer_{uuid.uuid4().hex[:8]}"
            new_slide.elements.append(copied_footer)

            # Set slide footer text (without notes)
            if isinstance(copied_footer, TextElement):
                # Extract only the visible footer text, not notes
                footer_text = self._extract_footer_text(copied_footer.text)
                new_slide.footer = footer_text

        return new_slide

    def _get_body_elements(self, slide: Slide) -> list[Element]:
        """
        Get all elements that belong in the body zone (not title, subtitle, or footer).

        Args:
            slide: The slide to get body elements from

        Returns:
            List of body elements
        """
        return [
            element
            for element in slide.elements
            if element.element_type
            not in (ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER)
        ]

    def _extract_footer_text(self, full_footer_text: str) -> str:
        """
        Extract only the visible footer text, removing HTML comments.

        Args:
            full_footer_text: The complete footer text including notes

        Returns:
            Footer text without HTML comments
        """
        import re

        # Remove HTML comments (which contain speaker notes)
        clean_text = re.sub(r"<!--.*?-->", "", full_footer_text, flags=re.DOTALL)
        return clean_text.strip()
