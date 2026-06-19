"""
Unit tests for SlidesService.add_image.

The service method existed but was never exposed as a tool (agents couldn't
insert images). These verify the createImage batchUpdate request is built
correctly, including the optional size.
"""


def _batch_body(mock_slides_service):
    _, kwargs = mock_slides_service.service.presentations.return_value.batchUpdate.call_args
    return kwargs["body"]["requests"]


class TestAddImage:
    def test_creates_image_request(self, mock_slides_service):
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createImage": {"objectId": "img1"}}]
        }

        result = mock_slides_service.add_image(
            presentation_id="p1",
            slide_id="s1",
            image_url="https://example.com/a.png",
            position=(120, 140),
        )

        assert result["imageId"] == "img1"
        assert result["result"] == "success"
        req = _batch_body(mock_slides_service)[0]["createImage"]
        assert req["url"] == "https://example.com/a.png"
        assert req["elementProperties"]["pageObjectId"] == "s1"
        transform = req["elementProperties"]["transform"]
        assert transform["translateX"] == 120
        assert transform["translateY"] == 140
        # No size requested -> no size key.
        assert "size" not in req["elementProperties"]

    def test_includes_size_when_given(self, mock_slides_service):
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createImage": {"objectId": "img2"}}]
        }

        mock_slides_service.add_image(
            presentation_id="p1",
            slide_id="s1",
            image_url="https://example.com/b.png",
            size=(300, 200),
        )

        req = _batch_body(mock_slides_service)[0]["createImage"]
        size = req["elementProperties"]["size"]
        assert size["width"]["magnitude"] == 300
        assert size["height"]["magnitude"] == 200
