"""Text request builder for Google Slides API requests."""

import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    TextElement,
)

logger = logging.getLogger(__name__)


class TextRequestBuilder(BaseRequestBuilder):
    """Builder for text-related Google Slides API requests."""

    def generate_text_element_requests(
        self,
        element: TextElement,
        slide_id: str,
        theme_placeholders: dict[str, str] = None,
    ) -> list[dict]:
        """
        Generate requests for a text element.

        Args:
            element: The text element
            slide_id: The slide ID
            theme_placeholders: Dictionary mapping element types to placeholder IDs

        Returns:
            List of request dictionaries
        """
        requests = []

        # Check if this element should use a theme placeholder
        if theme_placeholders and element.element_type in theme_placeholders:
            # Use placeholder instead of creating a new shape
            return self._handle_themed_text_element(
                element, theme_placeholders[element.element_type]
            )

        # If no theme placeholder, proceed with custom shape creation
        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (300, 200))

        # Ensure element has a valid object_id
        if not element.object_id:
            element.object_id = self._generate_id(f"text_{slide_id}")
            logger.debug(
                f"Generated missing object_id for text element: {element.object_id}"
            )

        # Create text box
        create_textbox_request = {
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
        requests.append(create_textbox_request)

        # Skip insertion if there's no text
        if not element.text:
            return requests

        # Insert text
        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": element.text,
            }
        }
        requests.append(insert_text_request)

        # Apply text formatting if present
        if hasattr(element, "formatting") and element.formatting:
            for text_format in element.formatting:
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style=self._format_to_style(text_format),
                    fields=self._format_to_fields(text_format),
                    start_index=text_format.start,
                    end_index=text_format.end,
                )
                requests.append(style_request)

        # Apply paragraph style if this is a title or subtitle
        if element.element_type in (ElementType.TITLE, ElementType.SUBTITLE):
            paragraph_style = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "alignment": "CENTER",
                    },
                    "fields": "alignment",
                }
            }
            requests.append(paragraph_style)
        # Apply horizontal alignment if specified and this is not a title/subtitle
        elif hasattr(element, "horizontal_alignment") and element.horizontal_alignment:
            alignment_map = {
                AlignmentType.LEFT: "START",
                AlignmentType.CENTER: "CENTER",
                AlignmentType.RIGHT: "END",
                AlignmentType.JUSTIFY: "JUSTIFIED",
            }
            api_alignment = alignment_map.get(element.horizontal_alignment, "START")

            paragraph_style = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "alignment": api_alignment,
                    },
                    "fields": "alignment",
                }
            }
            requests.append(paragraph_style)

        # ENHANCEMENT: Apply vertical alignment if specified
        if (
            hasattr(element, "directives")
            and element.directives
            and "valign" in element.directives
        ):
            valign_value = element.directives["valign"]
            if isinstance(valign_value, str):
                # Map valign directive to API values
                valign_map = {
                    "top": "TOP",
                    "middle": "MIDDLE",
                    "bottom": "BOTTOM",
                }
                api_valign = valign_map.get(valign_value.lower(), "MIDDLE")

                # Create shape properties update request
                vertical_align_request = {
                    "updateShapeProperties": {
                        "objectId": element.object_id,
                        "fields": "contentVerticalAlignment",
                        "shapeProperties": {"contentVerticalAlignment": api_valign},
                    }
                }
                requests.append(vertical_align_request)
                logger.debug(
                    f"Applied vertical alignment '{api_valign}' to element {element.object_id}"
                )

        # ENHANCEMENT: Apply text box padding if specified
        if (
            hasattr(element, "directives")
            and element.directives
            and "padding" in element.directives
        ):
            padding_value = element.directives["padding"]
            if isinstance(padding_value, int | float):
                # Create text box properties update request
                padding_request = {
                    "updateShapeProperties": {
                        "objectId": element.object_id,
                        "fields": "textBoxProperties.leftInset,textBoxProperties.rightInset,textBoxProperties.topInset,textBoxProperties.bottomInset",
                        "shapeProperties": {
                            "textBoxProperties": {
                                "leftInset": {"magnitude": padding_value, "unit": "PT"},
                                "rightInset": {
                                    "magnitude": padding_value,
                                    "unit": "PT",
                                },
                                "topInset": {"magnitude": padding_value, "unit": "PT"},
                                "bottomInset": {
                                    "magnitude": padding_value,
                                    "unit": "PT",
                                },
                            }
                        },
                    }
                }
                requests.append(padding_request)
                logger.debug(
                    f"Applied padding of {padding_value}pt to text box {element.object_id}"
                )

        # ENHANCEMENT: Apply paragraph-level styling
        self._apply_paragraph_styling(element, requests)

        # Apply custom styling from directives
        self._apply_text_color_directive(element, requests)
        self._apply_font_size_directive(element, requests)
        self._apply_background_directive(element, requests)

        # ENHANCEMENT: Apply border if specified
        self._apply_border_directive(element, requests)

        return requests

    def _handle_themed_text_element(
        self, element: TextElement, placeholder_id: str
    ) -> list[dict]:
        """
        Handle text element that should use a theme placeholder.

        Args:
            element: The text element
            placeholder_id: The ID of the placeholder to use

        Returns:
            List of request dictionaries
        """
        requests = []

        # Store the placeholder ID as the element's object_id for future reference
        element.object_id = placeholder_id

        # Only generate requests if there's text to insert
        if element.text:
            # Delete any existing text in the placeholder first
            delete_text_request = {
                "deleteText": {"objectId": placeholder_id, "textRange": {"type": "ALL"}}
            }
            requests.append(delete_text_request)

            # Insert the element's text into the placeholder
            insert_text_request = {
                "insertText": {
                    "objectId": placeholder_id,
                    "insertionIndex": 0,
                    "text": element.text,
                }
            }
            requests.append(insert_text_request)

            # Apply text formatting if present
            if hasattr(element, "formatting") and element.formatting:
                for text_format in element.formatting:
                    style_request = self._apply_text_formatting(
                        element_id=placeholder_id,
                        style=self._format_to_style(text_format),
                        fields=self._format_to_fields(text_format),
                        start_index=text_format.start,
                        end_index=text_format.end,
                    )
                    requests.append(style_request)

        logger.debug(
            f"Generated {len(requests)} requests for themed element {element.element_type} using placeholder {placeholder_id}"
        )
        return requests

    def _apply_paragraph_styling(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        """
        Apply paragraph-level styling based on directives.

        Args:
            element: The text element
            requests: The list of requests to append to
        """
        if not hasattr(element, "directives") or not element.directives:
            return

        paragraph_style = {}
        fields = []

        # Line spacing
        if "line-spacing" in element.directives:
            spacing = element.directives["line-spacing"]
            if isinstance(spacing, int | float) and spacing > 0:
                # API uses a structure like { spaceMultiple: 150 } for 1.5 spacing
                paragraph_style["spaceMultiple"] = spacing * 100  # API uses percentage
                fields.append("spaceMultiple")
                logger.debug(
                    f"Applied line spacing of {spacing} to element {element.object_id}"
                )

        # Space before paragraph
        if "para-spacing-before" in element.directives:
            spacing = element.directives["para-spacing-before"]
            if isinstance(spacing, int | float) and spacing >= 0:
                paragraph_style["spaceAbove"] = {"magnitude": spacing, "unit": "PT"}
                fields.append("spaceAbove")
                logger.debug(
                    f"Applied spacing before of {spacing}pt to element {element.object_id}"
                )

        # Space after paragraph
        if "para-spacing-after" in element.directives:
            spacing = element.directives["para-spacing-after"]
            if isinstance(spacing, int | float) and spacing >= 0:
                paragraph_style["spaceBelow"] = {"magnitude": spacing, "unit": "PT"}
                fields.append("spaceBelow")
                logger.debug(
                    f"Applied spacing after of {spacing}pt to element {element.object_id}"
                )

        # Start indent
        if "indent-start" in element.directives:
            indent = element.directives["indent-start"]
            if isinstance(indent, int | float) and indent >= 0:
                paragraph_style["indentStart"] = {"magnitude": indent, "unit": "PT"}
                fields.append("indentStart")
                logger.debug(
                    f"Applied start indent of {indent}pt to element {element.object_id}"
                )

        # First line indent
        if "indent-first-line" in element.directives:
            indent = element.directives["indent-first-line"]
            if isinstance(indent, int | float):
                paragraph_style["indentFirstLine"] = {"magnitude": indent, "unit": "PT"}
                fields.append("indentFirstLine")
                logger.debug(
                    f"Applied first line indent of {indent}pt to element {element.object_id}"
                )

        # If we have any paragraph styling to apply, create the request
        if paragraph_style and fields:
            para_style_request = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {"type": "ALL"},
                    "style": paragraph_style,
                    "fields": ",".join(fields),
                }
            }
            requests.append(para_style_request)

    def _apply_text_color_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        """Apply text color directive to the element."""
        if (
            not hasattr(element, "directives")
            or not element.directives
            or "color" not in element.directives
        ):
            return

        color_value = element.directives["color"]

        # Handle both string and tuple color values
        if isinstance(color_value, tuple) and len(color_value) == 2:
            # If it's a tuple, extract the color type and value
            color_type, color_value = color_value
            # Only proceed if it's a color directive with a hex value
            if color_type != "color" or not isinstance(color_value, str):
                color_value = None

        # Check if this is a theme color reference
        if isinstance(color_value, str) and not color_value.startswith("#"):
            # This might be a theme color - check if it's a valid theme color name
            theme_colors = [
                "TEXT1",
                "TEXT2",
                "BACKGROUND1",
                "BACKGROUND2",
                "ACCENT1",
                "ACCENT2",
                "ACCENT3",
                "ACCENT4",
                "ACCENT5",
                "ACCENT6",
                "HYPERLINK",
                "FOLLOWED_HYPERLINK",
            ]

            if color_value.upper() in theme_colors:
                # Use theme color reference
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"foregroundColor": {"themeColor": color_value.upper()}},
                    fields="foregroundColor.themeColor",
                    range_type="ALL",
                )
                requests.append(style_request)
                logger.debug(
                    f"Applied theme color {color_value.upper()} to element {element.object_id}"
                )
                return

        # If it's a hex color, apply it as RGB
        if isinstance(color_value, str) and color_value.startswith("#"):
            rgb = self._hex_to_rgb(color_value)
            style_request = self._apply_text_formatting(
                element_id=element.object_id,
                style={"foregroundColor": {"rgbColor": rgb}},
                fields="foregroundColor.rgbColor",
                range_type="ALL",
            )
            requests.append(style_request)
            logger.debug(f"Applied color {color_value} to element {element.object_id}")

    def _apply_font_size_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        """Apply font size directive to the element."""
        if (
            not hasattr(element, "directives")
            or not element.directives
            or "fontsize" not in element.directives
        ):
            return

        font_size = element.directives["fontsize"]
        if isinstance(font_size, int | float):
            style_request = self._apply_text_formatting(
                element_id=element.object_id,
                style={"fontSize": {"magnitude": font_size, "unit": "PT"}},
                fields="fontSize",
                range_type="ALL",
            )
            requests.append(style_request)
            logger.debug(
                f"Applied font size {font_size}pt to element {element.object_id}"
            )

    def _apply_background_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        """Apply background color directive to the element."""
        if (
            not hasattr(element, "directives")
            or not element.directives
            or "background" not in element.directives
        ):
            return

        background_directive = element.directives["background"]

        # Handle theme color reference for background
        if isinstance(
            background_directive, str
        ) and not background_directive.startswith("#"):
            theme_colors = [
                "TEXT1",
                "TEXT2",
                "BACKGROUND1",
                "BACKGROUND2",
                "ACCENT1",
                "ACCENT2",
                "ACCENT3",
                "ACCENT4",
                "ACCENT5",
                "ACCENT6",
            ]

            if background_directive.upper() in theme_colors:
                # Use theme color reference for background
                shape_properties_request = {
                    "updateShapeProperties": {
                        "objectId": element.object_id,
                        "fields": "shapeProperties.shapeBackgroundFill.solidFill.color.themeColor",
                        "shapeProperties": {
                            "shapeBackgroundFill": {
                                "solidFill": {
                                    "color": {
                                        "themeColor": background_directive.upper()
                                    }
                                }
                            }
                        },
                    }
                }
                requests.append(shape_properties_request)
                logger.debug(
                    f"Applied theme background color {background_directive.upper()} to element {element.object_id}"
                )
                return

        # Check if the directive is the tuple format from DirectiveParser
        if isinstance(background_directive, tuple) and len(background_directive) == 2:
            bg_type, bg_value = background_directive
            # Check if it's a color and the value is a string starting with #
            if (
                bg_type == "color"
                and isinstance(bg_value, str)
                and bg_value.startswith("#")
            ):
                try:
                    rgb = self._hex_to_rgb(bg_value)
                    # Generate the API request to update the shape's background fill
                    shape_properties_request = {
                        "updateShapeProperties": {
                            "objectId": element.object_id,
                            "fields": "shapeProperties.shapeBackgroundFill.solidFill.color.rgbColor",
                            "shapeProperties": {
                                "shapeBackgroundFill": {
                                    "solidFill": {"color": {"rgbColor": rgb}}
                                }
                            },
                        }
                    }
                    requests.append(shape_properties_request)
                    logger.debug(
                        f"Applied background color {bg_value} to element {element.object_id}"
                    )
                except ValueError as e:
                    logger.warning(
                        f"Invalid hex color '{bg_value}' for background directive: {e}"
                    )

    def _apply_border_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        """
        Apply border directive to the element.

        Handles formats like:
        - [border=1pt solid #FF0000]
        - [border=dashed blue]
        """
        if (
            not hasattr(element, "directives")
            or not element.directives
            or "border" not in element.directives
        ):
            return

        border_value = element.directives["border"]
        if not isinstance(border_value, str):
            return

        # Parse border value: width style color
        parts = border_value.split()

        # Default values
        weight = {"magnitude": 1, "unit": "PT"}
        dash_style = "SOLID"
        color = {"rgbColor": {"red": 0, "green": 0, "blue": 0}}
        fields = []

        # Process parts
        for part in parts:
            # Check if it's a width specification
            if part.endswith("pt") or part.endswith("px"):
                try:
                    width_value = float(part.rstrip("ptx"))
                    weight = {"magnitude": width_value, "unit": "PT"}
                    fields.append("outline.weight")
                except ValueError:
                    pass
            # Check if it's a style specification
            elif part.lower() in ["solid", "dashed", "dotted"]:
                style_map = {
                    "solid": "SOLID",
                    "dashed": "DASH",
                    "dotted": "DOT",
                }
                dash_style = style_map.get(part.lower(), "SOLID")
                fields.append("outline.dashStyle")
            # Check if it's a color specification
            elif part.startswith("#"):
                try:
                    rgb = self._hex_to_rgb(part)
                    color = {"rgbColor": rgb}
                    fields.append("outline.outlineFill.solidFill.color.rgbColor")
                except ValueError:
                    pass
            # Check if it's a named color
            elif part.lower() in [
                "black",
                "white",
                "red",
                "green",
                "blue",
                "yellow",
                "cyan",
                "magenta",
            ]:
                # Map named colors to RGB
                color_map = {
                    "black": {"red": 0, "green": 0, "blue": 0},
                    "white": {"red": 1, "green": 1, "blue": 1},
                    "red": {"red": 1, "green": 0, "blue": 0},
                    "green": {"red": 0, "green": 1, "blue": 0},
                    "blue": {"red": 0, "green": 0, "blue": 1},
                    "yellow": {"red": 1, "green": 1, "blue": 0},
                    "cyan": {"red": 0, "green": 1, "blue": 1},
                    "magenta": {"red": 1, "green": 0, "blue": 1},
                }
                color = {"rgbColor": color_map.get(part.lower())}
                fields.append("outline.outlineFill.solidFill.color.rgbColor")
            # Check if it's a theme color
            elif part.upper() in [
                "TEXT1",
                "TEXT2",
                "BACKGROUND1",
                "BACKGROUND2",
                "ACCENT1",
                "ACCENT2",
                "ACCENT3",
                "ACCENT4",
                "ACCENT5",
                "ACCENT6",
            ]:
                color = {"themeColor": part.upper()}
                fields.append("outline.outlineFill.solidFill.color.themeColor")

        # If we have enough information, create the border request
        if fields:
            border_request = {
                "updateShapeProperties": {
                    "objectId": element.object_id,
                    "fields": ",".join(fields),
                    "shapeProperties": {
                        "outline": {
                            "outlineFill": {"solidFill": {"color": color}},
                            "weight": weight,
                            "dashStyle": dash_style,
                        }
                    },
                }
            }
            requests.append(border_request)
            logger.debug(
                f"Applied border style to element {element.object_id}: {border_value}"
            )
