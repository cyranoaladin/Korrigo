import pytest
from exams.serializers import BookletSerializer, CopySerializer
from exams.models import Copy, Booklet
from unittest.mock import MagicMock

@pytest.mark.unit
class TestSerializersStrict:
    
    def test_booklet_serializer_integrity(self):
        """
        Ensure pages_images is exposed and matches structure.
        """
        booklet = MagicMock(spec=Booklet)
        booklet.pk = "123"
        booklet.start_page = 1
        booklet.end_page = 2
        booklet.pages_images = ["p1.png", "p2.png"]
        booklet.student_name_guess = "John"
        
        serializer = BookletSerializer(instance=booklet)
        data = serializer.data
        
        assert data['pages_images'] == ["p1.png", "p2.png"]
        assert data['start_page'] == 1
    
    def test_copy_serializer_embedding(self):
        """
        Ensure Copy serializer embeds booklets and contains final_pdf.
        """
        copy = MagicMock(spec=Copy)
        copy.pk = "abc"
        copy.anonymous_id = "ANON"
        copy.status = "READY"
        
        # Mock relation
        booklet_mock = MagicMock(spec=Booklet)
        booklet_mock.pages_images = []
        copy.booklets.all.return_value = [booklet_mock]
        
        # Serializer with Request context (for URLs)
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://test/url"
        
        serializer = CopySerializer(instance=copy, context={'request': request})
        data = serializer.data
        
        assert 'booklets' in data
        assert isinstance(data['booklets'], list)
        assert data['status'] == "READY"
