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

        context_container = self._find_context_container(slide.root_section)
        if not context_container:
            logger.warning(
                "[Fill Handler] No [fill] context container found. Falling back to standard handler."
            )
            return self._fallback_to_standard_handler(
                slide, overflowing_element, continuation_number
            )

        logger.debug(f"[Fill Handler] Found context container: {context_container.id}")

        scenario = self._determine_overflow_scenario(
            slide.root_section, context_container, overflowing_element
        )
        logger.debug(f"[Fill Handler] Determined overflow scenario: {scenario}")

        if scenario == "atomic_move":
            return self._handle_atomic_move(
                slide, context_container, continuation_number
            )

        logger.debug(
            "[Fill Handler] Sibling/Outside Overflow: Using standard handler then re-applying context."
        )

        # Per OVERFLOW_SPEC.md Rule #9.B: Implement "remove, process, re-assemble" algorithm

        # Step 1: Isolate Context - Remove the context container from the slide structure
        modified_slide = self._isolate_context_container(slide, context_container)

        # Step 2: Delegate Content Processing - Process only the remaining content
        if modified_slide.root_section and self._has_content_to_process(
            modified_slide.root_section
        ):
            # Process the modified slide (without context) using standard overflow logic
            fitted_slide, continuation_slide = self.handler.handle_overflow(
                modified_slide, overflowing_element, continuation_number
            )
        else:
            # No content to process - everything fits
            fitted_slide = modified_slide
            continuation_slide = None

        # Step 3: Re-assemble Fitted Slide - Combine original context container with fitted content
        reassembled_fitted_slide = self._reassemble_fitted_slide(
            slide, context_container, fitted_slide
        )

        # Re-position the reassembled fitted slide since we modified its structure
        repositioned_fitted_slide = self.manager.layout_manager.calculate_positions(
            reassembled_fitted_slide
        )

        final_slides = [repositioned_fitted_slide]

        # Step 4: Re-assemble Continuation Slide - If overflow exists, duplicate context
        if continuation_slide:
            reassembled_continuation_slide = self._reassemble_continuation_slide(
                slide, context_container, continuation_slide
            )

            # Process the reassembled continuation slide
            repositioned_continuation = self.manager.layout_manager.calculate_positions(
                reassembled_continuation_slide
            )
            final_slides.extend(self.manager.process_slide(repositioned_continuation))

        self.manager._finalize_slide(repositioned_fitted_slide)
        return final_slides

    def _determine_overflow_scenario(
        self,
        root_section: "Section",
        context_container: "Section",
        overflowing_element: "Element",
    ) -> str:
        """Determines if the overflow is atomic, in a sibling, or outside the context container."""
        path_to_overflow = self.handler._find_path_to_parent(
            root_section, self.handler._get_node_id(overflowing_element)
        )
        if not path_to_overflow:
            return "outside"

        if any(node.id == context_container.id for node in path_to_overflow):
            return "atomic_move"

        return "sibling_overflow"

    def _handle_atomic_move(
        self, slide: "Slide", context_container: "Section", continuation_number: int
    ) -> list["Slide"]:
        """Handles the atomic move of an entire context container to a new slide."""
        logger.debug(
            f"[Fill Handler] Executing Atomic Move for container '{context_container.id}'."
        )

        path_to_parent = self.handler._find_path_to_parent(
            slide.root_section, context_container.id
        )
        if not path_to_parent:
            logger.error(
                f"[Fill Handler] Could not find parent of context container '{context_container.id}'. Aborting."
            )
            self.manager._finalize_slide(slide)
            return [slide]

        parent_section = path_to_parent[-1]
        try:
            child_ids = [self.handler._get_node_id(c) for c in parent_section.children]
            split_index = child_ids.index(context_container.id)
        except (ValueError, AttributeError):
            logger.error(
                "[Fill Handler] Could not find context container in parent's children. Aborting."
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
        logger.debug(
            "[Fill Handler] Created fitted slide without the context container."
        )

        overflowing_children = parent_section.children[split_index:]
        continuation_root = Section(
            id=f"cont_root_{context_container.id}",
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

    def _find_context_container(self, section: "Section") -> Optional["Section"]:
        """Find the container section containing a [fill] image.

        Per OVERFLOW_SPEC.md Rule #9.B: The context container is the Section
        that directly holds the [fill] image.
        """
        if not section:
            return None

        # Check if this section directly contains a [fill] image as a child
        for child in section.children:
            if (
                hasattr(child, "element_type")
                and child.element_type.value == "image"
                and child.directives.get("fill")
            ):
                # This section directly contains a [fill] image
                return section

        # Recursively search in child sections
        for child in section.children:
            if isinstance(child, Section):
                found = self._find_context_container(child)
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

    def _find_context_parent_structure(
        self, root: "Section", context_container: "Section"
    ) -> list["Section"] | None:
        """Find the path to the parent structure of the context container."""
        if not root or not context_container:
            return None

        # Check if any direct child is the context container
        for child in root.children:
            if isinstance(child, Section) and child.id == context_container.id:
                # Found the parent - return the path to it
                return [root]
            if isinstance(child, Section):
                # Recursively search in child sections
                path = self._find_context_parent_structure(child, context_container)
                if path is not None:
                    return [root] + path
        return None

    def _recreate_parent_structure(
        self,
        context_parent_path: list["Section"],
        duplicated_context_container: "Section",
        overflowing_content_root: "Section",
    ) -> "Section":
        """Recreate the parent structure to maintain the original layout."""
        if not context_parent_path:
            # Fallback: create a simple container
            return Section(
                id="cont_root_fallback",
                type="row",
                children=[duplicated_context_container, overflowing_content_root],
            )

        # Use the immediate parent structure to maintain layout
        immediate_parent = context_parent_path[0]
        return Section(
            id=f"cont_{immediate_parent.id}",
            type=immediate_parent.type,
            directives=deepcopy(immediate_parent.directives),
            children=[duplicated_context_container, overflowing_content_root],
        )

    def _isolate_context_container(
        self, slide: "Slide", context_container: "Section"
    ) -> "Slide":
        """Isolate the context container from the slide structure."""
        modified_slide = deepcopy(slide)
        modified_slide.root_section.children = [
            child
            for child in modified_slide.root_section.children
            if child.id != context_container.id
        ]
        return modified_slide

    def _has_content_to_process(self, section: "Section") -> bool:
        """Check if a section contains any content to process."""
        for child in section.children:
            if isinstance(child, Section):
                if self._has_content_to_process(child):
                    return True
            elif hasattr(child, "element_type") and child.element_type.value != "image":
                return True
        return False

    def _reassemble_fitted_slide(
        self,
        original_slide: "Slide",
        context_container: "Section",
        fitted_slide: "Slide",
    ) -> "Slide":
        """Reassemble the fitted slide with the original context container."""
        reassembled_slide = deepcopy(fitted_slide)

        # Insert the original context container at the beginning to preserve layout
        if reassembled_slide.root_section is None:
            # Create a new root section if none exists
            reassembled_slide.root_section = Section(
                id=f"reassembled_{original_slide.object_id}",
                type=original_slide.root_section.type,
                directives=deepcopy(original_slide.root_section.directives),
                children=[context_container],
            )
        else:
            reassembled_slide.root_section.children.insert(0, context_container)

        return reassembled_slide

    def _reassemble_continuation_slide(
        self,
        original_slide: "Slide",
        context_container: "Section",
        continuation_slide: "Slide",
    ) -> "Slide":
        """Reassemble the continuation slide with a duplicated context container.

        Per OVERFLOW_SPEC.md Rule #9.B.4.a: Perform a deepcopy of the original
        "context container" (including its width and height directives).
        """
        reassembled_slide = deepcopy(continuation_slide)

        # Per Rule #9.B.4.a: Perform a deepcopy of the original context container
        # including its width and height directives
        duplicated_context_container = deepcopy(context_container)

        # The continuation slide's root contains the overflowing content, but we need to
        # preserve the original structure. Find the original parent structure to maintain layout.
        if reassembled_slide.root_section is None:
            # Create a new root section that matches the original structure
            reassembled_slide.root_section = Section(
                id=f"cont_{original_slide.object_id}",
                type=original_slide.root_section.type,
                directives=deepcopy(original_slide.root_section.directives),
                children=[duplicated_context_container],
            )
        else:
            # We need to reconstruct the original section structure for the overflowing content
            # Find which section in the original slide contained the overflowing content
            original_content_containers = [
                child
                for child in original_slide.root_section.children
                if child.id != context_container.id
            ]

            if original_content_containers:
                # Create new sections for the overflowing content that preserve structure
                reconstructed_content_sections = []
                for original_content_container in original_content_containers:
                    # Create a copy of the original container but with overflowing content
                    reconstructed_container = Section(
                        id=original_content_container.id,
                        type=original_content_container.type,
                        directives=deepcopy(original_content_container.directives),
                        children=reassembled_slide.root_section.children,  # The overflowing elements
                    )
                    reconstructed_content_sections.append(reconstructed_container)

                # Create the full structure with context and reconstructed content sections
                reassembled_slide.root_section = Section(
                    id=f"cont_{original_slide.object_id}",
                    type=original_slide.root_section.type,
                    directives=deepcopy(original_slide.root_section.directives),
                    children=[duplicated_context_container]
                    + reconstructed_content_sections,
                )
            else:
                # Fallback: just prepend the context container
                reassembled_slide.root_section.children.insert(
                    0, duplicated_context_container
                )

        return reassembled_slide
