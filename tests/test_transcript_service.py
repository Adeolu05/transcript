import unittest
from unittest.mock import patch, MagicMock
from app.services.transcript_service import get_transcript
from youtube_transcript_api import TranscriptsDisabled, VideoUnavailable

class TestTranscriptService(unittest.TestCase):

    @patch('app.services.transcript_service.YouTubeTranscriptApi')
    def test_get_transcript_success(self, MockApiClass):
        # Setup mock - return dicts to match what the api actually returns
        mock_instance = MockApiClass.return_value
        
        mock_snippet = {
            'text': 'Hello',
            'start': 0.0,
            'duration': 1.0
        }
        
        mock_instance.fetch.return_value = [mock_snippet]

        # Execute
        with patch('app.services.transcript_service._get_youtube_metadata') as mock_meta:
            mock_meta.return_value = {"title": "Test Title", "duration": 100}
            result = get_transcript('test_video_id')

        # Verify
        MockApiClass.assert_called_once()
        mock_instance.fetch.assert_called_once_with('test_video_id', languages=['en'])
        
        self.assertEqual(result['video_id'], 'test_video_id')
        self.assertEqual(result['title'], 'Test Title')
        self.assertEqual(result['duration_seconds'], 100)
        self.assertEqual(result['language'], 'en')
        self.assertEqual(len(result['segments']), 1)
        self.assertEqual(result['segments'][0]['text'], 'Hello')
        self.assertEqual(result['segments'][0]['start'], 0.0)
        self.assertEqual(result['segments'][0]['duration'], 1.0)

    @patch('app.services.transcript_service._get_youtube_metadata')
    @patch('app.services.transcript_service.YouTubeTranscriptApi')
    def test_transcripts_disabled(self, MockApiClass, mock_meta):
        mock_meta.return_value = {"title": "Test", "duration": 0}
        mock_instance = MockApiClass.return_value
        mock_instance.fetch.side_effect = TranscriptsDisabled('test_video_id')
        
        with self.assertRaises(Exception) as context:
            get_transcript('test_video_id')
        
        self.assertIn("Transcripts are disabled", str(context.exception))

    @patch('app.services.transcript_service._get_youtube_metadata')
    @patch('app.services.transcript_service.YouTubeTranscriptApi')
    def test_video_unavailable(self, MockApiClass, mock_meta):
        mock_meta.return_value = {"title": "Test", "duration": 0}
        mock_instance = MockApiClass.return_value
        mock_instance.fetch.side_effect = VideoUnavailable('test_video_id')
        
        with self.assertRaises(Exception) as context:
            get_transcript('test_video_id')
        
        self.assertIn("Video is unavailable", str(context.exception))

if __name__ == '__main__':
    unittest.main()
