import pytest
from markdowndeck.models import ElementType
from markdowndeck.models.elements.media import ImageElement


class TestImageElement:
    def test_data_c_03_split_raises_not_implemented_error(self):
        """
        Test Case: DATA-C-03
        Validates that ImageElement.split() raises NotImplementedError.
        Spec: DATA_MODELS.md, Section 3.4
        """
        image_element = ImageElement(element_type=ElementType.IMAGE, url="test.png")
        with pytest.raises(NotImplementedError) as excinfo:
            image_element.split(available_height=100.0)
        assert "ImageElement.split should never be called" in str(excinfo.value)
