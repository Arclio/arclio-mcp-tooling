import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    Slide,
    TextElement,
)


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    """Provides a fresh ApiRequestGenerator instance for each test."""
    return ApiRequestGenerator()


class TestApiGeneratorAutofit:
    def test_api_c_10_autofit_is_disabled_for_all_text_shapes(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-10
        Validates that any 'createShape' request for a TEXT_BOX is immediately
        followed by an 'updateShapeProperties' request to disable autofit.
        This confirms our layout instructions are being sent correctly.
        Spec: Implicit requirement for predictable layout.
        """
        # Arrange: A slide with multiple text elements to ensure this is a consistent behavior.
        text_element_1 = TextElement(
            element_type=ElementType.TEXT,
            text="Sample content 1",
            object_id="test_shape_1",
            position=(100, 100),
            size=(300, 150),
        )
        text_element_2 = TextElement(
            element_type=ElementType.TEXT,
            text="Sample content 2",
            object_id="test_shape_2",
            position=(100, 300),
            size=(300, 150),
        )
        slide = Slide(object_id="test_slide", renderable_elements=[text_element_1, text_element_2])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert: For each text element, verify the autofit request follows creation.
        for obj_id in ["test_shape_1", "test_shape_2"]:
            create_shape_index = -1
            for i, req in enumerate(requests):
                if req.get("createShape", {}).get("objectId") == obj_id:
                    create_shape_index = i
                    break

            assert create_shape_index != -1, f"createShape request not found for {obj_id}."

            assert create_shape_index + 1 < len(requests), f"No request found after createShape for {obj_id}."
            autofit_request = requests[create_shape_index + 1]

            assert "updateShapeProperties" in autofit_request, (
                f"Expected updateShapeProperties request after createShape for {obj_id}."
            )

            props = autofit_request["updateShapeProperties"]
            assert props["objectId"] == obj_id
            assert props["fields"] == "autofit.autofitType"
            assert props["shapeProperties"]["autofit"]["autofitType"] == "NONE"
