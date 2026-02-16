import os
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

class FileGenerator:
    @staticmethod
    def generate_txt(content: str) -> BytesIO:
        file_stream = BytesIO()
        file_stream.write(content.encode('utf-8'))
        file_stream.seek(0)
        return file_stream

    @staticmethod
    def generate_docx(content: str) -> BytesIO:
        doc = Document()
        # Split content by newlines to avoid one giant paragraph if relevant
        for paragraph in content.split('\n\n'):
            doc.add_paragraph(paragraph)
        
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream

    @staticmethod
    def generate_pdf(content: str) -> BytesIO:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        
        file_stream = BytesIO()
        
        # Use SimpleDocTemplate for proper layout
        doc = SimpleDocTemplate(
            file_stream,
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
                # Create paragraph with proper text wrapping
                para = Paragraph(para_text, style)
                story.append(para)
                story.append(Spacer(1, 0.2 * inch))
        
        # Build PDF
        doc.build(story)
        file_stream.seek(0)
        return file_stream

    @staticmethod
    def generate_file(content: str, file_format: str) -> BytesIO:
        if file_format == 'docx':
            return FileGenerator.generate_docx(content)
        elif file_format == 'pdf':
            return FileGenerator.generate_pdf(content)
        else:
            return FileGenerator.generate_txt(content)
