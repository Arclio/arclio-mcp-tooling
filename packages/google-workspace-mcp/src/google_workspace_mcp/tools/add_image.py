"""
Precise Google Slides Image Positioning - Python Implementation
Uses your existing BaseGoogleService infrastructure for authentication.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google_workspace_mcp.app import mcp  # Import from central app module
from google_workspace_mcp.services.base import BaseGoogleService
from google_workspace_mcp.utils.unit_conversion import convert_template_zone_coordinates

logger = logging.getLogger(__name__)


@dataclass
class ImageZone:
    """Represents a positioning zone for images on a slide."""

    x: int  # EMU coordinates
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to Google Slides API format."""
        return {
            "size": {
                "width": {"magnitude": self.width, "unit": "EMU"},
                "height": {"magnitude": self.height, "unit": "EMU"},
            },
            "transform": {
                "scaleX": 1,
                "scaleY": 1,
                "translateX": self.x,
                "translateY": self.y,
                "unit": "EMU",
            },
        }


class PreciseSlidesPositioning(BaseGoogleService):
    """
    Precise image positioning for Google Slides using EMU coordinates.
    Extends your existing BaseGoogleService for consistent authentication.
    """

    def __init__(self):
        super().__init__("slides", "v1")

    @staticmethod
    def inches_to_emu(inches: float) -> int:
        """Convert inches to EMU (English Metric Units). 1 inch = 914,400 EMU."""
        return int(inches * 914400)

    @staticmethod
    def emu_to_inches(emu: int) -> float:
        """Convert EMU to inches for human-readable dimensions."""
        return emu / 914400

    def get_template_zones(self) -> Dict[str, ImageZone]:
        """
        Define the positioning zones based on your template layout.
        Standard Google Slides: 10" x 5.625" (widescreen 16:9)
        """
        slide_width = self.inches_to_emu(10)
        slide_height = self.inches_to_emu(5.625)

        zones = {
            # Full slide background
            "background": ImageZone(x=0, y=0, width=slide_width, height=slide_height),
            # Title area (top section)
            "title": ImageZone(
                x=self.inches_to_emu(0.5),
                y=self.inches_to_emu(0.3),
                width=self.inches_to_emu(9),
                height=self.inches_to_emu(0.8),
            ),
            # Left content area (copy block)
            "left_content": ImageZone(
                x=self.inches_to_emu(0.5),
                y=self.inches_to_emu(1.3),
                width=self.inches_to_emu(4),
                height=self.inches_to_emu(3.8),
            ),
            # Right image block (your main focus)
            "right_image_block": ImageZone(
                x=self.inches_to_emu(5),
                y=self.inches_to_emu(1.3),
                width=self.inches_to_emu(4.5),
                height=self.inches_to_emu(3.8),
            ),
        }

        return zones

    def add_background_image(
        self, presentation_id: str, slide_id: str, image_url: str
    ) -> Dict[str, Any]:
        """
        Add a background image that fills the entire slide.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            image_url: Publicly accessible URL of the background image

        Returns:
            API response or error details
        """
        try:
            zones = self.get_template_zones()
            background_zone = zones["background"]

            object_id = f"background_{int(__import__('time').time() * 1000)}"

            requests = [
                {
                    "createImage": {
                        "objectId": object_id,
                        "url": image_url,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            **background_zone.to_dict(),
                        },
                    }
                }
            ]

            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"Background image added successfully: {object_id}")
            return {
                "success": True,
                "object_id": object_id,
                "zone": "background",
                "response": response,
            }

        except Exception as error:
            return self.handle_api_error("add_background_image", error)

    def add_right_side_image(
        self, presentation_id: str, slide_id: str, image_url: str
    ) -> Dict[str, Any]:
        """
        Add an image to the right image block with precise positioning.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            image_url: Publicly accessible URL of the portrait image

        Returns:
            API response or error details
        """
        try:
            zones = self.get_template_zones()
            right_zone = zones["right_image_block"]

            object_id = f"right_image_{int(__import__('time').time() * 1000)}"

            requests = [
                {
                    "createImage": {
                        "objectId": object_id,
                        "url": image_url,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            **right_zone.to_dict(),
                        },
                    }
                }
            ]

            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"Right side image added successfully: {object_id}")
            return {
                "success": True,
                "object_id": object_id,
                "zone": "right_image_block",
                "response": response,
            }

        except Exception as error:
            return self.handle_api_error("add_right_side_image", error)

    def add_image_to_zone(
        self,
        presentation_id: str,
        slide_id: str,
        image_url: str,
        zone_name: str,
        custom_zone: Optional[ImageZone] = None,
    ) -> Dict[str, Any]:
        """
        Add an image to any specified zone with precise positioning.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            image_url: Publicly accessible URL of the image
            zone_name: Name of predefined zone or 'custom'
            custom_zone: Custom ImageZone if zone_name is 'custom'

        Returns:
            API response or error details
        """
        try:
            if zone_name == "custom" and custom_zone:
                zone = custom_zone
            else:
                zones = self.get_template_zones()
                if zone_name not in zones:
                    raise ValueError(
                        f"Unknown zone: {zone_name}. Available: {list(zones.keys())}"
                    )
                zone = zones[zone_name]

            object_id = f"{zone_name}_{int(__import__('time').time() * 1000)}"

            requests = [
                {
                    "createImage": {
                        "objectId": object_id,
                        "url": image_url,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            **zone.to_dict(),
                        },
                    }
                }
            ]

            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"Image added to {zone_name} successfully: {object_id}")
            return {
                "success": True,
                "object_id": object_id,
                "zone": zone_name,
                "response": response,
            }

        except Exception as error:
            return self.handle_api_error("add_image_to_zone", error)

    def get_existing_element_positions(
        self, presentation_id: str, slide_id: str
    ) -> Dict[str, Any]:
        """
        Extract exact positions, dimensions, and content of existing elements from a template slide.
        Use this to reverse-engineer your template coordinates and understand element content.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide

        Returns:
            Dictionary of element positions, content, and metadata or error details
        """
        try:
            response = (
                self.service.presentations()
                .pages()
                .get(presentationId=presentation_id, pageObjectId=slide_id)
                .execute()
            )

            elements = response.get("pageElements", [])
            positions = {}

            for element in elements:
                if "objectId" in element:
                    obj_id = element["objectId"]

                    # Get basic positioning info
                    size = element.get("size", {})
                    transform = element.get("transform", {})

                    # Determine element type and extract content
                    element_info = self._extract_element_content(element)

                    # Get scaling factors
                    scale_x = transform.get("scaleX", 1)
                    scale_y = transform.get("scaleY", 1)

                    # Calculate actual visual positions
                    actual_pos = self.calculate_actual_position(
                        transform.get("translateX", 0),
                        transform.get("translateY", 0),
                        size.get("width", {}).get("magnitude", 0),
                        size.get("height", {}).get("magnitude", 0),
                        scale_x,
                        scale_y,
                    )

                    positions[obj_id] = {
                        # Raw position and size data
                        "x_emu": transform.get("translateX", 0),
                        "y_emu": transform.get("translateY", 0),
                        "width_emu": size.get("width", {}).get("magnitude", 0),
                        "height_emu": size.get("height", {}).get("magnitude", 0),
                        "x_inches": self.emu_to_inches(transform.get("translateX", 0)),
                        "y_inches": self.emu_to_inches(transform.get("translateY", 0)),
                        "width_inches": self.emu_to_inches(
                            size.get("width", {}).get("magnitude", 0)
                        ),
                        "height_inches": self.emu_to_inches(
                            size.get("height", {}).get("magnitude", 0)
                        ),
                        "scaleX": scale_x,
                        "scaleY": scale_y,
                        # Actual visual positions (accounting for scaling)
                        **actual_pos,
                        # Content and type information
                        **element_info,
                    }

            logger.info(
                f"Retrieved positions and content for {len(positions)} elements"
            )
            return {"success": True, "elements": positions, "slide_id": slide_id}

        except Exception as error:
            return self.handle_api_error("get_existing_element_positions", error)

    def _extract_element_content(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract content and metadata from a slide element.

        Args:
            element: Raw element data from Google Slides API

        Returns:
            Dictionary with element type, content, and metadata
        """
        element_info = {
            "element_type": "unknown",
            "content": None,
            "content_type": None,
            "metadata": {},
            "raw_element_keys": list(element.keys()),  # Debug: show all available keys
        }

        # Text box or shape with text
        if "shape" in element:
            element_info["element_type"] = "shape"
            shape = element["shape"]

            # Get shape type
            shape_type = shape.get("shapeType", "UNSPECIFIED")
            element_info["metadata"]["shape_type"] = shape_type

            # Extract text content
            if "text" in shape:
                text_content = self._extract_text_content(shape["text"])
                element_info["content"] = text_content["text"]
                element_info["content_type"] = "text"
                element_info["metadata"]["text_formatting"] = text_content["formatting"]
            else:
                element_info["content_type"] = "shape_no_text"

        # Image element
        elif "image" in element:
            element_info["element_type"] = "image"
            element_info["content_type"] = "image"
            image = element["image"]

            # Get image properties
            element_info["content"] = image.get("sourceUrl", "No URL available")
            element_info["metadata"] = {
                "image_properties": image.get("imageProperties", {}),
                "content_url": image.get("contentUrl", None),
            }

        # Line element
        elif "line" in element:
            element_info["element_type"] = "line"
            element_info["content_type"] = "line"
            line = element["line"]
            element_info["metadata"] = {
                "line_type": line.get("lineType", "UNKNOWN"),
                "line_properties": line.get("lineProperties", {}),
            }

        # Video element
        elif "video" in element:
            element_info["element_type"] = "video"
            element_info["content_type"] = "video"
            video = element["video"]
            element_info["content"] = video.get("url", "No URL available")
            element_info["metadata"] = {
                "video_properties": video.get("videoProperties", {})
            }

        # Table element
        elif "table" in element:
            element_info["element_type"] = "table"
            element_info["content_type"] = "table"
            table = element["table"]

            # Extract table structure and content
            table_content = self._extract_table_content(table)
            element_info["content"] = table_content
            element_info["metadata"] = {
                "rows": table.get("rows", 0),
                "columns": table.get("columns", 0),
            }

        # Group element
        elif "elementGroup" in element:
            element_info["element_type"] = "group"
            element_info["content_type"] = "group"
            group = element["elementGroup"]
            element_info["metadata"] = {
                "children_count": len(group.get("children", [])),
                "children_ids": [
                    child.get("objectId") for child in group.get("children", [])
                ],
            }

        # Placeholder or other special elements
        if "placeholder" in element:
            placeholder = element["placeholder"]
            element_info["metadata"]["placeholder"] = {
                "type": placeholder.get("type", "UNKNOWN"),
                "index": placeholder.get("index", 0),
            }

        return element_info

    def _extract_text_content(self, text_element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text content and formatting from a text element.

        Args:
            text_element: Text element from Google Slides API

        Returns:
            Dictionary with text content and formatting information
        """
        text_content = {"text": "", "formatting": []}

        text_runs = text_element.get("textElements", [])

        for text_run in text_runs:
            if "textRun" in text_run:
                run = text_run["textRun"]
                content = run.get("content", "")
                text_content["text"] += content

                # Extract formatting if available
                style = run.get("style", {})
                if style:
                    text_content["formatting"].append(
                        {
                            "content": content,
                            "font_family": style.get("fontFamily", ""),
                            "font_size": style.get("fontSize", {}).get("magnitude", 0),
                            "bold": style.get("bold", False),
                            "italic": style.get("italic", False),
                            "foreground_color": style.get("foregroundColor", {}),
                            "background_color": style.get("backgroundColor", {}),
                        }
                    )

            elif "autoText" in text_run:
                # Handle auto text (like slide numbers, dates, etc.)
                auto_text = text_run["autoText"]
                text_content["text"] += f"[AUTO: {auto_text.get('type', 'UNKNOWN')}]"

        return text_content

    def _extract_table_content(self, table_element: Dict[str, Any]) -> List[List[str]]:
        """
        Extract content from table cells.

        Args:
            table_element: Table element from Google Slides API

        Returns:
            2D list representing table content
        """
        table_content = []

        table_rows = table_element.get("tableRows", [])
        for row in table_rows:
            row_content = []
            table_cells = row.get("tableCells", [])

            for cell in table_cells:
                cell_text = ""
                if "text" in cell:
                    cell_text_data = self._extract_text_content(cell["text"])
                    cell_text = cell_text_data["text"].strip()
                row_content.append(cell_text)

            table_content.append(row_content)

        return table_content

    def calculate_actual_position(
        self,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> Dict[str, float]:
        """
        Calculate the actual visual position and size considering scaling.

        Args:
            x_emu, y_emu: Position in EMU
            width_emu, height_emu: Size in EMU
            scale_x, scale_y: Scaling factors

        Returns:
            Dictionary with actual positions and sizes in inches
        """
        return {
            "actual_x_inches": self.emu_to_inches(x_emu),
            "actual_y_inches": self.emu_to_inches(y_emu),
            "actual_width_inches": self.emu_to_inches(width_emu) * scale_x,
            "actual_height_inches": self.emu_to_inches(height_emu) * scale_y,
            "visual_right_edge_inches": self.emu_to_inches(x_emu)
            + (self.emu_to_inches(width_emu) * scale_x),
            "visual_bottom_edge_inches": self.emu_to_inches(y_emu)
            + (self.emu_to_inches(height_emu) * scale_y),
        }

    def implement_complete_template(
        self,
        presentation_id: str,
        slide_id: str,
        background_url: str,
        portrait_url: str,
    ) -> Dict[str, Any]:
        """
        Implement your complete template with background and portrait images.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            background_url: URL for background image (https://i.ibb.co/4RXQbYGB/IMG-7774.jpg)
            portrait_url: URL for portrait image (https://i.ibb.co/HLWpZmPS/20250122-KEVI4992-kevinostaj.jpg)

        Returns:
            Combined results or error details
        """
        try:
            results = {"success": True, "operations": []}

            # Step 1: Add background image
            bg_result = self.add_background_image(
                presentation_id, slide_id, background_url
            )
            results["operations"].append(bg_result)

            if not bg_result.get("success", False):
                logger.error(
                    "Background image failed, stopping template implementation"
                )
                return bg_result

            # Step 2: Add portrait image to right block
            portrait_result = self.add_right_side_image(
                presentation_id, slide_id, portrait_url
            )
            results["operations"].append(portrait_result)

            if not portrait_result.get("success", False):
                logger.error("Portrait image failed")
                results["success"] = False

            # Step 3: Return zone information for reference
            zones = self.get_template_zones()
            results["template_zones"] = {
                name: {
                    "x_inches": self.emu_to_inches(zone.x),
                    "y_inches": self.emu_to_inches(zone.y),
                    "width_inches": self.emu_to_inches(zone.width),
                    "height_inches": self.emu_to_inches(zone.height),
                }
                for name, zone in zones.items()
            }

            logger.info("Template implementation completed successfully")
            return results

        except Exception as error:
            return self.handle_api_error("implement_complete_template", error)

    def extract_template_zones_by_text(
        self, presentation_id: str, slide_id: str, unit: str = "EMU"
    ) -> Dict[str, Any]:
        """
        Extract positioning zones from a template slide by finding placeholder text elements.
        This gives us the exact coordinates where content should be placed.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the template slide
            unit: Target unit for coordinates ("EMU", "PT", or "INCHES"). Default is "EMU".

        Returns:
            Dictionary with zone information including coordinates in both EMU and specified unit
        """
        try:
            # Validate unit parameter
            if unit not in ["EMU", "PT", "INCHES"]:
                raise ValueError("unit must be 'EMU', 'PT', or 'INCHES'")

            elements_result = self.get_existing_element_positions(
                presentation_id, slide_id
            )

            if not elements_result.get("success"):
                return {"error": "Failed to read template slide"}

            elements = elements_result["elements"]
            template_zones = {}

            # Keywords to look for in template text (case-insensitive)
            zone_keywords = {
                "image block": "image_block",
                "background image": "background_image",
                "full-bleed background": "background_image",
                "copy block": "copy_block",
                "slide copy block": "slide_copy",
                "press recap slide title": "press_recap_slide_title",
                "slide title": "slide_title",
                "logo": "logo_area",
                "brand": "logo_area",
                # Add more keywords for stat blocks and phone images
                "stat a": "stat_a",
                "stat b": "stat_b",
                "stat c": "stat_c",
                "stat d": "stat_d",
                "phone image a": "phone_image_a",
                "phone image b": "phone_image_b",
                "phone image c": "phone_image_c",
                "phone image title a": "phone_image_title_a",
                "phone image title b": "phone_image_title_b",
                "phone image title c": "phone_image_title_c",
                "image title": "image_title",
                "data table a": "data_table_a",
                "data table b": "data_table_b",
                "data summary copy block": "data_summary_copy_block",
                "table title": "table_title",
                "summary slide title": "summary_slide_title",
                "summary slide copy block": "summary_slide_copy_block",
                "thank you copy": "thank_you_copy",
                "graph a": "graph_a",
                "graph b": "graph_b",
                "graph title": "graph_title",
            }

            # Scan all text elements for template keywords
            for element_id, element_info in elements.items():
                if element_info.get("content_type") == "text" and element_info.get(
                    "content"
                ):
                    content = element_info["content"].lower().strip()

                    # Check if this text element matches any template zone
                    for keyword, zone_name in zone_keywords.items():
                        if keyword in content:
                            # Use actual visual dimensions if element is scaled
                            x_inches = element_info.get("x_inches", 0)
                            y_inches = element_info.get("y_inches", 0)

                            if element_info.get(
                                "actual_width_inches"
                            ) and element_info.get("actual_height_inches"):
                                width_inches = element_info["actual_width_inches"]
                                height_inches = element_info["actual_height_inches"]
                            else:
                                width_inches = element_info.get("width_inches", 0)
                                height_inches = element_info.get("height_inches", 0)

                            # Base zone data with EMU and inches coordinates
                            zone_data = {
                                "zone_name": zone_name,
                                "original_text": element_info["content"],
                                "element_id": element_id,
                                # Coordinates in inches (human readable)
                                "x_inches": x_inches,
                                "y_inches": y_inches,
                                "width_inches": width_inches,
                                "height_inches": height_inches,
                                # Coordinates in EMU (for API calls)
                                "x_emu": self.inches_to_emu(x_inches),
                                "y_emu": self.inches_to_emu(y_inches),
                                "width_emu": self.inches_to_emu(width_inches),
                                "height_emu": self.inches_to_emu(height_inches),
                                # Scaling info
                                "scale_x": element_info.get("scaleX", 1),
                                "scale_y": element_info.get("scaleY", 1),
                                # ImageZone object for easy use
                                "image_zone": ImageZone(
                                    x=self.inches_to_emu(x_inches),
                                    y=self.inches_to_emu(y_inches),
                                    width=self.inches_to_emu(width_inches),
                                    height=self.inches_to_emu(height_inches),
                                ),
                            }

                            # Add coordinates in the requested unit if not EMU
                            if unit != "EMU":
                                zone_data = convert_template_zone_coordinates(
                                    zone_data, unit
                                )

                            # Handle duplicate zone names by adding a counter
                            unique_zone_name = zone_name
                            counter = 2
                            while unique_zone_name in template_zones:
                                unique_zone_name = f"{zone_name}_{counter}"
                                counter += 1

                            template_zones[unique_zone_name] = zone_data

                            unit_suffix = unit.lower() if unit != "EMU" else "emu"
                            width_key = (
                                f"width_{unit_suffix}" if unit != "EMU" else "width_emu"
                            )
                            height_key = (
                                f"height_{unit_suffix}"
                                if unit != "EMU"
                                else "height_emu"
                            )
                            x_key = f"x_{unit_suffix}" if unit != "EMU" else "x_emu"
                            y_key = f"y_{unit_suffix}" if unit != "EMU" else "y_emu"

                            width_val = zone_data.get(width_key, width_inches)
                            height_val = zone_data.get(height_key, height_inches)
                            x_val = zone_data.get(x_key, x_inches)
                            y_val = zone_data.get(y_key, y_inches)

                            logger.info(
                                f"🎯 Found template zone '{unique_zone_name}' from text '{content}': {width_val:.2f} {unit}×{height_val:.2f} {unit} at ({x_val:.2f} {unit}, {y_val:.2f} {unit})"
                            )
                            break  # Found a match, move to next element

            return {
                "success": True,
                "zones": template_zones,
                "slide_id": slide_id,
                "unit": unit,
            }

        except Exception as error:
            return self.handle_api_error("extract_template_zones_by_text", error)

    def place_image_in_template_zone(
        self,
        presentation_id: str,
        slide_id: str,
        zone_name: str,
        image_url: str,
        template_zones: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Place an image in a specific template zone, replacing the placeholder text.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            zone_name: Name of the template zone (e.g., "image_block")
            image_url: URL of the image to place
            template_zones: Template zones extracted from extract_template_zones_by_text()

        Returns:
            API response or error details
        """
        try:
            zones = template_zones.get("zones", {})
            if zone_name not in zones:
                raise ValueError(
                    f"Zone '{zone_name}' not found in template. Available zones: {list(zones.keys())}"
                )

            zone_info = zones[zone_name]
            image_zone = zone_info["image_zone"]

            object_id = f"{zone_name}_{int(__import__('time').time() * 1000)}"

            requests = [
                {
                    "createImage": {
                        "objectId": object_id,
                        "url": image_url,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            **image_zone.to_dict(),
                        },
                    }
                }
            ]

            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"✅ Image placed in '{zone_name}' zone: {object_id}")
            logger.info(
                f"📍 Position: {zone_info['width_inches']:.2f}\"×{zone_info['height_inches']:.2f}\" at ({zone_info['x_inches']:.2f}\", {zone_info['y_inches']:.2f}\")"
            )

            return {
                "success": True,
                "object_id": object_id,
                "zone_name": zone_name,
                "zone_info": zone_info,
                "response": response,
            }

        except Exception as error:
            return self.handle_api_error("place_image_in_template_zone", error)

    def create_presentation(self, title: str) -> Dict[str, Any]:
        """
        Create a new Google Slides presentation.

        Args:
            title: The title of the presentation

        Returns:
            Presentation details or error information
        """
        try:
            presentation = {"title": title}

            response = self.service.presentations().create(body=presentation).execute()

            presentation_id = response["presentationId"]
            logger.info(f"Presentation created successfully: {presentation_id}")

            return {
                "success": True,
                "presentation_id": presentation_id,
                "title": title,
                "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                "response": response,
            }

        except Exception as error:
            return self.handle_api_error("create_presentation", error)

    def create_slide(
        self, presentation_id: str, layout: str = "BLANK"
    ) -> Dict[str, Any]:
        """
        Create a new slide in an existing presentation.

        Args:
            presentation_id: The ID of the presentation
            layout: Layout type ('BLANK', 'TITLE_AND_BODY', 'TITLE_ONLY', etc.)

        Returns:
            Slide details or error information
        """
        try:
            slide_id = f"slide_{int(__import__('time').time() * 1000)}"

            requests = [
                {
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {"predefinedLayout": layout},
                    }
                }
            ]

            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"Slide created successfully: {slide_id}")

            return {
                "success": True,
                "slide_id": slide_id,
                "layout": layout,
                "response": response,
            }

        except Exception as error:
            return self.handle_api_error("create_slide", error)

    def create_presentation_with_slides(
        self, title: str, slide_count: int = 2
    ) -> Dict[str, Any]:
        """
        Create a presentation with multiple blank slides.

        Args:
            title: The title of the presentation
            slide_count: Number of slides to create (default: 2)

        Returns:
            Complete presentation setup details
        """
        try:
            # Create presentation
            pres_result = self.create_presentation(title)
            if not pres_result.get("success"):
                return pres_result

            presentation_id = pres_result["presentation_id"]
            slides = []

            # Create additional slides (presentation starts with one slide)
            for i in range(
                slide_count - 1
            ):  # -1 because presentation has one slide already
                slide_result = self.create_slide(presentation_id, "BLANK")
                if slide_result.get("success"):
                    slides.append(slide_result)
                else:
                    logger.warning(f"Failed to create slide {i+2}: {slide_result}")

            # Get the first slide ID (already exists)
            pres_details = (
                self.service.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )

            first_slide_id = pres_details["slides"][0]["objectId"]
            slides.insert(
                0, {"success": True, "slide_id": first_slide_id, "layout": "BLANK"}
            )

            logger.info(f"Presentation with {len(slides)} slides created successfully")

            return {
                "success": True,
                "presentation_id": presentation_id,
                "title": title,
                "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                "slides": slides,
                "slide_ids": [
                    slide["slide_id"] for slide in slides if slide.get("success")
                ],
            }

        except Exception as error:
            return self.handle_api_error("create_presentation_with_slides", error)

    def implement_multi_slide_template(
        self,
        presentation_id: str,
        slide_ids: list,
        background_url: str,
        portrait_url: str,
    ) -> Dict[str, Any]:
        """
        Implement template across multiple slides - background on first slide, portrait on second.

        Args:
            presentation_id: The ID of the presentation
            slide_ids: List of slide IDs [background_slide_id, portrait_slide_id]
            background_url: URL for background image
            portrait_url: URL for portrait image

        Returns:
            Results for all slide operations
        """
        try:
            if len(slide_ids) < 2:
                raise ValueError("Need at least 2 slide IDs for multi-slide template")

            results = {"success": True, "operations": []}

            # Slide 1: Background image (full slide)
            bg_result = self.add_background_image(
                presentation_id, slide_ids[0], background_url
            )
            results["operations"].append(
                {
                    "slide": 1,
                    "slide_id": slide_ids[0],
                    "type": "background",
                    "result": bg_result,
                }
            )

            # Slide 2: Portrait image in right block
            portrait_result = self.add_right_side_image(
                presentation_id, slide_ids[1], portrait_url
            )
            results["operations"].append(
                {
                    "slide": 2,
                    "slide_id": slide_ids[1],
                    "type": "portrait_right",
                    "result": portrait_result,
                }
            )

            # Check if any operations failed
            failed_ops = [
                op for op in results["operations"] if not op["result"].get("success")
            ]
            if failed_ops:
                results["success"] = False
                results["failed_operations"] = failed_ops

            logger.info(
                f"Multi-slide template implemented across {len(slide_ids)} slides"
            )
            return results

        except Exception as error:
            return self.handle_api_error("implement_multi_slide_template", error)

    def create_complete_presentation_workflow(
        self, title: str, background_url: str, portrait_url: str
    ) -> Dict[str, Any]:
        """
        Complete workflow: Create presentation, create slides, add images to separate slides.

        Args:
            title: The title of the presentation
            background_url: URL for background image (first slide)
            portrait_url: URL for portrait image (second slide)

        Returns:
            Complete workflow results
        """
        try:
            # Step 1: Create presentation with 2 slides
            pres_result = self.create_presentation_with_slides(title, slide_count=2)
            if not pres_result.get("success"):
                return pres_result

            presentation_id = pres_result["presentation_id"]
            slide_ids = pres_result["slide_ids"]

            # Step 2: Implement template across slides
            template_result = self.implement_multi_slide_template(
                presentation_id, slide_ids, background_url, portrait_url
            )

            # Step 3: Combine results
            final_result = {
                "success": template_result.get("success", False),
                "presentation_id": presentation_id,
                "title": pres_result["title"],
                "url": pres_result["url"],
                "slides": {
                    "slide_1": {
                        "slide_id": slide_ids[0],
                        "content": "background_image",
                        "url": f"{pres_result['url']}#slide=id.{slide_ids[0]}",
                    },
                    "slide_2": {
                        "slide_id": slide_ids[1],
                        "content": "portrait_image",
                        "url": f"{pres_result['url']}#slide=id.{slide_ids[1]}",
                    },
                },
                "template_operations": template_result.get("operations", []),
            }

            logger.info(f"Complete presentation workflow finished: {presentation_id}")
            return final_result

        except Exception as error:
            return self.handle_api_error("create_complete_presentation_workflow", error)

    @staticmethod
    def extract_presentation_id_from_url(url: str) -> str:
        """
        Extract presentation ID from Google Slides URL.

        Args:
            url: Google Slides URL

        Returns:
            Presentation ID

        Raises:
            ValueError: If URL format is invalid
        """
        # Pattern to match Google Slides URLs
        pattern = r"/presentation/d/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, url)

        if not match:
            raise ValueError(f"Invalid Google Slides URL format: {url}")

        return match.group(1)

    def get_presentation_slides(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get all slides from a presentation with their IDs and basic info.

        Args:
            presentation_id: The ID of the presentation

        Returns:
            Dictionary with slide information or error details
        """
        try:
            response = (
                self.service.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )

            slides_info = []
            for i, slide in enumerate(response.get("slides", [])):
                slides_info.append(
                    {
                        "slide_number": i + 1,
                        "slide_id": slide["objectId"],
                        "layout": slide.get("slideProperties", {}).get(
                            "masterObjectId", "unknown"
                        ),
                    }
                )

            logger.info(f"Retrieved {len(slides_info)} slides from presentation")
            return {
                "success": True,
                "presentation_id": presentation_id,
                "presentation_title": response.get("title", "Unknown"),
                "slides": slides_info,
                "total_slides": len(slides_info),
            }

        except Exception as error:
            return self.handle_api_error("get_presentation_slides", error)

    def get_elements_from_specific_slides(
        self, presentation_id: str, slide_numbers: List[int]
    ) -> Dict[str, Any]:
        """
        Get element positions from specific slides by slide number.

        Args:
            presentation_id: The ID of the presentation
            slide_numbers: List of slide numbers (1-indexed)

        Returns:
            Dictionary with elements from specified slides or error details
        """
        try:
            # First get all slides to map numbers to IDs
            slides_result = self.get_presentation_slides(presentation_id)
            if not slides_result.get("success"):
                return slides_result

            slides_info = slides_result["slides"]
            results = {
                "success": True,
                "presentation_id": presentation_id,
                "slides_analyzed": [],
            }

            for slide_num in slide_numbers:
                if slide_num < 1 or slide_num > len(slides_info):
                    logger.warning(
                        f"Slide number {slide_num} is out of range (1-{len(slides_info)})"
                    )
                    continue

                slide_info = slides_info[slide_num - 1]  # Convert to 0-indexed
                slide_id = slide_info["slide_id"]

                # Get elements from this slide
                elements_result = self.get_existing_element_positions(
                    presentation_id, slide_id
                )

                slide_data = {
                    "slide_number": slide_num,
                    "slide_id": slide_id,
                    "elements_found": (
                        len(elements_result.get("elements", {}))
                        if elements_result.get("success")
                        else 0
                    ),
                    "elements": elements_result.get("elements", {}),
                    "success": elements_result.get("success", False),
                }

                if elements_result.get("success"):
                    logger.info(
                        f"Retrieved {slide_data['elements_found']} elements from slide {slide_num}"
                    )
                else:
                    logger.error(
                        f"Failed to get elements from slide {slide_num}: {elements_result}"
                    )

                results["slides_analyzed"].append(slide_data)

            return results

        except Exception as error:
            return self.handle_api_error("get_elements_from_specific_slides", error)


# @mcp.tool(
#     name="analyze_presentation_layout",
# )
async def analyze_presentation_layout(
    presentation_url: str = "https://docs.google.com/presentation/d/1tdBZ0MH-CGiV2VmEptS7h0PfIyXOp3_yXN_AkNzgpTc/edit?slide=id.g360952048d5_0_86#slide=id.g360952048d5_0_86",
) -> Dict[str, Any]:
    """
    Get a comprehensive overview of all slides in a presentation.

    Args:
        presentation_url: Google Slides URL (defaults to the provided template)

    Returns:
        Dictionary with all slides and their basic information
    """
    try:
        # Initialize the service
        positioner = PreciseSlidesPositioning()

        # Extract presentation ID from URL
        presentation_id = positioner.extract_presentation_id_from_url(presentation_url)
        logger.info(f"Analyzing presentation: {presentation_id}")

        # Get all slides
        slides_result = positioner.get_presentation_slides(presentation_id)

        if slides_result.get("success"):
            logger.info(
                f"✅ Found {slides_result['total_slides']} slides in presentation"
            )
            logger.info(f"📝 Presentation: '{slides_result['presentation_title']}'")

            # Get basic content from each slide
            for slide_info in slides_result["slides"]:
                slide_num = slide_info["slide_number"]
                slide_id = slide_info["slide_id"]

                # Get first few elements to understand slide content
                elements_result = positioner.get_existing_element_positions(
                    presentation_id, slide_id
                )

                if elements_result.get("success"):
                    elements = elements_result["elements"]
                    text_elements = []

                    # Extract text content from elements to identify slide purpose
                    for element_id, element_info in list(elements.items())[
                        :3
                    ]:  # First 3 elements
                        if element_info.get(
                            "content_type"
                        ) == "text" and element_info.get("content"):
                            text_content = element_info["content"].strip()
                            if (
                                text_content and len(text_content) < 100
                            ):  # Short text likely to be titles
                                text_elements.append(text_content)

                    slide_info["sample_text"] = text_elements
                    slide_info["total_elements"] = len(elements)

                    logger.info(
                        f"📄 Slide {slide_num}: {slide_info['total_elements']} elements"
                    )
                    if text_elements:
                        logger.info(
                            f"   📝 Sample text: {', '.join(text_elements[:2])}"
                        )

            return slides_result
        else:
            logger.error(f"❌ Failed to analyze presentation: {slides_result}")
            raise ValueError(f"Failed to analyze presentation: {slides_result}")

    except Exception as error:
        logger.error(f"Error in analyze_presentation_layout: {error}")
        raise ValueError(f"Error analyzing presentation: {error}")


# @mcp.tool(
#     name="get_template_elements_from_slides",
# )
async def get_template_elements_from_slides(
    presentation_url: str = "https://docs.google.com/presentation/d/1tdBZ0MH-CGiV2VmEptS7h0PfIyXOp3_yXN_AkNzgpTc/edit?slide=id.g360952048d5_0_86#slide=id.g360952048d5_0_86",
    slide_numbers: str = "4,5",
) -> Dict[str, Any]:
    """
    Extract element positions from specific slides in a template presentation.

    Args:
        presentation_url: Google Slides URL (defaults to the provided template)
        slide_numbers: Comma-separated slide numbers to analyze (e.g., "4,5")

    Returns:
        Dictionary with element positions and dimensions from specified slides
    """
    try:
        # Initialize the service
        positioner = PreciseSlidesPositioning()

        # Extract presentation ID from URL
        presentation_id = positioner.extract_presentation_id_from_url(presentation_url)
        logger.info(f"Extracted presentation ID: {presentation_id}")

        # Parse slide numbers
        slide_nums = [int(num.strip()) for num in slide_numbers.split(",")]
        logger.info(f"Analyzing slides: {slide_nums}")

        # Get elements from specified slides
        result = positioner.get_elements_from_specific_slides(
            presentation_id, slide_nums
        )

        if result.get("success"):
            logger.info(
                f"✅ Successfully analyzed {len(result['slides_analyzed'])} slides"
            )

            # Log detailed information about elements found
            for slide_data in result["slides_analyzed"]:
                slide_num = slide_data["slide_number"]
                elements_count = slide_data["elements_found"]
                logger.info(f"📄 Slide {slide_num}: Found {elements_count} elements")

                # Log element details in human-readable format with content
                for element_id, element_info in slide_data["elements"].items():
                    # Get content preview
                    content_preview = ""
                    if element_info.get("content"):
                        content = str(element_info["content"])
                        if element_info["content_type"] == "text":
                            # Show first 50 characters of text
                            content_preview = f" - Text: '{content[:50]}{'...' if len(content) > 50 else ''}'"
                        elif element_info["content_type"] == "image":
                            content_preview = f" - Image URL: {content[:50]}{'...' if len(content) > 50 else ''}"
                        elif element_info["content_type"] == "table":
                            rows = len(content) if isinstance(content, list) else 0
                            content_preview = f" - Table: {rows} rows"

                    # Check for placeholder information
                    placeholder_info = ""
                    if "placeholder" in element_info.get("metadata", {}):
                        placeholder = element_info["metadata"]["placeholder"]
                        placeholder_info = (
                            f" [Placeholder: {placeholder.get('type', 'UNKNOWN')}]"
                        )

                    # Show both raw and actual visual positions if they differ
                    raw_pos = f"({element_info['x_inches']:.2f}\", {element_info['y_inches']:.2f}\")"
                    raw_size = f"{element_info['width_inches']:.2f}\" × {element_info['height_inches']:.2f}\""

                    if (
                        element_info.get("scaleX", 1) != 1
                        or element_info.get("scaleY", 1) != 1
                    ):
                        # Show actual visual dimensions when scaled
                        actual_size = f"{element_info.get('actual_width_inches', 0):.2f}\" × {element_info.get('actual_height_inches', 0):.2f}\""
                        scale_info = f" [Scaled: {element_info.get('scaleX', 1):.2f}x, {element_info.get('scaleY', 1):.2f}x → {actual_size}]"
                    else:
                        scale_info = ""

                    logger.info(
                        f"  🔲 {element_id} ({element_info['element_type']}): "
                        f"{raw_size} at {raw_pos}{scale_info}"
                        f"{content_preview}{placeholder_info}"
                    )

                    # Log shape type for shapes
                    if element_info[
                        "element_type"
                    ] == "shape" and "shape_type" in element_info.get("metadata", {}):
                        shape_type = element_info["metadata"]["shape_type"]
                        logger.info(f"    └─ Shape type: {shape_type}")

                    # Log debug info about element structure
                    if element_info.get("raw_element_keys"):
                        logger.info(
                            f"    └─ Raw element keys: {element_info['raw_element_keys']}"
                        )

            return result
        else:
            logger.error(f"❌ Failed to analyze slides: {result}")
            raise ValueError(f"Failed to analyze slides: {result}")

    except Exception as error:
        logger.error(f"Error in get_template_elements_from_slides: {error}")
        raise ValueError(f"Error analyzing template slides: {error}")


# @mcp.tool(
#     name="create_presentation_with_positioned_images",
# )
async def create_presentation_with_positioned_images(
    title: str = "Press Recap - Paris x Motorola",
    background_url: str = "https://i.ibb.co/4RXQbYGB/IMG-7774.jpg",
    portrait_url: str = "https://i.ibb.co/HLWpZmPS/20250122-KEVI4992-kevinostaj.jpg",
) -> Dict[str, Any]:
    """
    Creates a Google Slides presentation with precisely positioned background and portrait images.

    Args:
        title: Title for the new presentation
        background_url: URL for the background image (full slide)
        portrait_url: URL for the portrait image (right block)

    Returns:
        Dictionary with presentation details and operation results
    """
    try:
        # Initialize the service
        positioner = PreciseSlidesPositioning()

        logger.info("Creating complete presentation workflow...")
        result = positioner.create_complete_presentation_workflow(
            title=title,
            background_url=background_url,
            portrait_url=portrait_url,
        )

        if result.get("success"):
            logger.info(f"✅ Presentation created successfully!")
            logger.info(f"📝 Presentation URL: {result['url']}")
            logger.info(
                f"📄 Slide 1 (Background): {result['slides']['slide_1']['url']}"
            )
            logger.info(f"📄 Slide 2 (Portrait): {result['slides']['slide_2']['url']}")
            return result
        else:
            logger.error(f"❌ Workflow failed: {result}")
            raise ValueError(f"Workflow failed: {result}")

    except Exception as error:
        logger.error(f"Error in create_presentation_with_positioned_images: {error}")
        raise ValueError(f"Error creating presentation: {error}")


# @mcp.tool(
#     name="create_slide_from_template_zones",
# )
async def create_slide_from_template_zones(
    template_presentation_url: str = "https://docs.google.com/presentation/d/1tdBZ0MH-CGiV2VmEptS7h0PfIyXOp3_yXN_AkNzgpTc/edit?slide=id.g360952048d5_0_86#slide=id.g360952048d5_0_86",
    template_slide_number: int = 5,
    new_presentation_title: str = "Template-Based Slides",
    image_block_url: str = "https://i.ibb.co/HLWpZmPS/20250122-KEVI4992-kevinostaj.jpg",
    background_image_url: str = "https://i.ibb.co/4RXQbYGB/IMG-7774.jpg",
) -> Dict[str, Any]:
    """
    Extract template zones from a template slide and create a new slide with images placed exactly where the placeholder text indicates.

    Args:
        template_presentation_url: URL of the template presentation
        template_slide_number: Slide number to extract template zones from (e.g., 5 for "Image Block")
        new_presentation_title: Title for the new presentation
        image_block_url: URL for image to place in "Image Block" zone
        background_image_url: URL for background image (if template has background zone)

    Returns:
        Dictionary with template extraction results and new slide creation details
    """
    try:
        # Initialize the service
        positioner = PreciseSlidesPositioning()

        # Extract template presentation ID
        template_presentation_id = positioner.extract_presentation_id_from_url(
            template_presentation_url
        )
        logger.info(f"🔍 Analyzing template presentation: {template_presentation_id}")

        # Get template slide ID
        slides_result = positioner.get_presentation_slides(template_presentation_id)
        if not slides_result.get("success") or template_slide_number > len(
            slides_result["slides"]
        ):
            raise ValueError(f"Template slide {template_slide_number} not found")

        template_slide_id = slides_result["slides"][template_slide_number - 1][
            "slide_id"
        ]
        logger.info(
            f"📄 Using template slide {template_slide_number} (ID: {template_slide_id})"
        )

        # Extract template zones from the template slide
        template_zones = positioner.extract_template_zones_by_text(
            template_presentation_id, template_slide_id
        )
        if not template_zones.get("success"):
            raise ValueError(f"Failed to extract template zones: {template_zones}")

        zones = template_zones["zones"]
        logger.info(f"🎯 Found {len(zones)} template zones: {list(zones.keys())}")

        # Create new presentation with one slide
        new_pres_result = positioner.create_presentation_with_slides(
            new_presentation_title, slide_count=1
        )
        if not new_pres_result.get("success"):
            raise ValueError(f"Failed to create new presentation: {new_pres_result}")

        new_presentation_id = new_pres_result["presentation_id"]
        new_slide_id = new_pres_result["slide_ids"][0]

        logger.info(f"✅ Created new presentation: {new_presentation_id}")

        # Place images in template zones
        placement_results = []

        # Place background image if background zone exists
        if "background_image" in zones and background_image_url:
            bg_result = positioner.place_image_in_template_zone(
                new_presentation_id,
                new_slide_id,
                "background_image",
                background_image_url,
                template_zones,
            )
            placement_results.append({"zone": "background_image", "result": bg_result})

        # Place image in image block zone
        if "image_block" in zones and image_block_url:
            img_result = positioner.place_image_in_template_zone(
                new_presentation_id,
                new_slide_id,
                "image_block",
                image_block_url,
                template_zones,
            )
            placement_results.append({"zone": "image_block", "result": img_result})

        # Summary
        successful_placements = [
            p for p in placement_results if p["result"].get("success")
        ]
        failed_placements = [
            p for p in placement_results if not p["result"].get("success")
        ]

        final_result = {
            "success": len(failed_placements) == 0,
            "template_analysis": {
                "template_presentation_id": template_presentation_id,
                "template_slide_number": template_slide_number,
                "template_slide_id": template_slide_id,
                "zones_found": list(zones.keys()),
                "zones_details": zones,
            },
            "new_presentation": {
                "presentation_id": new_presentation_id,
                "presentation_url": new_pres_result["url"],
                "slide_id": new_slide_id,
                "title": new_presentation_title,
            },
            "image_placements": {
                "successful": len(successful_placements),
                "failed": len(failed_placements),
                "details": placement_results,
            },
        }

        logger.info(f"🎉 Template-based slide creation completed!")
        logger.info(f"📝 New presentation URL: {new_pres_result['url']}")
        logger.info(f"🖼️  Successfully placed {len(successful_placements)} images")

        if failed_placements:
            logger.warning(f"⚠️  {len(failed_placements)} image placements failed")

        return final_result

    except Exception as error:
        logger.error(f"Error in create_slide_from_template_zones: {error}")
        raise ValueError(f"Error creating slide from template: {error}")


@mcp.tool(
    name="extract_template_zones_only",
)
async def extract_template_zones_only(
    template_presentation_url: str = "https://docs.google.com/presentation/d/1tdBZ0MH-CGiV2VmEptS7h0PfIyXOp3_yXN_AkNzgpTc/edit?slide=id.g360952048d5_0_86#slide=id.g360952048d5_0_86",
    slide_numbers: str = "4,5",
    unit: str = "PT",
) -> Dict[str, Any]:
    """
    Extract positioning zones and coordinates from specific slides by finding and analyzing placeholder text elements.
    Returns precise coordinates and dimensions for LLM prompting with configurable units.

    Args:
        template_presentation_url: URL of the template presentation
        slide_numbers: Comma-separated slide numbers to analyze (e.g., "4,5")
        unit: Target unit for coordinates ("EMU", "PT", or "INCHES"). Default is "PT".

    Returns:
        Dictionary with extracted template zones, coordinates, and dimensions for each slide
    """
    try:
        # Initialize the service
        positioner = PreciseSlidesPositioning()

        # Extract presentation ID from URL
        presentation_id = positioner.extract_presentation_id_from_url(
            template_presentation_url
        )
        logger.info(
            f"🔍 Extracting template zones from presentation: {presentation_id}"
        )

        # Parse slide numbers
        slide_nums = [int(num.strip()) for num in slide_numbers.split(",")]
        logger.info(f"📄 Analyzing slides: {slide_nums}")

        # Get all slides info
        slides_result = positioner.get_presentation_slides(presentation_id)
        if not slides_result.get("success"):
            raise ValueError(f"Failed to get presentation slides: {slides_result}")

        slides_info = slides_result["slides"]
        results = {
            "success": True,
            "presentation_id": presentation_id,
            "presentation_title": slides_result.get("presentation_title", "Unknown"),
            "slides_analyzed": [],
        }

        # Extract template zones from each requested slide
        for slide_num in slide_nums:
            if slide_num < 1 or slide_num > len(slides_info):
                logger.warning(
                    f"Slide number {slide_num} is out of range (1-{len(slides_info)})"
                )
                continue

            slide_info = slides_info[slide_num - 1]  # Convert to 0-indexed
            slide_id = slide_info["slide_id"]

            logger.info(f"🎯 Extracting template zones from slide {slide_num}")

            # Extract template zones from this slide
            template_zones = positioner.extract_template_zones_by_text(
                presentation_id, slide_id, unit
            )

            slide_data = {
                "slide_number": slide_num,
                "slide_id": slide_id,
                "zones_found": len(template_zones.get("zones", {})),
                "template_zones": template_zones.get("zones", {}),
                "extraction_success": template_zones.get("success", False),
            }

            if template_zones.get("success"):
                zones = template_zones["zones"]
                logger.info(f"✅ Slide {slide_num}: Found {len(zones)} template zones")

                # Log each zone for easy reference
                for zone_name, zone_info in zones.items():
                    logger.info(
                        f"  🎯 {zone_name}: {zone_info['width_inches']:.2f}\"×{zone_info['height_inches']:.2f}\" at ({zone_info['x_inches']:.2f}\", {zone_info['y_inches']:.2f}\")"
                    )
                    logger.info(
                        f"      📝 Original text: '{zone_info['original_text']}'"
                    )
                    logger.info(
                        f"      📐 EMU coordinates: x={zone_info['x_emu']}, y={zone_info['y_emu']}, w={zone_info['width_emu']}, h={zone_info['height_emu']}"
                    )
            else:
                logger.warning(f"❌ Failed to extract zones from slide {slide_num}")

            results["slides_analyzed"].append(slide_data)

        # Summary logging
        total_zones = sum(slide["zones_found"] for slide in results["slides_analyzed"])
        logger.info(f"🎉 Template zone extraction completed!")
        logger.info(f"📊 Total zones found across all slides: {total_zones}")

        return results

    except Exception as error:
        logger.error(f"Error in extract_template_zones_only: {error}")
        raise ValueError(f"Error extracting template zones: {error}")


def main_with_creation():
    """Standalone main function for testing without MCP."""
    import asyncio

    async def test_both_tools():
        # Test template analysis
        print("=== Testing Template Analysis ===")
        template_result = await get_template_elements_from_slides()
        print("Template analysis result:", template_result)

        print("\n=== Testing Presentation Creation ===")
        # Test presentation creation
        creation_result = await create_presentation_with_positioned_images()
        print("Creation result:", creation_result)

        return template_result, creation_result

    results = asyncio.run(test_both_tools())
    print("All results:", results)


if __name__ == "__main__":
    main_with_creation()


# # Usage example function
# def main():
#     """Example usage of the PreciseSlidesPositioning class."""

#     # Initialize the service (uses your existing auth setup)
#     positioner = PreciseSlidesPositioning()

#     # Your slide details
#     presentation_id = "your-presentation-id-here"
#     slide_id = "your-slide-id-here"

#     # Your image URLs
#     background_url = "https://i.ibb.co/4RXQbYGB/IMG-7774.jpg"
#     portrait_url = "https://i.ibb.co/HLWpZmPS/20250122-KEVI4992-kevinostaj.jpg"

#     # Method 1: Complete template implementation
#     print("Implementing complete template...")
#     result = positioner.implement_complete_template(
#         presentation_id, slide_id, background_url, portrait_url
#     )
#     print("Result:", result)

#     # Method 2: Individual operations
#     print("\nAlternative: Adding images individually...")

#     # Add background
#     bg_result = positioner.add_background_image(
#         presentation_id, slide_id, background_url
#     )
#     print("Background result:", bg_result)

#     # Add portrait to right side
#     portrait_result = positioner.add_right_side_image(
#         presentation_id, slide_id, portrait_url
#     )
#     print("Portrait result:", portrait_result)

#     # Method 3: Analyze existing template (helpful for fine-tuning)
#     print("\nAnalyzing existing template elements...")
#     positions = positioner.get_existing_element_positions(presentation_id, slide_id)
#     if positions.get("success"):
#         for element_id, pos in positions["elements"].items():
#             print(
#                 f"{element_id}: {pos['width_inches']:.2f}\" x {pos['height_inches']:.2f}\" at ({pos['x_inches']:.2f}\", {pos['y_inches']:.2f}\")"
#             )


# if __name__ == "__main__":
#     main()
