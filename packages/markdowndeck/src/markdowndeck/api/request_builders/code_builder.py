"""Code request builder for Google Slides API requests."""

import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import CodeElement

logger = logging.getLogger(__name__)


class CodeRequestBuilder(BaseRequestBuilder):
    """Builder for code-related Google Slides API requests."""

    def generate_code_element_requests(
        self, element: CodeElement, slide_id: str
    ) -> list[dict]:
        """
        Generate requests for a code element.

        Args:
            element: The code element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 200))

        # Ensure element has a valid object_id
        if not element.object_id:
            element.object_id = self._generate_id(f"code_{slide_id}")
            logger.debug(
                f"Generated missing object_id for code element: {element.object_id}"
            )

        # Create shape
        create_shape_request = {
            "createShape": {
                "objectId": element.object_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": size[0], "unit": "PT"},
                        "height": {"magnitude": size[1], "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": position[0],
                        "translateY": position[1],
                        "unit": "PT",
                    },
                },
            }
        }
        requests.append(create_shape_request)

        # We're no longer setting autofit since only NONE is supported,
        # and applying NONE is unnecessary as it's the default

        # Skip insertion if there's no code text
        if not element.code:
            return requests

        # Insert code text
        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": element.code,
            }
        }
        requests.append(insert_text_request)

        # Add code formatting (monospace font, background)
        style_request = self._apply_text_formatting(
            element_id=element.object_id,
            style={
                "fontFamily": "Courier New",
                "backgroundColor": {
                    "opaqueColor": {
                        "rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                    }
                },
            },
            fields="fontFamily,backgroundColor",
            range_type="ALL",
        )
        requests.append(style_request)

        # Set reasonable paragraph spacing to prevent excessive gaps
        paragraph_style = {
            "updateParagraphStyle": {
                "objectId": element.object_id,
                "textRange": {"type": "ALL"},
                "style": {
                    # Use less space for code which is already well-spaced visually
                    "spaceAbove": {"magnitude": 0, "unit": "PT"},
                    "spaceBelow": {"magnitude": 0, "unit": "PT"},
                    # Set line spacing slightly higher than single for readability
                    "lineSpacing": 115,  # 1.15 spacing is good for code readability
                },
                "fields": "spaceAbove,spaceBelow,lineSpacing",
            }
        }
        requests.append(paragraph_style)

        # Add shape background
        shape_background_request = {
            "updateShapeProperties": {
                "objectId": element.object_id,
                "fields": "shapeBackgroundFill.solidFill.color",  # Correct field path
                "shapeProperties": {
                    "shapeBackgroundFill": {
                        "solidFill": {
                            "color": {
                                "rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                            }
                        }
                    }
                },
            }
        }
        requests.append(shape_background_request)

        # Add language label if specified
        if element.language and element.language != "text":
            # Create label shape
            label_id = f"{element.object_id}_label"
            create_label_request = {
                "createShape": {
                    "objectId": label_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": 80, "unit": "PT"},
                            "height": {"magnitude": 20, "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": position[0],
                            "translateY": position[1] - 20,  # Above code block
                            "unit": "PT",
                        },
                    },
                }
            }
            requests.append(create_label_request)

            # Insert label text
            insert_label_request = {
                "insertText": {
                    "objectId": label_id,
                    "insertionIndex": 0,
                    "text": element.language,
                }
            }
            requests.append(insert_label_request)

            # Style label
            style_label_request = self._apply_text_formatting(
                element_id=label_id,
                style={
                    "fontFamily": "Arial",
                    "fontSize": {"magnitude": 10, "unit": "PT"},
                    "foregroundColor": {
                        "opaqueColor": {
                            "rgbColor": {"red": 0.3, "green": 0.3, "blue": 0.3}
                        }
                    },
                },
                fields="fontFamily,fontSize,foregroundColor",
                range_type="ALL",
            )
            requests.append(style_label_request)

            # Center text in label
            center_label_request = {
                "updateParagraphStyle": {
                    "objectId": label_id,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "alignment": "CENTER",
                    },
                    "fields": "alignment",
                }
            }
            requests.append(center_label_request)

        return requests
