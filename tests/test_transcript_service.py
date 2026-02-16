import unittest
from unittest.mock import patch, MagicMock
from app.services.transcript_service import get_transcript
from youtube_transcript_api import TranscriptsDisabled, VideoUnavailable

class TestTranscriptService(unittest.TestCase):

    @patch('app.services.transcript_service.YouTubeTranscriptApi')
    def test_get_transcript_success(self, MockApiClass):
        # Setup mock - create objects with attributes, not dicts
        mock_instance = MockApiClass.return_value
        
        # Create mock transcript snippet objects
        from unittest.mock import MagicMock
        mock_snippet = MagicMock()
        mock_snippet.text = 'Hello'
        mock_snippet.start = 0.0
        mock_snippet.duration = 1.0
        
        mock_instance.fetch.return_value = [mock_snippet]

        # Execute
        result = get_transcript('test_video_id')

        # Verify
        MockApiClass.assert_called_once()
        mock_instance.fetch.assert_called_once_with('test_video_id', languages=['en'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'Hello')
        self.assertEqual(result[0]['start'], 0.0)
        self.assertEqual(result[0]['duration'], 1.0)

    @patch('app.services.transcript_service.YouTubeTranscriptApi')
    def test_transcripts_disabled(self, MockApiClass):
        mock_instance = MockApiClass.return_value
        mock_instance.fetch.side_effect = TranscriptsDisabled('test_video_id')
        
        with self.assertRaises(Exception) as context:
            get_transcript('test_video_id')
        
        self.assertIn("Transcripts are disabled", str(context.exception))

    @patch('app.services.transcript_service.YouTubeTranscriptApi')
    def test_video_unavailable(self, MockApiClass):
        mock_instance = MockApiClass.return_value
        mock_instance.fetch.side_effect = VideoUnavailable('test_video_id')
        
        with self.assertRaises(Exception) as context:
            get_transcript('test_video_id')
        
        self.assertIn("Video is unavailable", str(context.exception))

if __name__ == '__main__':
    unittest.main()
