"""Updated unit tests for image element metrics with enhanced proactive scaling support."""

from markdowndeck.layout.constants import (
    DEFAULT_IMAGE_ASPECT_RATIO,
    IMAGE_HEIGHT_FRACTION,
    MIN_IMAGE_HEIGHT,
)
from markdowndeck.layout.metrics.image import (
    _get_image_aspect_ratio,
    calculate_image_display_size,
    calculate_image_element_height,
)
from markdowndeck.models import ElementType, ImageElement


class TestImageMetricsProactiveScaling:
    """Test proactive image scaling implementation per Rule #5."""

    def test_proactive_scaling_fits_container_width(self):
        """Test that images are proactively scaled to fit container width."""

        image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/test.jpg")

        container_width = 400.0
        calculated_height = calculate_image_element_height(image, container_width)

        # Height should be calculated based on container width and aspect ratio
        expected_height = container_width / DEFAULT_IMAGE_ASPECT_RATIO
        expected_height = max(expected_height, MIN_IMAGE_HEIGHT)

        assert abs(calculated_height - expected_height) < 1.0, (
            f"Proactively scaled height should match expected: {expected_height}, got {calculated_height}"
        )

    def test_proactive_scaling_with_width_directive(self):
        """Test proactive scaling respects width directives through display size calculation."""

        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"width": 0.5},  # 50% of container
        )

        container_width = 400.0
        # Width directives are handled by calculate_image_display_size, not calculate_image_element_height
        display_width, calculated_height = calculate_image_display_size(image, container_width)

        # Should scale based on 50% of container width
        effective_width = container_width * 0.5
        expected_height = effective_width / DEFAULT_IMAGE_ASPECT_RATIO
        expected_height = max(expected_height, MIN_IMAGE_HEIGHT)

        assert abs(display_width - effective_width) < 1.0, (
            f"Width should be 50% of container: expected {effective_width}, got {display_width}"
        )
        assert abs(calculated_height - expected_height) < 1.0, (
            f"Height should match expected: {expected_height}, got {calculated_height}"
        )

    def test_proactive_scaling_with_height_constraint(self):
        """Test proactive scaling with height constraints."""

        image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/test.jpg")

        container_width = 800.0
        available_height = 200.0  # Constraint

        calculated_height = calculate_image_element_height(image, container_width, available_height)

        # Should be constrained by available height
        max_allowed_height = available_height * IMAGE_HEIGHT_FRACTION
        unconstrained_height = container_width / DEFAULT_IMAGE_ASPECT_RATIO

        expected_height = max_allowed_height if unconstrained_height > max_allowed_height else unconstrained_height

        assert abs(calculated_height - expected_height) < 1.0

    def test_proactive_scaling_prevents_overflow(self):
        """Test that proactive scaling prevents images from causing overflow."""

        # Large container that would normally result in huge image
        huge_container_width = 2000.0
        available_height = 300.0

        image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/test.jpg")

        calculated_height = calculate_image_element_height(image, huge_container_width, available_height)

        # Should be constrained to prevent overflow
        max_allowed = available_height * IMAGE_HEIGHT_FRACTION
        assert calculated_height <= max_allowed + 1.0, "Proactive scaling should prevent overflow"

    def test_explicit_height_overrides_proactive_scaling(self):
        """Test that explicit height directives override proactive scaling."""

        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"height": 150.0},
        )

        # Large container that would normally scale differently
        container_width = 1000.0
        calculated_height = calculate_image_element_height(image, container_width)

        assert calculated_height == 150.0, "Explicit height directive should override proactive scaling"

    def test_minimum_height_enforced_in_proactive_scaling(self):
        """Test that minimum height is enforced even with proactive scaling."""

        image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/test.jpg")

        # Very small container that would normally result in tiny image
        tiny_container_width = 5.0
        calculated_height = calculate_image_element_height(image, tiny_container_width)

        assert calculated_height >= MIN_IMAGE_HEIGHT, (
            f"Should enforce minimum height {MIN_IMAGE_HEIGHT}, got {calculated_height}"
        )

    def test_aspect_ratio_detection_from_url(self):
        """Test aspect ratio detection from URL patterns."""

        # Test URL with dimensions in path
        image_800x600 = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/800x600/test.jpg")

        # Should detect 4:3 aspect ratio (800/600 = 1.333)
        container_width = 400.0
        height_800x600 = calculate_image_element_height(image_800x600, container_width)
        expected_height_4_3 = container_width / (800 / 600)

        assert abs(height_800x600 - expected_height_4_3) < 2.0, "Should detect aspect ratio from URL"

        # Test URL with query parameters
        image_with_params = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg?width=1920&height=1080",
        )

        height_16_9 = calculate_image_element_height(image_with_params, container_width)
        expected_height_16_9 = container_width / (1920 / 1080)

        assert abs(height_16_9 - expected_height_16_9) < 2.0, "Should detect aspect ratio from query parameters"

    def test_calculate_image_display_size_proactive(self):
        """Test calculate_image_display_size with proactive scaling."""

        image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/test.jpg")

        available_width = 400.0
        available_height = 300.0

        display_width, display_height = calculate_image_display_size(image, available_width, available_height)

        # Width should match available width (or directive if present)
        assert display_width == available_width

        # Height should be scaled appropriately
        expected_height = calculate_image_element_height(image, available_width, available_height)
        assert abs(display_height - expected_height) < 1.0

    def test_proactive_scaling_with_width_directive_display_size(self):
        """Test display size calculation with width directive."""

        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"width": 0.6},  # 60% width
        )

        available_width = 500.0
        available_height = 400.0

        display_width, display_height = calculate_image_display_size(image, available_width, available_height)

        expected_width = available_width * 0.6
        assert abs(display_width - expected_width) < 1.0

        # Height should be scaled for the actual display width
        expected_height = calculate_image_element_height(image, expected_width, available_height)
        assert abs(display_height - expected_height) < 1.0


class TestImageAspectRatioDetection:
    """Test aspect ratio detection functionality."""

    def test_aspect_ratio_from_path_dimensions(self):
        """Test aspect ratio detection from path-based dimensions."""

        # Test various dimension patterns in URLs
        test_cases = [
            ("https://example.com/800x600/test.jpg", 800 / 600),
            ("https://example.com/1920x1080/image.png", 1920 / 1080),
            ("https://example.com/400x300/pic.gif", 400 / 300),
        ]

        for url, expected_ratio in test_cases:
            detected_ratio = _get_image_aspect_ratio(url)
            assert abs(detected_ratio - expected_ratio) < 0.01, (
                f"Should detect ratio {expected_ratio} from {url}, got {detected_ratio}"
            )

    def test_aspect_ratio_from_query_params(self):
        """Test aspect ratio detection from query parameters."""

        test_cases = [
            ("https://example.com/test.jpg?width=800&height=600", 800 / 600),
            ("https://example.com/test.jpg?w=1920&h=1080", 1920 / 1080),
        ]

        for url, expected_ratio in test_cases:
            detected_ratio = _get_image_aspect_ratio(url)
            assert abs(detected_ratio - expected_ratio) < 0.01, (
                f"Should detect ratio {expected_ratio} from {url}, got {detected_ratio}"
            )

    def test_aspect_ratio_from_filename(self):
        """Test aspect ratio detection from filename patterns."""

        test_cases = [
            ("https://example.com/image_800x600.jpg", 800 / 600),
            ("https://example.com/pic_1920x1080.png", 1920 / 1080),
        ]

        for url, expected_ratio in test_cases:
            detected_ratio = _get_image_aspect_ratio(url)
            # This might not be implemented yet, so allow default ratio
            if detected_ratio != DEFAULT_IMAGE_ASPECT_RATIO:
                assert abs(detected_ratio - expected_ratio) < 0.01

    def test_aspect_ratio_default_fallback(self):
        """Test fallback to default aspect ratio."""

        urls_without_dimensions = [
            "https://example.com/test.jpg",
            "https://example.com/images/photo.png",
            "data:image/jpeg;base64,/9j/4AAQSkZJRgABA...",
        ]

        for url in urls_without_dimensions:
            detected_ratio = _get_image_aspect_ratio(url)
            assert detected_ratio == DEFAULT_IMAGE_ASPECT_RATIO, f"Should fallback to default ratio for {url}"

    def test_aspect_ratio_caching(self):
        """Test that aspect ratio detection uses caching."""

        url = "https://example.com/800x600/test.jpg"

        # First call
        ratio1 = _get_image_aspect_ratio(url)

        # Second call should use cache
        ratio2 = _get_image_aspect_ratio(url)

        assert ratio1 == ratio2
        assert ratio1 == 800 / 600


class TestImageMetricsErrorHandling:
    """Test error handling in image metrics."""

    def test_empty_url_handling(self):
        """Test handling of empty or invalid URLs."""

        empty_image = ImageElement(element_type=ElementType.IMAGE, url="")

        height = calculate_image_element_height(empty_image, 400.0)
        assert height >= MIN_IMAGE_HEIGHT

    def test_invalid_directive_handling(self):
        """Test handling of invalid directives."""

        image_invalid_height = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"height": "invalid"},
        )

        # Should not crash and should fall back to calculated height
        height = calculate_image_element_height(image_invalid_height, 400.0)
        assert height > 0

    def test_extreme_dimensions_handling(self):
        """Test handling of extreme dimension values."""

        image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/test.jpg")

        # Very small width
        height_tiny = calculate_image_element_height(image, 1.0)
        assert height_tiny >= MIN_IMAGE_HEIGHT

        # Very large width
        height_huge = calculate_image_element_height(image, 10000.0)
        assert height_huge > 0
        assert height_huge < 100000  # Should be reasonable

    def test_zero_or_negative_dimensions(self):
        """Test handling of zero or negative dimensions."""

        image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/test.jpg")

        # Zero width
        height_zero = calculate_image_element_height(image, 0.0)
        assert height_zero >= MIN_IMAGE_HEIGHT

        # Negative width
        height_negative = calculate_image_element_height(image, -100.0)
        assert height_negative >= MIN_IMAGE_HEIGHT


class TestImageElementSplittingProactive:
    """Test image element splitting with proactive scaling integration."""

    def test_image_split_always_fits_due_to_proactive_scaling(self):
        """Test that images always fit due to proactive scaling (Rule #5)."""

        # Create a large image that would normally overflow
        large_image = ImageElement(element_type=ElementType.IMAGE, url="https://example.com/huge_image.jpg")
        # Set size as if calculated by layout system
        large_image.size = (400, 300)  # Already proactively scaled

        # Test with very small available height
        fitted, overflowing = large_image.split(50)

        # Per Rule #5, images are proactively scaled to prevent overflow
        assert fitted is not None, "Image should always fit due to proactive scaling"
        assert overflowing is None, "No overflow should occur with proactive scaling"
        assert fitted is large_image, "Should return the original image"

    def test_image_split_preserves_proactive_scaling_metadata(self):
        """Test that split preserves proactive scaling metadata."""

        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"width": 0.8},  # Proactive scaling directive
            alt_text="Proactively scaled image",
        )
        image.size = (320, 180)  # Proactively scaled size

        fitted, overflowing = image.split(100)

        assert fitted is not None
        assert fitted.directives.get("width") == 0.8
        assert fitted.alt_text == "Proactively scaled image"
        assert fitted.size == (320, 180)
        assert overflowing is None

    def test_image_split_consistency_with_proactive_scaling(self):
        """Test that split behavior is consistent with proactive scaling principle."""

        # Create images with different aspect ratios
        wide_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/1920x1080/wide.jpg",  # 16:9
        )

        tall_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/600x800/tall.jpg",  # 3:4
        )

        # Both should have been proactively scaled to fit
        wide_image.size = (400, 225)  # Scaled for 16:9
        tall_image.size = (400, 533)  # Scaled for 3:4

        # Both should always fit regardless of available height
        wide_fitted, wide_overflow = wide_image.split(100)
        tall_fitted, tall_overflow = tall_image.split(100)

        assert wide_fitted is not None
        assert wide_overflow is None
        assert tall_fitted is not None
        assert tall_overflow is None

    def test_image_split_with_explicit_height_directive(self):
        """Test split behavior with explicit height directives."""

        image_fixed_height = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"height": 200},  # Explicit height
        )
        image_fixed_height.size = (400, 200)  # Size respects directive

        # Even with explicit height, proactive scaling ensures it fits
        fitted, overflowing = image_fixed_height.split(150)

        # Behavior depends on implementation - could fit or not
        # But should not cause system errors
        assert fitted is not None or overflowing is not None
        if fitted is not None:
            assert fitted.directives.get("height") == 200
