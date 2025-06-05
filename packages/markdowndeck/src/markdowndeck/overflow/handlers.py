"""Overflow handling strategies for content distribution."""

import logging

from markdowndeck.models import Slide
from markdowndeck.overflow.models import ContentGroup, DistributionPlan, OverflowInfo
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)


class StandardOverflowHandler:
    """
    Standard overflow handling strategy.

    Implements intelligent content distribution with:
    - Respect for element relationships
    - Smart content grouping
    - Optimal slide utilization
    - Clean continuation slide creation
    """

    def __init__(
        self,
        slide_width: float = 720,
        slide_height: float = 405,
        margins: dict[str, float] = None,
    ):
        """
        Initialize standard overflow handler.

        Args:
            slide_width: Width of slides in points
            slide_height: Height of slides in points
            margins: Slide margins
        """
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins or {"top": 50, "right": 50, "bottom": 50, "left": 50}

        # Calculate available body height for content distribution
        header_height = 90.0
        footer_height = 30.0
        self.body_height = slide_height - margins["top"] - margins["bottom"] - header_height - footer_height

        # Initialize slide builder
        self.slide_builder = SlideBuilder(slide_width=slide_width, slide_height=slide_height, margins=margins)

        logger.debug(f"StandardOverflowHandler initialized - {self.body_height}pt body height available")

    def handle_overflow(self, slide: Slide, overflow_info: OverflowInfo) -> list[Slide]:
        """
        Handle overflow by distributing content across multiple slides.

        Args:
            slide: Original slide with overflow
            overflow_info: Overflow analysis details

        Returns:
            List of slides with content properly distributed
        """
        logger.info(f"Handling overflow for slide {slide.object_id}")

        # Step 1: Analyze content groups
        from markdowndeck.overflow.detector import OverflowDetector

        detector = OverflowDetector(self.slide_width, self.slide_height, self.margins)
        content_groups = detector.analyze_content_groups(slide)

        if not content_groups:
            logger.warning("No content groups found - returning original slide")
            return [slide]

        # Step 2: Create distribution plan
        distribution_plan = self._create_distribution_plan(content_groups)

        # Step 3: Build slides from distribution plan
        result_slides = self._build_slides_from_plan(slide, distribution_plan)

        logger.info(f"Overflow handling complete: {len(result_slides)} slides created")
        return result_slides

    def _create_distribution_plan(self, content_groups: list[ContentGroup]) -> DistributionPlan:
        """
        Create a plan for distributing content groups across slides.

        Args:
            content_groups: Groups of related content

        Returns:
            Distribution plan with groups assigned to slides
        """
        logger.debug(f"Creating distribution plan for {len(content_groups)} content groups")

        slides = []
        current_slide_groups = []
        current_slide_height = 0.0

        # Reserve some space for spacing between groups
        spacing_per_group = 10.0
        usable_height = self.body_height - (len(content_groups) * spacing_per_group)

        for group in content_groups:
            group_height = group.total_height

            # Check if group fits in current slide
            if current_slide_height + group_height <= usable_height and current_slide_groups:  # Not the first group
                # Add to current slide
                current_slide_groups.append(group)
                current_slide_height += group_height
                logger.debug(f"Added group to current slide (height now: {current_slide_height:.1f})")

            else:
                # Start new slide
                if current_slide_groups:
                    slides.append(current_slide_groups)
                    logger.debug(f"Completed slide with {len(current_slide_groups)} groups")

                current_slide_groups = [group]
                current_slide_height = group_height

                # Handle oversized groups
                if group_height > usable_height:
                    logger.warning(f"Group exceeds slide capacity ({group_height:.1f} > {usable_height:.1f})")
                    # For now, still place it - future enhancement could split large groups

        # Add final slide if it has content
        if current_slide_groups:
            slides.append(current_slide_groups)
            logger.debug(f"Added final slide with {len(current_slide_groups)} groups")

        return DistributionPlan(slides=slides)

    def _build_slides_from_plan(self, original_slide: Slide, plan: DistributionPlan) -> list[Slide]:
        """
        Build actual slides from the distribution plan.

        Args:
            original_slide: Original slide to base new slides on
            plan: Distribution plan

        Returns:
            List of constructed slides
        """
        logger.debug(f"Building {plan.total_slides} slides from distribution plan")

        result_slides = []

        for slide_index, slide_groups in enumerate(plan.slides):
            is_first_slide = slide_index == 0

            # Create slide
            if is_first_slide:
                # First slide keeps original title and structure
                new_slide = self.slide_builder.create_first_slide(original_slide, slide_groups)
            else:
                # Continuation slides get modified titles
                new_slide = self.slide_builder.create_continuation_slide(original_slide, slide_groups, slide_index)

            # Position elements within the slide
            self._position_slide_elements(new_slide, slide_groups)

            result_slides.append(new_slide)
            logger.debug(f"Built slide {slide_index + 1} with {len(slide_groups)} content groups")

        return result_slides

    def _position_slide_elements(self, slide: Slide, content_groups: list[ContentGroup]) -> None:
        """
        Position elements within a slide based on content groups.

        Args:
            slide: Slide to position elements in
            content_groups: Content groups for this slide
        """
        # Start positioning after header
        header_height = 90.0
        current_y = self.margins["top"] + header_height
        group_spacing = 10.0

        for group in content_groups:
            # Position each element in the group
            for element in group.elements:
                if element.position and element.size:
                    # Update Y position while preserving X position and size
                    element.position = (element.position[0], current_y)
                    current_y += element.size[1]

                    # Add small spacing between elements within a group
                    if element != group.elements[-1]:  # Not the last element in group
                        current_y += 5.0

            # Add spacing between groups
            if group != content_groups[-1]:  # Not the last group
                current_y += group_spacing

        logger.debug(f"Positioned {sum(len(g.elements) for g in content_groups)} elements ending at y={current_y:.1f}")

    def _handle_oversized_group(self, group: ContentGroup) -> list[ContentGroup]:
        """
        Handle a content group that's too large for a single slide.

        Future enhancement: Could implement smart splitting of large groups.
        For now, returns the group as-is with a warning.

        Args:
            group: Oversized content group

        Returns:
            List of groups (potentially split)
        """
        logger.warning(f"Content group of type '{group.group_type}' exceeds slide capacity")

        # Future implementation could:
        # 1. Split long text elements across slides
        # 2. Split large lists into chunks
        # 3. Split large tables by rows
        # 4. Create "continued on next slide" markers

        return [group]  # For now, return as-is
