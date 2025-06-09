"""
Unit tests for the ApiRequestGenerator, ensuring adherence to API_GEN_SPEC.md.

Each test case directly corresponds to a specification in
`docs/markdowndeck/testing/TEST_CASES_UNIT_API_GENERATOR.md`.
"""

import re
from copy import deepcopy

import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    ImageElement,
    Section,
    Slide,
    SlideLayout,
    TextElement,
)
from markdowndeck.models.elements.list import ListElement


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    """Provides a fresh ApiRequestGenerator instance for each test."""
    return ApiRequestGenerator()


@pytest.fixture
def finalized_slide() -> Slide:
    """
    Provides a slide in the 'Finalized' state, which is the expected
    input for the ApiRequestGenerator.
    """
    return Slide(
        object_id="final_slide_1",
        sections=[],  # Must be empty
        elements=[],  # Must be empty
        renderable_elements=[
            TextElement(
                element_type=ElementType.TITLE,
                text="Finalized Title",
                object_id="el_title",
                position=(50, 50),
                size=(620, 40),
            ),
            TextElement(
                element_type=ElementType.TEXT,
                text="Finalized Body",
                object_id="el_body",
                position=(50, 150),
                size=(620, 100),
            ),
        ],
    )


class TestApiRequestGenerator:
    """Tests the functionality of the ApiRequestGenerator."""

    def test_object_id_regex_compliance(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-06
        Validates that all generated objectIds comply with Google Slides API regex.

        Per Google Slides API documentation, objectIds must match:
        ^[a-zA-Z0-9_][a-zA-Z0-9_-:]*$
        """
        # Arrange: Create a slide with various element types without object_ids
        slide = Slide(
            object_id="test_slide",
            sections=[],
            elements=[],
            renderable_elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Test Title",
                    position=(50, 50),
                    size=(620, 40),
                    object_id=None,  # Explicitly set to None to force generation
                ),
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Test Body",
                    position=(50, 150),
                    size=(620, 100),
                    object_id=None,  # Explicitly set to None to force generation
                ),
                ImageElement(
                    element_type=ElementType.IMAGE,
                    url="https://example.com/image.jpg",
                    position=(50, 300),
                    size=(300, 200),
                    object_id=None,  # Explicitly set to None to force generation
                ),
            ],
        )
        deck = Deck(slides=[slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert: Check that ALL objectIds in createShape/createImage requests match the regex
        google_slides_object_id_regex = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_:\-]*$")

        generated_object_ids = []
        for batch in batches:
            for request in batch["requests"]:
                object_id = None

                # Extract objectId from different request types
                if "createShape" in request:
                    object_id = request["createShape"]["objectId"]
                elif "createImage" in request:
                    object_id = request["createImage"]["objectId"]
                elif "createSlide" in request:
                    object_id = request["createSlide"]["objectId"]
                elif "insertText" in request:
                    object_id = request["insertText"]["objectId"]
                elif "updateParagraphStyle" in request:
                    object_id = request["updateParagraphStyle"]["objectId"]

                # Validate objectId if found
                if object_id:
                    generated_object_ids.append(object_id)
                    assert google_slides_object_id_regex.match(object_id), (
                        f"ObjectId '{object_id}' does not match Google Slides API regex "
                        f"^[a-zA-Z0-9_][a-zA-Z0-9_-:]*$"
                    )

        # Ensure we actually tested some objectIds
        assert len(generated_object_ids) > 0, "No objectIds were generated to test"

    def test_empty_list_no_delete_text(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-07
        Validates that empty lists don't generate invalid deleteText requests.

        This tests the fix for Discrepancy #2: Invalid deleteText for empty placeholders.
        """
        # Arrange: Create a slide with an empty list element
        slide = Slide(
            object_id="test_slide",
            sections=[],
            elements=[],
            renderable_elements=[
                ListElement(
                    element_type=ElementType.BULLET_LIST,
                    items=[],  # Empty list
                    position=(50, 150),
                    size=(620, 100),
                    object_id=None,
                ),
            ],
        )
        deck = Deck(slides=[slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert: Check that no deleteText requests are generated for empty lists
        for batch in batches:
            for request in batch["requests"]:
                assert (
                    "deleteText" not in request
                ), "Empty lists should not generate deleteText requests as they would be invalid"

    def test_invalid_image_url_skipped(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-08
        Validates that invalid image URLs are skipped and don't generate createImage requests.

        This tests the fix for Discrepancy #3: Inconsistent image URL validation.
        """
        # Arrange: Create a slide with an invalid image URL
        slide = Slide(
            object_id="test_slide",
            sections=[],
            elements=[],
            renderable_elements=[
                ImageElement(
                    element_type=ElementType.IMAGE,
                    url="invalid-url-not-http",  # Invalid URL
                    position=(50, 300),
                    size=(300, 200),
                    object_id=None,
                ),
            ],
        )
        deck = Deck(slides=[slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert: Check that no createImage requests are generated for invalid URLs
        for batch in batches:
            for request in batch["requests"]:
                assert (
                    "createImage" not in request
                ), "Invalid image URLs should not generate createImage requests"

    def test_api_c_01(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-01
        Validates the generator ONLY reads from `slide.renderable_elements`.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange: Add junk data to stale lists
        finalized_slide.sections = [Section(id="junk_section")]
        finalized_slide.elements = [
            ImageElement(element_type=ElementType.IMAGE, url="junk.png")
        ]
        deck = Deck(slides=[finalized_slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert
        requests = batches[0]["requests"]

        # Check that requests were generated for renderable_elements
        title_req = next(
            (
                r
                for r in requests
                if r.get("insertText", {}).get("text") == "Finalized Title"
            ),
            None,
        )
        body_req = next(
            (
                r
                for r in requests
                if r.get("insertText", {}).get("text") == "Finalized Body"
            ),
            None,
        )
        assert title_req is not None
        assert body_req is not None

        # Check that junk data was ignored
        image_req = next((r for r in requests if "createImage" in r), None)
        assert (
            image_req is None
        ), "Junk data from stale 'elements' list should be ignored."

    def test_api_c_02(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-02
        Validates that the generator is stateless and does not modify its input.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        original_slide_copy = deepcopy(finalized_slide)
        deck = Deck(slides=[finalized_slide])

        # Act
        api_generator.generate_batch_requests(deck, "pres_id")

        # Assert
        assert (
            finalized_slide == original_slide_copy
        ), "Generator must not modify the input slide object."

    def test_api_c_03(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-03
        Validates interpretation of visual styling directives.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        styled_element = TextElement(
            element_type=ElementType.TEXT,
            text="Styled Text",
            object_id="styled_el",
            position=(50, 200),
            size=(200, 50),
            directives={"color": "#FF0000", "fontsize": 18},
        )
        finalized_slide.renderable_elements.append(styled_element)
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        style_reqs = [
            r
            for r in requests
            if "updateTextStyle" in r
            and r["updateTextStyle"]["objectId"] == "styled_el"
        ]
        assert (
            len(style_reqs) > 0
        ), "Should generate updateTextStyle requests for directives."

        # Find the specific style updates
        color_update = next(
            (
                r
                for r in style_reqs
                if "foregroundColor" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        font_update = next(
            (r for r in style_reqs if "fontSize" in r["updateTextStyle"]["style"]), None
        )

        assert (
            color_update is not None
        ), "A request to update foregroundColor should exist."
        assert (
            color_update["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
                "rgbColor"
            ]["red"]
            == 1.0
        )

        assert font_update is not None, "A request to update fontSize should exist."
        assert font_update["updateTextStyle"]["style"]["fontSize"]["magnitude"] == 18

    def test_api_c_04(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-04
        Validates correct structure for position and size in API requests.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        shape_req = next(
            (
                r
                for r in requests
                if "createShape" in r and r["createShape"]["objectId"] == "el_body"
            ),
            None,
        )
        assert (
            shape_req is not None
        ), "A createShape request for the element should exist."

        props = shape_req["createShape"]["elementProperties"]

        # Check size structure
        assert "size" in props
        assert "width" in props["size"]
        assert "height" in props["size"]
        assert "magnitude" in props["size"]["width"]
        assert "unit" in props["size"]["width"]

        # Check transform structure
        assert "transform" in props
        assert "translateX" in props["transform"]
        assert "translateY" in props["transform"]
        assert "unit" in props["transform"]

    def test_api_c_05(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-05
        Validates that generated requests use precise `fields` masks.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        bg_element = TextElement(
            element_type=ElementType.TEXT,
            text="BG Text",
            object_id="bg_el",
            position=(50, 250),
            size=(200, 50),
            directives={"background": ("color", "#123456")},
        )
        finalized_slide.renderable_elements.append(bg_element)
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        update_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and r["updateShapeProperties"]["objectId"] == "bg_el"
                and "shapeBackgroundFill"
                in r["updateShapeProperties"].get("fields", "")
            ),
            None,
        )

        assert (
            update_req is not None
        ), "An updateShapeProperties request should exist for the background."

        # Validate the fields mask is precise as per the gotcha
        expected_mask = "shapeBackgroundFill.solidFill.color.rgbColor"
        assert (
            update_req["updateShapeProperties"]["fields"] == expected_mask
        ), f"Field mask must be precise. Expected '{expected_mask}', got '{update_req['updateShapeProperties']['fields']}'"

    def test_api_c_09_placeholder_usage_and_autofit(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-09
        Validates that placeholders are used correctly and autofit properties are set.
        From: TASK_008 Sub-Task 1 and 2 implementation.
        """
        # Arrange: Create a slide with placeholder mappings and text elements
        slide = Slide(
            object_id="test_slide_ph",
            layout=SlideLayout.TITLE_AND_BODY,
            placeholder_mappings={
                ElementType.TITLE: "placeholder_title_123",
                ElementType.TEXT: "placeholder_body_456",
            },
        )

        # Add a title element that should use the title placeholder
        title_element = TextElement(
            element_type=ElementType.TITLE,
            text="Test Title",
            position=(50, 50),
            size=(600, 100),
        )

        # Add a text element that should use the body placeholder
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Test body text",
            position=(50, 200),
            size=(600, 200),
        )

        # Add a text element without placeholder (should create new shape)
        no_placeholder_element = TextElement(
            element_type=ElementType.TEXT,
            text="No placeholder text",
            object_id="explicit_text_box",
            position=(50, 400),
            size=(600, 100),
        )

        slide.renderable_elements = [
            title_element,
            text_element,
            no_placeholder_element,
        ]
        deck = Deck(slides=[slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")
        requests = batches[0]["requests"]

        # Assert: Verify title placeholder usage
        title_inserts = [
            r
            for r in requests
            if "insertText" in r
            and r["insertText"]["objectId"] == "placeholder_title_123"
        ]
        assert len(title_inserts) == 1, "Should insert text into title placeholder"
        assert title_inserts[0]["insertText"]["text"] == "Test Title"

        # Assert: Title placeholder should NOT have deleteText (fixed in TASK_008)
        # This prevents the "startIndex 0 must be less than endIndex 0" error
        title_deletes = [
            r
            for r in requests
            if "deleteText" in r
            and r["deleteText"]["objectId"] == "placeholder_title_123"
        ]
        assert (
            len(title_deletes) == 0
        ), "Should NOT delete from themed placeholders to avoid API errors"

        # Assert: Body placeholder usage
        body_inserts = [
            r
            for r in requests
            if "insertText" in r
            and r["insertText"]["objectId"] == "placeholder_body_456"
        ]
        assert len(body_inserts) == 1, "Should insert text into body placeholder"
        assert body_inserts[0]["insertText"]["text"] == "Test body text"

        # Assert: Body placeholder should NOT have deleteText (fixed in TASK_008)
        body_deletes = [
            r
            for r in requests
            if "deleteText" in r
            and r["deleteText"]["objectId"] == "placeholder_body_456"
        ]
        assert (
            len(body_deletes) == 0
        ), "Should NOT delete from themed placeholders to avoid API errors"

        # Assert: No createShape for placeholder elements
        title_creates = [
            r
            for r in requests
            if "createShape" in r
            and r["createShape"]["objectId"] == "placeholder_title_123"
        ]
        assert (
            len(title_creates) == 0
        ), "Should not create shape for placeholder elements"

        body_creates = [
            r
            for r in requests
            if "createShape" in r
            and r["createShape"]["objectId"] == "placeholder_body_456"
        ]
        assert (
            len(body_creates) == 0
        ), "Should not create shape for placeholder elements"

        # Assert: createShape for non-placeholder element
        explicit_creates = [
            r
            for r in requests
            if "createShape" in r
            and r["createShape"]["objectId"] == "explicit_text_box"
        ]
        assert (
            len(explicit_creates) == 1
        ), "Should create shape for non-placeholder elements"

        # Assert: Autofit disabled for created shapes
        autofit_requests = [
            r
            for r in requests
            if "updateShapeProperties" in r
            and "autofit" in r["updateShapeProperties"].get("shapeProperties", {})
            and r["updateShapeProperties"]["objectId"] == "explicit_text_box"
        ]
        assert (
            len(autofit_requests) == 1
        ), "Should set autofit properties for created text boxes"

        autofit_req = autofit_requests[0]
        assert autofit_req["updateShapeProperties"]["fields"] == "autofit.autofitType"
        assert (
            autofit_req["updateShapeProperties"]["shapeProperties"]["autofit"][
                "autofitType"
            ]
            == "NONE"
        )

    def test_api_c_10_autofit_is_disabled_for_text_shapes(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-10
        Validates that any 'createShape' request for a TEXT_BOX is immediately
        followed by an 'updateShapeProperties' request to disable autofit.
        Spec: Implicit requirement for predictable layout.
        """
        # Arrange
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Sample content",
            object_id="test_shape_1",
            position=(100, 100),
            size=(300, 150),
        )
        slide = Slide(object_id="test_slide", renderable_elements=[text_element])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        create_shape_index = -1
        for i, req in enumerate(requests):
            if req.get("createShape", {}).get("objectId") == "test_shape_1":
                create_shape_index = i
                break

        assert (
            create_shape_index != -1
        ), "createShape request not found for the text element."

        # The very next request should be to disable autofit
        assert create_shape_index + 1 < len(
            requests
        ), "No request found after createShape."
        autofit_request = requests[create_shape_index + 1]
        assert (
            "updateShapeProperties" in autofit_request
        ), "Expected updateShapeProperties request after createShape."

        props = autofit_request["updateShapeProperties"]
        assert props["objectId"] == "test_shape_1"
        assert props["fields"] == "autofit.autofitType"
        assert props["shapeProperties"]["autofit"]["autofitType"] == "NONE"

    def test_api_c_12_autofit_disabled_for_pathologically_narrow_text_shapes(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-12
        Validates that autofit is disabled even for pathologically narrow text shapes
        like those that cause the overlapping text bug (width: 37.5).
        This test targets the exact scenario from TASK_005.
        """
        # Arrange: Create a pathologically narrow text element (like the bug scenario)
        narrow_text_element = TextElement(
            element_type=ElementType.TEXT,
            text="This text is in the second column and should be very narrow causing problems",
            object_id="text_slide_2_d77c491f",  # Same ID from TASK_005 evidence
            position=(360.0, 150.0),
            size=(37.5, 337.2),  # Exact pathological dimensions from TASK_005
        )
        slide = Slide(
            object_id="pathological_slide", renderable_elements=[narrow_text_element]
        )
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert: Find the createShape request
        create_shape_index = -1
        for i, req in enumerate(requests):
            if req.get("createShape", {}).get("objectId") == "text_slide_2_d77c491f":
                create_shape_index = i
                break

        assert (
            create_shape_index != -1
        ), "createShape request not found for pathological text element."

        # The CRITICAL assertion: There must be an updateShapeProperties request immediately after createShape
        assert create_shape_index + 1 < len(
            requests
        ), "No request found after createShape."
        next_request = requests[create_shape_index + 1]

        # This should be the autofit request, but if the bug exists, it might be insertText instead
        if "insertText" in next_request:
            # This means autofit was skipped! This is the bug.
            raise AssertionError(
                f"BUG DETECTED: insertText request found immediately after createShape without autofit! Next request: {next_request}"
            )

        assert (
            "updateShapeProperties" in next_request
        ), f"Expected updateShapeProperties request after createShape, got: {next_request}"

        props = next_request["updateShapeProperties"]
        assert props["objectId"] == "text_slide_2_d77c491f"
        assert props["fields"] == "autofit.autofitType"
        assert props["shapeProperties"]["autofit"]["autofitType"] == "NONE"

    def test_api_c_11_autofit_is_disabled_for_nested_text_shapes(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-11
        Validates that 'autofit: NONE' is applied to ALL created text shapes,
        including those within nested sections (columns). This test ensures the
        fix for inconsistent autofit application.
        Spec: Implicit requirement for predictable layout.
        """
        # Arrange: A slide with a columnar layout
        text_element_col1 = TextElement(
            element_type=ElementType.TEXT,
            text="Column 1",
            object_id="col1_shape",
            position=(50, 150),
            size=(300, 100),
        )
        text_element_col2 = TextElement(
            element_type=ElementType.TEXT,
            text="Column 2",
            object_id="col2_shape",
            position=(360, 150),
            size=(300, 100),
        )
        slide = Slide(
            object_id="nested_slide",
            renderable_elements=[text_element_col1, text_element_col2],
        )
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert for Column 1
        create_shape_index_1 = next(
            (
                i
                for i, req in enumerate(requests)
                if req.get("createShape", {}).get("objectId") == "col1_shape"
            ),
            -1,
        )
        assert create_shape_index_1 != -1, "createShape request not found for column 1."
        autofit_request_1 = requests[create_shape_index_1 + 1]
        assert (
            "updateShapeProperties" in autofit_request_1
        ), "Expected updateShapeProperties for column 1."
        assert (
            autofit_request_1["updateShapeProperties"]["shapeProperties"]["autofit"][
                "autofitType"
            ]
            == "NONE"
        )

        # Assert for Column 2
        create_shape_index_2 = next(
            (
                i
                for i, req in enumerate(requests)
                if req.get("createShape", {}).get("objectId") == "col2_shape"
            ),
            -1,
        )
        assert create_shape_index_2 != -1, "createShape request not found for column 2."
        autofit_request_2 = requests[create_shape_index_2 + 1]
        assert (
            "updateShapeProperties" in autofit_request_2
        ), "Expected updateShapeProperties for column 2."
        assert (
            autofit_request_2["updateShapeProperties"]["shapeProperties"]["autofit"][
                "autofitType"
            ]
            == "NONE"
        )

    def test_api_c_11_autofit_is_disabled_for_all_text_shapes_in_columns(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-11
        Validates that 'autofit: NONE' is applied to ALL created text shapes,
        including those within nested sections (columns), proving consistent application.
        Spec: Implicit requirement for predictable layout from PRINCIPLES.md.
        """
        # Arrange: A slide with a columnar layout
        text_element_col1 = TextElement(
            element_type=ElementType.TEXT,
            text="Column 1",
            object_id="col1_shape",
            position=(50, 150),
            size=(300, 100),
        )
        text_element_col2 = TextElement(
            element_type=ElementType.TEXT,
            text="Column 2",
            object_id="col2_shape",
            position=(360, 150),
            size=(300, 100),
        )
        slide = Slide(
            object_id="nested_slide",
            renderable_elements=[text_element_col1, text_element_col2],
        )
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert that EACH createShape is followed by an autofit request
        for obj_id in ["col1_shape", "col2_shape"]:
            create_shape_index = next(
                (
                    i
                    for i, req in enumerate(requests)
                    if req.get("createShape", {}).get("objectId") == obj_id
                ),
                -1,
            )

            assert (
                create_shape_index != -1
            ), f"createShape request not found for {obj_id}."

            autofit_request = requests[create_shape_index + 1]
            assert (
                "updateShapeProperties" in autofit_request
            ), f"Expected updateShapeProperties for {obj_id}."

            props = autofit_request["updateShapeProperties"]
            assert props["objectId"] == obj_id
            assert props["fields"] == "autofit.autofitType"
            assert props["shapeProperties"]["autofit"]["autofitType"] == "NONE"

    def test_api_c_13_autofit_bug_themed_placeholders_missing_autofit(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-13
        CRITICAL BUG TEST: Exposes the autofit bug for themed text placeholders.

        The bug is in _handle_themed_text_element() which does NOT disable autofit
        for text elements that use theme placeholders, while regular text elements do.
        This causes inconsistent autofit behavior described in TASK_005.
        """
        # Arrange: Create a text element WITHOUT object_id so it uses theme placeholder
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="This text should use a themed placeholder and expose the autofit bug",
            object_id=None,  # This forces use of theme placeholder
            position=(50.0, 150.0),
            size=(37.5, 337.2),  # Use pathological dimensions to trigger the bug
        )

        # Create a slide with placeholder mappings (simulating themed slide)
        slide = Slide(
            object_id="themed_slide",
            renderable_elements=[text_element],
            placeholder_mappings={ElementType.TEXT: "themed_text_placeholder_id"},
        )
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert: For themed placeholders, there should be NO createShape request
        # Instead we should see insertText directly to the placeholder
        [r for r in requests if "createShape" in r]
        insert_text_requests = [
            r
            for r in requests
            if "insertText" in r
            and r["insertText"]["objectId"] == "themed_text_placeholder_id"
        ]

        # The bug: insertText exists but no autofit request for the placeholder
        assert (
            len(insert_text_requests) > 0
        ), "Should have insertText request for themed placeholder"

        # Look for any autofit request for the themed placeholder
        autofit_requests = [
            r
            for r in requests
            if "updateShapeProperties" in r
            and r["updateShapeProperties"]["objectId"] == "themed_text_placeholder_id"
            and "autofit" in r["updateShapeProperties"].get("shapeProperties", {})
        ]

        # This assertion will FAIL and expose the bug
        assert len(autofit_requests) > 0, (
            f"BUG CONFIRMED: No autofit request found for themed placeholder! "
            f"Found {len(insert_text_requests)} insertText requests but {len(autofit_requests)} autofit requests. "
            f"All requests: {[list(r.keys())[0] for r in requests]}"
        )
