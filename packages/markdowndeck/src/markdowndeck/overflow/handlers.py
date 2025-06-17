import logging
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Optional, Union, cast

if TYPE_CHECKING:
    from markdowndeck.models import Element, Slide

from markdowndeck.models import Section as SectionModel
from markdowndeck.models.constants import ElementType
from markdowndeck.models.elements.table import TableElement
from markdowndeck.models.slide import Section
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)

OVERFLOW_SAFETY_MARGIN = 5.0


class StandardOverflowHandler:
    """
    Handles overflow by partitioning the slide's content tree. This class uses a
    path-finding algorithm to locate the overflowing element and then non-destructively
    builds two new trees: one for the content that fits ('fitted') and one for the
    content that must move to a new slide ('continuation').
    """

    def __init__(self, slide_height: float, top_margin: float, bottom_margin: float):
        """Initializes the handler with the slide's vertical boundaries."""
        self.slide_height = slide_height
        self.top_margin = top_margin
        self.bottom_margin = bottom_margin

    def handle_overflow(
        self, slide: "Slide", overflowing_element: "Element", continuation_number: int
    ) -> tuple["Slide", "Slide | None"]:
        """
        Orchestrates the overflow handling process. This is the main entry point.
        """
        logger.debug(
            f"--- Overflow Handling Started for Element: {self._get_node_id(overflowing_element)} ---"
        )

        original_element_id = self._get_node_id(overflowing_element)
        if not original_element_id:
            temp_id = f"temp_overflow_{uuid.uuid4().hex[:8]}"
            overflowing_element.object_id = temp_id
            original_element_id = temp_id
            logger.debug(f"Assigned temporary ID to element: {temp_id}")

        available_height = self._calculate_available_height(slide, overflowing_element)
        available_height -= OVERFLOW_SAFETY_MARGIN
        logger.debug(
            f"Available height for splitting (with margin): {available_height:.2f}pt"
        )

        is_atomic = overflowing_element.element_type == ElementType.IMAGE
        if is_atomic:
            logger.debug(
                f"Element {self._get_node_id(overflowing_element)} is atomic. Bypassing split and moving whole element."
            )
            fitted_part, overflow_part = None, deepcopy(overflowing_element)
        else:
            fitted_part, overflow_part = self._split_element_safely(
                overflowing_element, available_height
            )

        if fitted_part and overflowing_element.position:
            fitted_part.position = overflowing_element.position

        if overflow_part:
            overflow_part._overflow_moved = True
        logger.debug(
            f"Element split result: has_fitted_part={bool(fitted_part)}, has_overflow_part={bool(overflow_part)}"
        )

        fitted_root = deepcopy(slide.root_section)

        path_to_parent = self._find_path_to_parent(fitted_root, original_element_id)
        if not path_to_parent:
            logger.error(
                f"FATAL: Could not find path to parent of overflowing element '{original_element_id}'. Aborting split."
            )
            return deepcopy(slide), None

        continuation_content = [overflow_part] if overflow_part else []

        for i in range(len(path_to_parent) - 1, -1, -1):
            parent_section = path_to_parent[i]
            child_node = (
                path_to_parent[i + 1]
                if i + 1 < len(path_to_parent)
                else overflowing_element
            )

            try:
                child_index = [
                    self._get_node_id(c) for c in parent_section.children
                ].index(self._get_node_id(child_node))
            except ValueError:
                logger.error(
                    f"Logic Error: Node {self._get_node_id(child_node)} not found in parent {self._get_node_id(parent_section)}. Aborting."
                )
                return deepcopy(slide), None

            siblings_to_move = parent_section.children[child_index + 1 :]
            continuation_content = siblings_to_move + continuation_content

            if self._get_node_id(child_node) == original_element_id:
                new_children = parent_section.children[:child_index]
                if fitted_part:
                    new_children.append(fitted_part)
                parent_section.children = new_children
            else:
                parent_section.children = parent_section.children[: child_index + 1]

        continuation_content.reverse()

        logger.debug(
            f"Partitioning complete. Continuation has {len(continuation_content)} items."
        )

        fitted_slide = deepcopy(slide)
        fitted_slide.root_section = fitted_root

        continuation_slide = None
        if any(c is not None for c in continuation_content):
            slide_builder = SlideBuilder(slide)
            new_continuation_root = Section(
                id="cont_root", children=continuation_content
            )
            continuation_slide = slide_builder.create_continuation_slide(
                new_continuation_root, continuation_number
            )
            logger.debug("Continuation slide created.")
        else:
            logger.debug(
                "No continuation content, so no continuation slide will be created."
            )

        logger.debug("--- Overflow Handling Finished ---")
        return fitted_slide, continuation_slide

    def _get_node_id(self, node: Union[Section, "Element"]) -> str | None:
        """Safely gets the unique ID of a Section (.id) or an Element (.object_id)."""
        # REFACTORED: This is the new helper method to fix path-finding.
        if node is None:
            return None
        return getattr(node, "id", getattr(node, "object_id", None))

    def _find_path_to_parent(
        self, root: Section, target_id: str
    ) -> list[Section] | None:
        """
        Performs a DFS to find the path of Sections leading to the target's parent.
        Returns the list of sections, e.g., [root, child_section, grandchild_section].
        """
        # REFACTORED: This method now uses the _get_node_id helper.
        if not target_id:
            return None

        path_stack: list[Section] = []

        def find_recursive(section: Section) -> bool:
            path_stack.append(section)
            for child in section.children:
                if self._get_node_id(child) == target_id:
                    return True
                if isinstance(child, SectionModel) and find_recursive(child):
                    return True
            path_stack.pop()
            return False

        if find_recursive(root):
            return path_stack
        return None

    def _calculate_available_height(self, slide: "Slide", element: "Element") -> float:
        """Calculates the remaining vertical space from the element's top to the slide's bottom margin."""
        _start_y, end_y = self._calculate_body_boundaries(slide)
        element_top = element.position[1] if element.position else end_y
        return max(0, end_y - element_top)

    def _calculate_body_boundaries(self, slide: "Slide") -> tuple[float, float]:
        """Calculates the absolute y-coordinates for the top and bottom of the main content area."""
        from markdowndeck.layout.constants import HEADER_TO_BODY_SPACING

        top_offset = self.top_margin
        header_bottom = self.top_margin

        title = slide.get_title_element()
        if title and title.position and title.size:
            header_bottom = max(header_bottom, title.position[1] + title.size[1])

        subtitle = slide.get_subtitle_element()
        if subtitle and subtitle.position and subtitle.size:
            header_bottom = max(header_bottom, subtitle.position[1] + subtitle.size[1])

        if header_bottom > self.top_margin:
            top_offset = header_bottom + HEADER_TO_BODY_SPACING

        body_end_y = self.slide_height - self.bottom_margin
        footer = slide.get_footer_element()
        if footer and footer.position and footer.size:
            body_end_y = min(body_end_y, footer.position[1])

        return top_offset, body_end_y

    def _split_element_safely(
        self, element: "Element", height: float
    ) -> tuple[Optional["Element"], Optional["Element"]]:
        """Safely calls the element's split method and handles table header duplication."""
        if not callable(getattr(element, "split", None)):
            return None, deepcopy(element)
        try:
            fitted, overflow = element.split(height)
            if (
                element.element_type == ElementType.TABLE
                and overflow
                and isinstance(overflow, TableElement)
            ):
                original = cast(TableElement, element)
                if original.headers and not overflow.headers:
                    overflow.headers = deepcopy(original.headers)
                    if original.row_directives:
                        overflow.row_directives.insert(
                            0, deepcopy(original.row_directives[0])
                        )
            return fitted, overflow
        except Exception as e:
            logger.error(
                f"Error splitting {self._get_node_id(element)}: {e}", exc_info=True
            )
            return None, deepcopy(element)
