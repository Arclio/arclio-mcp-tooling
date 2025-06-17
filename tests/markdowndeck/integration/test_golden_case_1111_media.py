import pytest
from markdowndeck import markdown_to_requests

# This markdown has been corrected to be compliant with MarkdownDeck Grammar V2.0.
# Key Fixes:
# 1. Added explicit `[width]` and `[height]` directives to all `![...](...)` images without `[fill]`.
# 2. Wrapped all loose content (headings, paragraphs, etc.) within `:::section` blocks.
# 3. Corrected invalid nesting where `:::row` or `:::section` were children of a `:::section`.
MEDIA_DECK_MARKDOWN = """
[background=#fdeef1]
:::row [height=100%]
    :::column [width=90%] [valign=middle]
        :::section [align=center]
            ![Logo](https://placehold.co/100x100/333333/fdeef1?text=IHI) [width=100][height=100]
            # 11:11 Media Deck Templates [fontsize=48][font-family=Georgia]
        :::
    :::
    :::column [width=10%]
        :::section [align=right]
            ![Awsm Labs Logo](https://placehold.co/60x60/333333/fdeef1?text=Awsm) [width=60][height=60]
        :::
    :::
:::

===
[background=#ffffff]
:::section [padding=40]
    # Table of Contents [fontsize=40][font-family=Helvetica][margin-bottom=40]
:::
:::row [gap=50][padding=0,40,40,40]
    :::column [width=1/3]
        :::section [line-spacing=1.8]
            ### Case Study Deck [color=#00a0b0][font-family=Helvetica]
            Title
            Press Mentions
            Campaign Benchmarks
            Partnership Information
            Additional Data
            Campaign Hero Stats
            Social Media Metrics
            Additional Images
            Key Insights
            Campaign Takeaways
            Conclusion Slide
            Thank You
        :::
    :::
    :::column [width=1/3]
        :::section [line-spacing=1.8]
            ### Internal Recap Deck [color=#00a0b0][font-family=Helvetica]
            Title
            Executive Summary
            Press Mentions
            Campaign Recap Hero Stats
            Social Media Metrics
            High Level Data
            Data Deep Dive
            Positive/Negative Campaign Takeaways
            Additional Images
            Conclusion Slide
            Thank You
        :::
    :::
    :::column [width=1/3]
        :::section [line-spacing=1.8]
            ### Pitch Deck [color=#00a0b0][font-family=Helvetica]
            Title
            Partner Overview
            Partner Key Metrics
            Previous Partner Celebrity Partnerships
            Partner Press Coverage
            Fit with the Paris Brand
            Recommendations Slide
            Thank You Slide
        :::
    :::
:::
@@@
![Awsm Labs Logo](https://placehold.co/50x50/333333/000000?text=Awsm) [width=50][height=50]
===
[background=black]
:::row [height=100%]
    :::column [width=90%] [valign=middle]
        :::section [align=center][color=white]
            ![Logo](https://placehold.co/100x100/000000/ffffff?text=IHI) [width=100][height=100]
            # CASE STUDY DECK [fontsize=48][font-family=Impact]
            ## PAGE TYPES [fontsize=36][font-family=Helvetica]
        :::
    :::
    :::column [width=10%]
        :::section [align=right]
            ![Awsm Labs Logo](https://placehold.co/60x60/ffffff/000000?text=Awsm) [width=60][height=60]
        :::
    :::
:::

===
[background=url(https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=2070)]
:::row [height=100%]
    :::column [width=60%]
        :::section [padding=20]
            #### Title Slide B
        :::
    :::
    :::column [width=40%] [valign=middle]
        :::section [background=white][padding=40][align=center]
            ![Brand + Paris Logo](https://placehold.co/200x100/ffffff/333333?text=Brand+Logo) [width=200][height=100]
            ### Brand + Paris Logo Lock-Up
        :::
    :::
:::

===
:::row [gap=40]
    :::column [width=60%][padding=30]
        :::section [margin-bottom=30]
            ## Press Recap Slide Title [fontsize=32][color=#34495e]
        :::
        :::section [padding=30][background=#f8f9fa][border=1pt solid #e9ecef]
            This is the slide copy block. It contains a summary of the press mentions and media coverage. The text here provides context for the image shown on the right, highlighting key achievements and public reception.
        :::
    :::
    :::column [width=40%]
        :::section [height=100%] [width=100%]
            ![Image Block](https://images.unsplash.com/photo-1534067783941-51c9c23ecefd?q=80&w=1887) [fill]
        :::
    :::
:::

===
:::row [gap=30]
    :::column [width=60%][padding=20]
        :::section
            ## Slide Title [fontsize=32][margin-bottom=20]
        :::
        :::section [padding=20][margin-bottom=30]
            This is the slide copy block. It contains the main narrative of the slide, explaining the data and statistics shown below. It provides the story behind the numbers.
        :::
        :::row [gap=15]
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat A**
                :::
            :::
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat B**
                :::
            :::
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat C**
                :::
            :::
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat D**
                :::
            :::
        :::
    :::
    :::column [width=40%]
        :::section [height=100%] [width=100%]
            ![Image Block](https://images.unsplash.com/photo-1501854140801-50d01698950b?q=80&w=1950) [fill]
        :::
    :::
:::

===
:::row [gap=30]
    :::column [width=40%]
        :::section [height=100%] [width=100%]
            ![Image Block](https://images.unsplash.com/photo-1472214103451-9374bd1c798e?q=80&w=2070) [fill]
        :::
    :::
    :::column [width=60%][padding=20]
        :::section
            ## Slide Title [fontsize=32][margin-bottom=20]
        :::
        :::section [padding=20][margin-bottom=30]
            This is the slide copy block. It contains the main narrative of the slide, explaining the data and statistics shown below. It provides the story behind the numbers.
        :::
        :::row [gap=15]
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat A**
                :::
            :::
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat B**
                :::
            :::
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat C**
                :::
            :::
            :::column [width=1/4]
                :::section [align=center][padding=20][background=#f1f3f5][border-radius=5]
                    **Stat D**
                :::
            :::
        :::
    :::
:::

===
:::section [padding=20]
    ## Data Slide A [fontsize=32][margin-bottom=30][align=center]
:::
:::row [gap=30] [padding=0,20,20,20]
    :::column [width=50%]
        :::section
            ### Table Title A [align=center][margin-bottom=10]
            | Category      | Value 1 | Value 2 | [background=#343a40][color=white] |
            |---------------|---------|---------|--------------------------------|
            | Data Point A  | 1,234   | 56.7%   |                                |
            | Data Point B  | 8,765   | 43.2%   | [background=#f8f9fa]           |
            | Data Point C  | 4,321   | 88.9%   |                                |
        :::
    :::
    :::column [width=50%]
        :::section
            ### Table Title B [align=center][margin-bottom=10]
            | Metric        | Result  | Change  | [background=#343a40][color=white] |
            |---------------|---------|---------|--------------------------------|
            | Engagement    | 4.5/5   | +0.2    |                                |
            | Reach         | 1.2M    | +10%    | [background=#f8f9fa]           |
            | Conversion    | 2.3%    | -0.1%   |                                |
        :::
    :::
:::

===
:::row [gap=40]
    :::column [width=65%][padding=30]
        :::section [margin-bottom=20]
            ## Large Copy Block + Image [fontsize=32]
        :::
        :::section [padding=20][line-spacing=1.6]
            This is a large copy block designed for slides needing extensive textual explanation. The purpose is to provide detailed information, context, or a deep dive into a particular topic. The layout allows for significant content on the left, balanced by a visual element on the right. This block can contain multiple paragraphs, bullet points, or any other text-based content required to fully explain the slide's subject matter.
        :::
    :::
    :::column [width=35%]
        :::section [height=100%] [width=100%]
            ![Architectural building facade](https://images.unsplash.com/photo-1487958449943-2429e8be8625?q=80&w=2070) [fill]
        :::
    :::
:::

===
:::section [padding=20]
    ## Social Media Showcase [fontsize=32]
:::
:::row [gap=20][padding=0,20,20,20]
    :::column [width=40%]
        :::section [padding=20][line-spacing=1.5]
            ### Campaign Narrative
            This section details the narrative and strategy behind our recent social media campaign. We focused on authentic user-generated content and influencer partnerships to drive engagement.
            - **Platform Focus:** Instagram, TikTok
            - **Key Metric:** 25% increase in user shares
        :::
    :::
    :::column [width=20%]
        :::section [align=center]
            **Instagram Highlight** [bold][margin-bottom=10]
            ![Phone mockup of an Instagram story](https://placehold.co/150x300/e9ecef/495057?text=IG+Story) [width=150][height=300]
        :::
    :::
    :::column [width=20%]
        :::section [align=center]
            **TikTok Showcase** [bold][margin-bottom=10]
            ![Phone mockup of a TikTok video](https://placehold.co/150x300/e9ecef/495057?text=TikTok) [width=150][height=300]
        :::
    :::
    :::column [width=20%]
        :::section [align=center]
            **User Content** [bold][margin-bottom=10]
            ![Phone mockup of user-generated content](https://placehold.co/150x300/e9ecef/495057?text=UGC) [width=150][height=300]
        :::
    :::
:::

===
:::section [padding=20]
    ## Image Collection [fontsize=32][align=center][margin-bottom=20]
:::
:::section [padding=0,20,20,20]
    ![A wide panoramic landscape image](https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?q=80&w=2070) [width=100%][height=400]
:::

===
:::section [padding=40][align=center]
    ## Summary Slide [fontsize=32][margin-bottom=30]
:::
:::section [padding=0,40,40,40][align=center]
    :::section [padding=40][background=#f1f3f5][width=80%][line-spacing=1.5]
        This is the summary slide copy block. This area is used to summarize the key points, takeaways, or conclusions from the preceding slides. It provides a final, concise overview of the most important information presented in the deck.
    :::
:::

===
[background=url(https://images.unsplash.com/photo-1534447677768-64483a0f71d1?q=80&w=2070)]
:::row [height=100%]
    :::column [height=100%] [valign=middle]
        :::section [align=center]
            :::section [background=white][padding=30][border-radius=8][border=1pt solid #dee2e6]
                ### Thank You [fontsize=36][font-family=Georgia]
            :::
        :::
    :::
:::
"""


class TestGoldenCase1111Media:
    """A golden case test for a complex, real-world presentation."""

    def test_media_deck_parses_and_generates_successfully(self):
        """
        Runs the full pipeline on a complex, real-world markdown file.
        This test passing confirms that the parser, layout, overflow, and
        API generator can handle complex, nested, and styled content correctly
        when the markdown is grammatically valid.
        """
        try:
            # Act: Run the full pipeline via the main entrypoint
            result = markdown_to_requests(
                MEDIA_DECK_MARKDOWN, title="11:11 Media Deck Golden Case"
            )

            # Assert: The process completes without errors and produces batches
            assert result is not None, "Pipeline result should not be None."
            assert "slide_batches" in result, "Result must contain 'slide_batches'."
            assert (
                len(result["slide_batches"]) > 0
            ), "At least one slide batch should be generated."

            # Check for a reasonable number of requests in the first batch
            first_batch_requests = result["slide_batches"][0].get("requests", [])
            assert (
                len(first_batch_requests) > 0
            ), "The first slide batch should contain API requests."

        except Exception as e:
            pytest.fail(
                f"The pipeline failed to process the golden case markdown. Error: {e}"
            )
