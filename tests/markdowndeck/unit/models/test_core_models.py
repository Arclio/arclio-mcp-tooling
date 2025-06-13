from markdowndeck.models import (
    ElementType,
    ImageElement,
    Section,
    Slide,
    TextElement,
)


class TestCoreModels:
    def test_data_c_04_slide_is_continuation(self):
        """
        Test Case: DATA-C-01
        Spec: Verify Slide object correctly handles `is_continuation` flag.
        """
        # Arrange
        slide_is_cont = Slide(is_continuation=True)
        slide_is_not_cont = Slide()

        # Assert
        assert slide_is_cont.is_continuation is True
        assert slide_is_not_cont.is_continuation is False

    def test_data_c_05_section_mixed_children(self):
        """
        Test Case: DATA-C-02
        Spec: Verify Section.children can contain mixed Element and Section types.
        """
        # Arrange
        children = [
            TextElement(element_type=ElementType.TEXT),
            Section(),
            ImageElement(element_type=ElementType.IMAGE),
        ]
        section = Section(children=children)

        # Assert
        assert len(section.children) == 3
        assert isinstance(section.children[0], TextElement)
        assert isinstance(section.children[1], Section)
        assert isinstance(section.children[2], ImageElement)
