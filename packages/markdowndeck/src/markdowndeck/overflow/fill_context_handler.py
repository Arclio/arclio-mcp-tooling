import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from markdowndeck.models import Element, Slide
    from markdowndeck.overflow.manager import OverflowManager

from markdowndeck.models.slide import Section
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)


class FillContextOverflowHandler:
    """
    Implements the specialized "excise and replace" and "atomic move" overflow
    algorithms for slides containing a `[fill]` image, as per OVERFLOW_SPEC.md Rule #9.
    """

    def __init__(self, overflow_manager: "OverflowManager"):
        self.manager = overflow_manager
        self.handler = overflow_manager.handler

    def handle(
        self, slide: "Slide", overflowing_element: "Element", continuation_number: int
    ) -> list["Slide"]:
        """Main entry point for handling fill context overflow."""
        logger.debug(
            f"[Fill Handler] Starting for slide {slide.object_id} with overflowing element {self.handler._get_node_id(overflowing_element)}"
        )

        context_row = self._find_context_row(slide.root_section)
        if not context_row:
            logger.warning(
                "[Fill Handler] No [fill] context row found. Falling back to standard handler."
            )
            return self._fallback_to_standard_handler(
                slide, overflowing_element, continuation_number
            )

        logger.debug(f"[Fill Handler] Found context row: {context_row.id}")

        scenario = self._determine_overflow_scenario(
            slide.root_section, context_row, overflowing_element
        )
        logger.debug(f"[Fill Handler] Determined overflow scenario: {scenario}")

        if scenario == "atomic_move":
            return self._handle_atomic_move(slide, context_row, continuation_number)

        logger.debug(
            "[Fill Handler] Sibling/Outside Overflow: Using standard handler then re-applying context."
        )
        # REFACTORED: This is a simplified but more robust way to handle sibling overflow.
        # We perform a standard split, then re-insert the context into the continuation.
        fitted_slide, continuation_slide = self.handler.handle_overflow(
            slide, overflowing_element, continuation_number
        )

        final_slides = [fitted_slide]
        if continuation_slide:
            # Deepcopy the original context row to put into the new slide.
            new_context_row = deepcopy(context_row)
            # The continuation slide's root has the overflowing content.
            # We need to wrap it back into a structure that includes the context.
            overflowing_content_root = continuation_slide.root_section

            # Find the original parent of the context row.
            original_parent_path = self.handler._find_path_to_parent(
                slide.root_section, context_row.id
            )
            if original_parent_path:
                original_parent = original_parent_path[-1]
                # Re-create a simplified version of the original parent to hold the context and overflow content
                new_parent = Section(
                    id=f"cont_{original_parent.id}",
                    type=original_parent.type,
                    children=[new_context_row, overflowing_content_root],
                )
                continuation_slide.root_section = new_parent
            else:
                # Fallback if parent not found: just put context and overflow side-by-side
                continuation_slide.root_section = Section(
                    id="cont_root",
                    type="section",
                    children=[new_context_row, overflowing_content_root],
                )

            repositioned_continuation = self.manager.layout_manager.calculate_positions(
                continuation_slide
            )
            final_slides.extend(self.manager.process_slide(repositioned_continuation))

        self.manager._finalize_slide(fitted_slide)
        return final_slides

    def _determine_overflow_scenario(
        self,
        root_section: "Section",
        context_row: "Section",
        overflowing_element: "Element",
    ) -> str:
        """Determines if the overflow is atomic, in a sibling, or outside the context row."""
        path_to_overflow = self.handler._find_path_to_parent(
            root_section, self.handler._get_node_id(overflowing_element)
        )
        if not path_to_overflow:
            return "outside"

        if any(node.id == context_row.id for node in path_to_overflow):
            return "atomic_move"

        return "sibling_overflow"

    def _handle_atomic_move(
        self, slide: "Slide", context_row: "Section", continuation_number: int
    ) -> list["Slide"]:
        """Handles the atomic move of an entire context row to a new slide."""
        logger.debug(
            f"[Fill Handler] Executing Atomic Move for row '{context_row.id}'."
        )

        path_to_parent = self.handler._find_path_to_parent(
            slide.root_section, context_row.id
        )
        if not path_to_parent:
            logger.error(
                f"[Fill Handler] Could not find parent of context row '{context_row.id}'. Aborting."
            )
            self.manager._finalize_slide(slide)
            return [slide]

        parent_section = path_to_parent[-1]
        try:
            child_ids = [self.handler._get_node_id(c) for c in parent_section.children]
            split_index = child_ids.index(context_row.id)
        except (ValueError, AttributeError):
            logger.error(
                "[Fill Handler] Could not find context row in parent's children. Aborting."
            )
            self.manager._finalize_slide(slide)
            return [slide]

        fitted_root = deepcopy(slide.root_section)
        parent_in_fitted_tree = self._find_section_by_id(fitted_root, parent_section.id)
        if parent_in_fitted_tree:
            parent_in_fitted_tree.children = parent_in_fitted_tree.children[
                :split_index
            ]
        else:
            logger.error(
                "[Fill Handler] Failed to find parent in deepcopied fitted tree."
            )
            self.manager._finalize_slide(slide)
            return [slide]

        fitted_slide = deepcopy(slide)
        fitted_slide.root_section = fitted_root
        self.manager._finalize_slide(fitted_slide)
        logger.debug("[Fill Handler] Created fitted slide without the context row.")

        overflowing_children = parent_section.children[split_index:]
        continuation_root = Section(
            id=f"cont_root_{context_row.id}",
            type=parent_section.type,
            children=deepcopy(overflowing_children),
        )

        slide_builder = SlideBuilder(slide)
        continuation_slide = slide_builder.create_continuation_slide(
            continuation_root, continuation_number
        )

        repositioned_continuation = self.manager.layout_manager.calculate_positions(
            continuation_slide
        )

        return [fitted_slide] + self.manager.process_slide(repositioned_continuation)

    def _find_context_row(self, section: "Section") -> Optional["Section"]:
        """Find the row section containing a [fill] image."""
        if not section:
            return None
        if section.type == "row" and self._has_fill_descendant(section):
            return section
        for child in section.children:
            if isinstance(child, Section):
                found = self._find_context_row(child)
                if found:
                    return found
        return None

    def _has_fill_descendant(self, section: "Section") -> bool:
        """Check if a section contains any [fill] image in its hierarchy."""
        for child in section.children:
            if isinstance(child, Section):
                if self._has_fill_descendant(child):
                    return True
            elif (
                hasattr(child, "element_type")
                and child.element_type.value == "image"
                and child.directives.get("fill")
            ):
                return True
        return False

    def _find_section_by_id(
        self, root: "Section", section_id: str
    ) -> Optional["Section"]:
        """Find a section by ID within a tree."""
        if not root or not section_id:
            return None
        if root.id == section_id:
            return root
        for child in root.children:
            if isinstance(child, Section):
                found = self._find_section_by_id(child, section_id)
                if found:
                    return found
        return None

    def _fallback_to_standard_handler(
        self, slide: "Slide", element: "Element", num: int
    ) -> list["Slide"]:
        """Fallback to standard overflow handling."""
        logger.debug("[Fill Handler] Falling back to standard overflow handler.")
        fitted, cont = self.handler.handle_overflow(slide, element, num)
        self.manager._finalize_slide(fitted)
        final = [fitted]
        if cont:
            re_pos = self.manager.layout_manager.calculate_positions(cont)
            final.extend(self.manager.process_slide(re_pos))
        return final
