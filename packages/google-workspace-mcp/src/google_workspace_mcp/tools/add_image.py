"""
Precise Google Slides Image Positioning - Python Implementation
Uses your existing BaseGoogleService infrastructure for authentication.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from google_workspace_mcp.app import mcp  # Import from central app module
from google_workspace_mcp.services.base import BaseGoogleService

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
        Extract exact positions and dimensions of existing elements from a template slide.
        Use this to reverse-engineer your template coordinates.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide

        Returns:
            Dictionary of element positions or error details
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
                if (
                    "objectId" in element
                    and "size" in element
                    and "transform" in element
                ):
                    obj_id = element["objectId"]
                    size = element["size"]
                    transform = element["transform"]

                    positions[obj_id] = {
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
                        "scaleX": transform.get("scaleX", 1),
                        "scaleY": transform.get("scaleY", 1),
                        "element_type": (
                            list(element.keys())[1]
                            if len(element.keys()) > 1
                            else "unknown"
                        ),
                    }

            logger.info(f"Retrieved positions for {len(positions)} elements")
            return {"success": True, "elements": positions, "slide_id": slide_id}

        except Exception as error:
            return self.handle_api_error("get_existing_element_positions", error)

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
                "title": title,
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


@mcp.tool(
    name="create_presentation_with_positioned_images",
    description="Creates a Google Slides presentation with precisely positioned background and portrait images. Complete workflow with hardcoded images for testing.",
)
async def create_presentation_with_positioned_images() -> Dict[str, Any]:
    """Creates a Google Slides presentation with precisely positioned background and portrait images."""

    # Initialize the service
    positioner = PreciseSlidesPositioning()

    # Your image URLs
    background_url = "https://i.ibb.co/4RXQbYGB/IMG-7774.jpg"
    portrait_url = "https://i.ibb.co/HLWpZmPS/20250122-KEVI4992-kevinostaj.jpg"

    # Method 1: Complete workflow (recommended)
    print("Creating complete presentation workflow...")
    result = positioner.create_complete_presentation_workflow(
        title="Press Recap - Paris x Motorola",
        background_url=background_url,
        portrait_url=portrait_url,
    )

    if result.get("success"):
        logger.info(f"✅ Presentation created successfully!")
        logger.info(f"📝 Presentation URL: {result['url']}")
        logger.info(f"📄 Slide 1 (Background): {result['slides']['slide_1']['url']}")
        logger.info(f"📄 Slide 2 (Portrait): {result['slides']['slide_2']['url']}")
        return result
    else:
        logger.error(f"❌ Workflow failed: {result}")
        raise ValueError(f"Workflow failed: {result}")


def main_with_creation():
    """Standalone main function for testing without MCP."""
    import asyncio

    result = asyncio.run(create_presentation_with_positioned_images())
    print("Result:", result)


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
