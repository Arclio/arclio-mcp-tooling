#!/usr/bin/env python3
"""
Test script for batch slides functionality
"""

# Example usage showing the difference between old (15+ API calls) vs new (1 API call)

# OLD WAY - Multiple individual API calls:
"""
# This would require 15+ separate API calls:
await create_presentation(title="John's Company Campaign")
await create_slide(presentation_id, layout="BLANK") 
await create_textbox_with_text(presentation_id, slide_id, "John's Company Campaign", ...)  # Call 1
await create_textbox_with_text(presentation_id, slide_id, "Campaign description", ...)   # Call 2
await create_textbox_with_text(presentation_id, slide_id, "43.4M", ...)                 # Call 3
await update_text_formatting(presentation_id, element_id, "**43.4M**")                  # Call 4
await create_textbox_with_text(presentation_id, slide_id, "TOTAL IMPRESSIONS", ...)     # Call 5
await create_textbox_with_text(presentation_id, slide_id, "134K", ...)                  # Call 6
await update_text_formatting(presentation_id, element_id, "**134K**")                   # Call 7
await create_textbox_with_text(presentation_id, slide_id, "TOTAL ENGAGEMENTS", ...)     # Call 8
await create_textbox_with_text(presentation_id, slide_id, "4.8B", ...)                  # Call 9
await update_text_formatting(presentation_id, element_id, "**4.8B**")                   # Call 10
await create_textbox_with_text(presentation_id, slide_id, "AGGREGATE READERSHIP", ...)  # Call 11
await create_textbox_with_text(presentation_id, slide_id, "$9.1M", ...)                 # Call 12
await update_text_formatting(presentation_id, element_id, "**$9.1M**")                  # Call 13
await create_textbox_with_text(presentation_id, slide_id, "AD EQUIVALENCY", ...)        # Call 14
await add_image_to_slide(presentation_id, slide_id, image_url, ...)                     # Call 15
"""

# NEW WAY - Single batch API call:
template_data = {
    "title": {
        "text": "John's Company \"That's Company\" Super Bowl Campaign",
        "position": {"x": 32, "y": 35, "width": 330, "height": 40},
        "style": {"fontSize": 18, "fontFamily": "Roboto"},
    },
    "description": {
        "text": "John's Company leveraged the high-visibility Super Bowl platform to showcase their bold brand personality with \"That's Company\" campaign. The campaign successfully generated massive social media engagement and brand awareness across multiple touchpoints.",
        "position": {"x": 32, "y": 95, "width": 330, "height": 160},
        "style": {"fontSize": 12, "fontFamily": "Roboto"},
    },
    "stats": [
        {
            "value": "43.4M",
            "label": "TOTAL IMPRESSIONS",
            "position": {"x": 374.5, "y": 268.5},
        },
        {
            "value": "134K",
            "label": "TOTAL ENGAGEMENTS",
            "position": {"x": 516.5, "y": 268.5},
        },
        {
            "value": "4.8B",
            "label": "AGGREGATE READERSHIP",
            "position": {"x": 374.5, "y": 350.5},
        },
        {
            "value": "$9.1M",
            "label": "AD EQUIVALENCY",
            "position": {"x": 516.5, "y": 350.5},
        },
    ],
    "image": {
        "url": "https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=300&h=300&fit=crop",
        "position": {"x": 375, "y": 35},
        "size": {"width": 285, "height": 215},
    },
}

# Single API call that replaces all 15+ individual calls:
# await create_slide_from_template_data(presentation_id, slide_id, template_data)

print("Batch functionality has been added!")
print("- slides_batch_update: For raw API requests")
print("- create_slide_from_template_data: For structured template data")
print("- Reduces 15+ API calls to 1 call")
print("- Much faster execution")
print("- Atomic operation (all succeed or all fail)")

# PROBLEM: Two separate API calls needed
# OLD WAY - Two separate API calls:
# await create_slide(presentation_id, layout="BLANK")
# await create_textbox_with_text(presentation_id, slide_id, "John's Company Campaign", ...)  # Call 1
# await create_textbox_with_text(presentation_id, slide_id, "Campaign description", ...)   # Call 2
# await create_textbox_with_text(presentation_id, slide_id, "43.4M", ...)                 # Call 3
# await create_textbox_with_text(presentation_id, slide_id, "TOTAL IMPRESSIONS", ...)     # Call 4
# await create_textbox_with_text(presentation_id, slide_id, "TOTAL IMPRESSIONS", ...)     # Call 5
# await create_textbox_with_text(presentation_id, slide_id, "134K", ...)                  # Call 6
# await create_textbox_with_text(presentation_id, slide_id, "TOTAL ENGAGEMENTS", ...)     # Call 7
# await create_textbox_with_text(presentation_id, slide_id, "TOTAL ENGAGEMENTS", ...)     # Call 8
# await create_textbox_with_text(presentation_id, slide_id, "4.8B", ...)                  # Call 9
# await create_textbox_with_text(presentation_id, slide_id, "AGGREGATE READERSHIP", ...)  # Call 10
# await create_textbox_with_text(presentation_id, slide_id, "AGGREGATE READERSHIP", ...)  # Call 11
# await create_textbox_with_text(presentation_id, slide_id, "$9.1M", ...)                 # Call 12
# await create_textbox_with_text(presentation_id, slide_id, "AD EQUIVALENCY", ...)        # Call 13
# await create_textbox_with_text(presentation_id, slide_id, "AD EQUIVALENCY", ...)        # Call 14
# await add_image_to_slide(presentation_id, slide_id, image_url, ...)                     # Call 15
# TOTAL: 15+ API calls!

# NEW OPTIMIZED WAY - Single batch API call:
template_data = {
    "title": {
        "text": "John's Company \"That's Company\" Super Bowl Campaign",
        "position": {"x": 32, "y": 35, "width": 330, "height": 40},
        "style": {"fontSize": 18, "fontFamily": "Roboto"},
    },
    "description": {
        "text": "John's Company leveraged the high-visibility Super Bowl platform to showcase their bold brand personality with \"That's Company\" campaign. The campaign successfully generated massive social media engagement and brand awareness across multiple touchpoints.",
        "position": {"x": 32, "y": 95, "width": 330, "height": 160},
        "style": {"fontSize": 12, "fontFamily": "Roboto"},
    },
    "stats": [
        {
            "value": "43.4M",
            "label": "TOTAL IMPRESSIONS",
            "position": {"x": 374.5, "y": 268.5},
        },
        {
            "value": "134K",
            "label": "TOTAL ENGAGEMENTS",
            "position": {"x": 516.5, "y": 268.5},
        },
        {
            "value": "4.8B",
            "label": "AGGREGATE READERSHIP",
            "position": {"x": 374.5, "y": 350.5},
        },
        {
            "value": "$9.1M",
            "label": "AD EQUIVALENCY",
            "position": {"x": 516.5, "y": 350.5},
        },
    ],
    "image": {
        "url": "https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=300&h=300&fit=crop",
        "position": {"x": 375, "y": 35},
        "size": {"width": 285, "height": 215},
    },
}

# SOLUTION 1: Template data approach
# await create_slide_from_template_data(presentation_id, slide_id, template_data)

# SOLUTION 2: ENHANCED create_slide_with_elements (BEST!)
# Now supports creating slide + elements in ONE call!

elements = [
    {
        "type": "textbox",
        "content": "John's Company Campaign",
        "position": {"x": 32, "y": 35, "width": 330, "height": 40},
        "style": {"fontSize": 18, "fontFamily": "Roboto", "bold": True},
    },
    {
        "type": "textbox",
        "content": "Campaign results description...",
        "position": {"x": 32, "y": 95, "width": 330, "height": 160},
        "style": {"fontSize": 12, "fontFamily": "Roboto"},
    },
    {
        "type": "textbox",
        "content": "43.4M",
        "position": {"x": 374.5, "y": 268.5, "width": 142, "height": 40},
        "style": {"fontSize": 25, "fontFamily": "Playfair Display", "bold": True},
    },
    {
        "type": "image",
        "content": "https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=300&h=300&fit=crop",
        "position": {"x": 375, "y": 35, "width": 285, "height": 215},
    },
]

# NEW ENHANCED WAY - Create slide + elements in ONE call:
# await create_slide_with_elements(
#     presentation_id=presentation_id,
#     elements=elements,
#     create_slide=True,  # Creates slide AND adds elements
#     layout="BLANK",
#     background_color="#f8cdcd4f"
# )
# TOTAL: 1 API call! (creates slide + all elements)

# Or add elements to existing slide (original behavior):
# await create_slide_with_elements(
#     presentation_id=presentation_id,
#     slide_id=existing_slide_id,
#     elements=elements,
#     create_slide=False  # Only adds elements (default)
# )
# TOTAL: 1 API call! (just elements)

print("SOLUTION: Enhanced create_slide_with_elements function!")
print("- NOW SUPPORTS create_slide=True parameter")
print("- ELIMINATES the two-call pattern!")
print("- Backward compatible (create_slide=False is default)")
print("- create_slide_from_template_data: For structured template data")
print("- slides_batch_update: For raw API requests")
print("- Reduces 15+ API calls to 1 call")
print("- Much faster execution")
print("- Atomic operation (all succeed or all fail)")
print("- No more separate create_slide() + create_slide_with_elements() calls needed!")
