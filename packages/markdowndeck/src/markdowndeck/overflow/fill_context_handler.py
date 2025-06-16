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

        # Determine the overflow scenario
        scenario = self._determine_overflow_scenario(
            slide.root_section, context_row, overflowing_element
        )
        logger.debug(f"[Fill Handler] Determined overflow scenario: {scenario}")

        if scenario == "atomic_move":
            return self._handle_atomic_move(slide, context_row, continuation_number)

        # REFACTORED: The 'excise and re-assemble' logic is complex and error-prone.
        # A simpler, more robust approach is to let the standard handler split the content,
        # then ensure the [fill] context is present on both the original and continuation slides.
        logger.debug(
            "[Fill Handler] Sibling/Outside Overflow: Using standard handler then re-applying context."
        )

        fitted_slide, continuation_slide = self.handler.handle_overflow(
            slide, overflowing_element, continuation_number
        )

        # Ensure the fitted slide still has the context row. The standard handler should preserve it.
        # This is more of a sanity check.
        if not self._find_context_row(fitted_slide.root_section):
            logger.warning(
                "[Fill Handler] Context row was lost from fitted slide during standard handling."
            )

        final_slides = [fitted_slide]
        if continuation_slide:
            # Re-create the continuation slide with the full context.
            # The standard handler's continuation only has the overflowing part.

            # 1. Deepcopy the original context row to use as a template.
            new_continuation_root = deepcopy(context_row)

            # 2. Find which column in the template to inject the overflowing content into.
            original_overflow_column_id = self._find_overflowing_column_id(
                slide.root_section, overflowing_element
            )

            content_injected = False
            if original_overflow_column_id:
                for col in new_continuation_root.children:
                    if (
                        isinstance(col, Section)
                        and col.id == original_overflow_column_id
                    ):
                        col.children = continuation_slide.root_section.children
                        content_injected = True
                        logger.debug(
                            f"[Fill Handler] Injected overflow content into matching column '{col.id}'."
                        )
                        break

            if not content_injected:
                # Fallback: inject into the first column that doesn't have a fill image.
                for col in new_continuation_root.children:
                    if isinstance(col, Section) and not self._has_fill_descendant(col):
                        col.children = continuation_slide.root_section.children
                        logger.debug(
                            f"[Fill Handler] Injected overflow content into fallback column '{col.id}'."
                        )
                        break

            continuation_slide.root_section = new_continuation_root
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
        except ValueError:
            logger.error(
                "[Fill Handler] Could not find context row in parent's children. Aborting."
            )
            self.manager._finalize_slide(slide)
            return [slide]

        # Create the fitted slide with content before the context row.
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
            return [slide]

        fitted_slide = deepcopy(slide)
        fitted_slide.root_section = fitted_root
        self.manager._finalize_slide(fitted_slide)
        logger.debug("[Fill Handler] Created fitted slide without the context row.")

        # Create the continuation slide with the context row and any subsequent siblings.
        overflowing_children = parent_section.children[split_index:]

        # If the overflowing content is just the context row itself, we can use it directly as the root.
        if (
            len(overflowing_children) == 1
            and overflowing_children[0].id == context_row.id
        ):
            continuation_root = deepcopy(context_row)
        else:
            continuation_root = Section(
                id=f"cont_root_{context_row.id}",
                type=parent_section.type,
                children=deepcopy(overflowing_children),
            )

        # CRITICAL FIX: Ensure the new root for the continuation slide has explicit
        # dimensions if it contains a [fill] image, to satisfy LayoutManager.
        if self._has_fill_descendant(continuation_root):
            if "width" not in continuation_root.directives:
                continuation_root.directives["width"] = "100%"
            if "height" not in continuation_root.directives:
                continuation_root.directives["height"] = "100%"
            logger.debug(
                f"[Fill Handler] CRITICAL: Ensured continuation root has width/height directives: {continuation_root.directives}"
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

    def _find_overflowing_column_id(
        self, root: "Section", overflowing_element: "Element"
    ) -> str | None:
        """Finds the ID of the column that is the direct parent of the overflowing element."""
        path = self.handler._find_path_to_parent(
            root, self.handler._get_node_id(overflowing_element)
        )
        if path:
            return path[-1].id
        return None

    def _find_section_by_id(
        self, root: "Section", section_id: str
    ) -> Optional["Section"]:
        """Find a section by ID within a tree."""
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
