import os
import uuid
import time
import html
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

# Create a standard temp directory for the project
TEMP_DIR = Path(os.getenv("TEMP", "/tmp")) / "transcript_flow"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

class FileGenerator:
    @staticmethod
    def _get_temp_filepath(extension: str) -> Path:
        """Generates a unique temporary file path."""
        filename = f"{uuid.uuid4().hex}.{extension}"
        return TEMP_DIR / filename

    @staticmethod
    def generate_txt(content: str) -> str:
        filepath = FileGenerator._get_temp_filepath("txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return str(filepath)

    @staticmethod
    def generate_docx(content: str) -> str:
        filepath = FileGenerator._get_temp_filepath("docx")
        doc = Document()
        
        # Split content by newlines to avoid one giant paragraph
        for paragraph in content.split('\n\n'):
            doc.add_paragraph(paragraph)
            
        doc.save(str(filepath))
        return str(filepath)

    @staticmethod
    def generate_pdf(content: str) -> str:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        
        filepath = FileGenerator._get_temp_filepath("pdf")
        
        # Use SimpleDocTemplate for proper layout directly to file
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # Container for PDF elements
        story = []
        styles = getSampleStyleSheet()
        style = styles["BodyText"]
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        for para_text in paragraphs:
            if para_text.strip():
                # Replace single newlines with spaces for better flow
                para_text = para_text.replace('\n', ' ')
                # Escape HTML/XML characters to prevent ReportLab injection
                para_text = html.escape(para_text)
                # Create paragraph with proper text wrapping
                para = Paragraph(para_text, style)
                story.append(para)
                story.append(Spacer(1, 0.2 * inch))
        
        # Build PDF
        doc.build(story)
        return str(filepath)

    @staticmethod
    def generate_file(content: str, file_format: str) -> str:
        """Returns the absolute path to the generated file on disk."""
        if file_format == 'docx':
            return FileGenerator.generate_docx(content)
        elif file_format == 'pdf':
            return FileGenerator.generate_pdf(content)
        else:
            return FileGenerator.generate_txt(content)

    @staticmethod
    def cleanup_old_files(max_age_hours: int = 1) -> int:
        """Deletes files in the temp directory older than max_age_hours. Returns count deleted."""
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted = 0
        
        for file_path in TEMP_DIR.glob("*.*"):
            if file_path.is_file():
                try:
                    file_mtime = file_path.stat().st_mtime
                    if now - file_mtime > max_age_seconds:
                        file_path.unlink()
                        deleted += 1
                except Exception as e:
                    print(f"Failed to delete old file {file_path}: {e}")
        
        return deleted
