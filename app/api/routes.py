from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.services.transcript_service import get_transcript_from_url
from app.services.formatter_service import TranscriptFormatter
from app.services.file_service import FileGenerator
from app.utils.validators import validate_youtube_url

router = APIRouter()

class TranscriptRequest(BaseModel):
    url: str
    format_type: str = 'clean' # clean, timestamp, paragraph

class FileGenerationRequest(BaseModel):
    content: str
    file_format: str # txt, docx, pdf
    filename: Optional[str] = "transcript"

class UnifiedTranscriptRequest(BaseModel):
    url: str
    format_type: str = 'clean' # clean, timestamp, paragraph
    file_format: str = 'txt' # txt, docx, pdf

@router.post("/transcript")
async def generate_transcript(request: TranscriptRequest):
    try:
        video_id = validate_youtube_url(request.url)
        raw_transcript = get_transcript(video_id)
        formatted_text = TranscriptFormatter.format(raw_transcript, format_type=request.format_type)
        return {
            "video_id": video_id, 
            "formatted_text": formatted_text,
            "raw_transcript": raw_transcript # Return raw too in case client wants to reformat? Maybe overly verbose.
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/transcript/generate")
async def generate_transcript_file(request: UnifiedTranscriptRequest):
    """Unified endpoint for web frontend - generates transcript and returns file"""
    try:
        # Get transcript from URL (supports both YouTube and Vimeo)
        raw_transcript = get_transcript_from_url(request.url)
        
        # Format transcript
        formatted_text = TranscriptFormatter.format(raw_transcript, format_type=request.format_type)
        
        # Generate file
        file_stream = FileGenerator.generate_file(formatted_text, request.file_format)
        
        # Determine media type
        media_type = "text/plain"
        if request.file_format == 'pdf':
            media_type = "application/pdf"
        elif request.file_format == 'docx':
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
        filename = f"transcript.{request.file_format}"
        
        return Response(
            content=file_stream.getvalue(),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download")
async def download_file(request: FileGenerationRequest):
    try:
        file_stream = FileGenerator.generate_file(request.content, request.file_format)
        
        media_type = "text/plain"
        if request.file_format == 'pdf':
            media_type = "application/pdf"
        elif request.file_format == 'docx':
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
        filename = f"{request.filename}.{request.file_format}"
        
        return Response(
            content=file_stream.getvalue(),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
