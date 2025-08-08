"""
Certificate Generation Module

This module handles the generation of personalized certificates from CSV data
using a PDF template. It supports custom fonts, dynamic text positioning,
and Google Drive integration for storage.

Key Features:
- CSV data validation and processing
- PDF certificate generation with custom fonts (Unna, Lora, AlexBrush)
- Dynamic text positioning and wrapping
- Google Drive integration for certificate storage
- Comprehensive error handling and logging
- Font fallback system for missing fonts

Required CSV Columns:
- name: Student's full name
- email: Student's email address
- certificate_id: Unique certificate identifier
- course_type: Type of course completed
- completion_date: Date in MM/DD/YYYY format
- college_name: Name of the college/institution
- mentor_name: Name of the mentor/instructor
- mentor_signature: Signature file name or text

Author: Certificate Generation System
Date: 2024
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from io import BytesIO

# ReportLab imports for PDF generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# PyPDF2 for merging PDFs
from pypdf import PdfWriter, PdfReader

# Google Drive imports
# from auth_manager import get_drive_service
# from googleapiclient.http import MediaFileUpload

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('certificate_generator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Custom exception classes
class CertificateGeneratorError(Exception):
    """Base exception for certificate generator errors."""
    pass

class CSVError(CertificateGeneratorError):
    """Raised when there are issues with CSV data."""
    pass

class PDFError(CertificateGeneratorError):
    """Raised when there are issues with PDF generation."""
    pass

class FontError(CertificateGeneratorError):
    """Raised when there are issues with font loading."""
    pass

class ConfigurationError(CertificateGeneratorError):
    """Raised when there are configuration issues."""
    pass

class CertificateGenerator:
    """
    Main class for certificate generation functionality.
    
    This class handles the entire certificate generation process including:
    - CSV data reading and validation
    - PDF template processing with custom fonts
    - Dynamic text positioning and wrapping
    - Certificate generation with proper formatting
    - Google Drive integration for storage
    - Comprehensive error handling and reporting
    - Font fallback system for missing fonts
    
    The class uses ReportLab for PDF generation and supports custom fonts
    (Unna, Lora, AlexBrush) with automatic fallback to system fonts
    if the custom fonts are not available.
    
    Attributes:
        config (dict): Configuration dictionary for customization
        required_columns (list): List of required CSV column names
        fonts_loaded (bool): Whether custom fonts have been loaded
        font_fallbacks (dict): Mapping of missing fonts to fallback fonts
        generation_summary (dict): Summary of certificate generation process
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the certificate generator.
        
        Args:
            config (dict, optional): Configuration dictionary for customization.
                Can include font paths, template settings, and other options.
        
        Note:
            During initialization, the system will attempt to load custom fonts
            from the assets/fonts directory. If fonts are missing, a fallback
            system will be used with user prompting for approval.
        """
        self.config = config or {}
        self.required_columns = [
            'name', 'email', 'certificate_id', 'course_type', 
            'completion_date', 'college_name', 'mentor_name', 'mentor_signature', 'event_type'
        ]
        self.fonts_loaded = False
        self.font_fallbacks = {}  # Store font fallback mappings
        self.generation_summary = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'file_locations': [],
            'font_usage': {
                'custom_fonts_loaded': [],
                'fallback_fonts_used': [],
                'missing_fonts': []
            },
            'output_directory': '',
            'csv_source': ''
        }
        
        # Initialize fonts
        self._load_fonts()
    
    def _get_font_fallback(self, original_font: str) -> str:
        """
        Get fallback font for a missing font.
        
        Args:
            original_font: The original font name
            
        Returns:
            Fallback font name
        """
        # Define fallback mappings
        fallback_mappings = {
            'Unna-Bold': 'Helvetica-Bold',
            'Unna-Italic': 'Helvetica-Oblique',
            'Lora-Bold': 'Times-Bold',
            'Lora-Regular': 'Times-Roman',
            'AlexBrush': 'Courier-Bold'  # fallback for AlexBrush
        }
        
        return fallback_mappings.get(original_font, 'Helvetica')
    
    def _load_fonts(self):
        """
        Load custom fonts for certificate generation.
        
        This method attempts to load the required fonts (Unna, Lora, AlexBrush)
        and registers them with ReportLab for use in PDF generation.
        """
        try:
            fonts_dir = Path("assets/fonts")
            missing_fonts = []
            
            # Define font mappings
            font_files = {
                'Unna-Bold': fonts_dir / 'Unna-Bold.ttf',
                'Unna-Italic': fonts_dir / 'Unna-Italic.ttf',
                'Lora-Bold': fonts_dir / 'Lora-Bold.ttf',
                'Lora-Regular': fonts_dir / 'Lora-Regular.ttf',
                'AlexBrush': fonts_dir / 'Alex_Brush' / 'AlexBrush-Regular.ttf'
            }
            
            # Load and register fonts
            for font_name, font_path in font_files.items():
                if font_path.exists():
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                        logging.info(f"Loaded font: {font_name}")
                        self.generation_summary['font_usage']['custom_fonts_loaded'].append(font_name)
                    except Exception as e:
                        logging.warning(f"Failed to register font {font_name}: {str(e)}")
                        missing_fonts.append(font_name)
                        self.generation_summary['font_usage']['missing_fonts'].append(font_name)
                else:
                    logging.warning(f"Font file not found: {font_path}")
                    missing_fonts.append(font_name)
                    self.generation_summary['font_usage']['missing_fonts'].append(font_name)
            
            # Handle missing fonts automatically
            if missing_fonts:
                logging.warning(f"Missing fonts: {', '.join(missing_fonts)}. Using fallbacks.")
                for missing_font in missing_fonts:
                    fallback_font = self._get_font_fallback(missing_font)
                    self.font_fallbacks[missing_font] = fallback_font
                    logging.info(f"Using fallback font '{fallback_font}' for '{missing_font}'")
                    self.generation_summary['font_usage']['fallback_fonts_used'].append({
                        'original': missing_font,
                        'fallback': fallback_font
                    })
            
            self.fonts_loaded = True
            logging.info("Font loading completed")
            
        except Exception as e:
            logging.error(f"Error loading fonts: {str(e)}")
            raise FontError(f"Failed to load fonts: {str(e)}")
    
    def _get_available_font(self, preferred_font: str) -> str:
        """
        Get the best available font for a given preference.
        
        Args:
            preferred_font: The preferred font name
            
        Returns:
            Available font name (preferred or fallback)
        """
        # Check if preferred font is available
        try:
            # Test if font is registered
            from reportlab.pdfbase.pdfmetrics import getFont
            getFont(preferred_font)
            return preferred_font
        except:
            # Use fallback if available
            fallback = self.font_fallbacks.get(preferred_font)
            if fallback:
                return fallback
            else:
                # Use system default fallback
                return self._get_font_fallback(preferred_font)
    
    def read_csv_data(self, csv_path: str) -> pd.DataFrame:
        """
        Read and validate CSV data for certificate generation.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            pandas DataFrame with validated data
            
        Raises:
            CSVError: If CSV file cannot be read or is invalid
        """
        try:
            if not os.path.exists(csv_path):
                raise CSVError(f"CSV file not found: {csv_path}")
            
            df = pd.read_csv(csv_path)
            logging.info(f"Successfully read CSV file: {csv_path}")
            logging.info(f"CSV contains {len(df)} rows and {len(df.columns)} columns")
            
            # Validate required columns
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                raise CSVError(f"Missing required columns: {missing_columns}")
            
            # Remove rows with missing required data
            initial_count = len(df)
            df = df.dropna(subset=self.required_columns)
            removed_count = initial_count - len(df)
            
            if removed_count > 0:
                logging.warning(f"Removed {removed_count} rows with missing required data")
            
            logging.info(f"Valid data rows: {len(df)}")
            return df
            
        except pd.errors.EmptyDataError:
            raise CSVError("CSV file is empty")
        except pd.errors.ParserError as e:
            raise CSVError(f"Error parsing CSV file: {str(e)}")
        except Exception as e:
            raise CSVError(f"Unexpected error reading CSV: {str(e)}")
    
    def format_date(self, date_str: str) -> str:
        """
        Format date from MM/DD/YYYY to Day-th Mon YYYY format.
        
        Args:
            date_str: Date string in MM/DD/YYYY format
            
        Returns:
            Formatted date string (e.g., "2nd Jul 2025")
        """
        try:
            # Parse the date
            date_obj = datetime.strptime(date_str, "%m/%d/%y")
            
            # Get day suffix
            day = date_obj.day
            if 4 <= day <= 20 or 24 <= day <= 30:
                suffix = "th"
            else:
                suffix = ["st", "nd", "rd"][day % 10 - 1]
            
            # Format the date
            formatted_date = date_obj.strftime(f"%d{suffix} %b %Y")
            return formatted_date
            
        except ValueError as e:
            logging.warning(f"Invalid date format '{date_str}': {str(e)}")
            return date_str  # Return original if parsing fails
    
    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        """
        Calculate the width of text in points.
        
        Args:
            text: Text to measure
            font_name: Font name
            font_size: Font size in points
            
        Returns:
            Text width in points
        """
        try:
            # Create a temporary canvas to measure text
            from reportlab.pdfgen import canvas
            from io import BytesIO
            
            buffer = BytesIO()
            temp_canvas = canvas.Canvas(buffer, pagesize=landscape(A4))
            temp_canvas.setFont(font_name, font_size)
            
            # Get text width
            text_width = temp_canvas.stringWidth(text, font_name, font_size)
            return text_width
            
        except Exception as e:
            logging.warning(f"Error measuring text width: {str(e)}")
            # Fallback: estimate width based on character count
            return len(text) * font_size * 0.6
    
    def _draw_centered_text(self, canvas_obj, text: str, font_name: str, font_size: float, y_position: float, max_width: float = None):
        """
        Draw text centered horizontally on the canvas.
        
        Args:
            canvas_obj: ReportLab canvas object
            text: Text to draw
            font_name: Font name
            font_size: Font size in points
            y_position: Y position on the canvas
            max_width: Maximum width for text wrapping (optional)
        """
        try:
            # Get available font (preferred or fallback)
            available_font = self._get_available_font(font_name)
            canvas_obj.setFont(available_font, font_size)
            
            # Get text width
            text_width = self._get_text_width(text, available_font, font_size)
            
            # Calculate center position
            width, height = landscape(A4)
            x_position = (width - text_width) / 2
            
            # Handle text that's too wide
            if max_width and text_width > max_width:
                # Truncate text and add ellipsis
                while self._get_text_width(text + "...", available_font, font_size) > max_width and len(text) > 0:
                    text = text[:-1]
                
                text += "..."
                text_width = self._get_text_width(text, available_font, font_size)
                x_position = (width - text_width) / 2
            
            # Ensure text doesn't go off the page
            if x_position < 50:  # 50pt margin
                x_position = 50
            elif x_position + text_width > width - 50:
                x_position = width - text_width - 50
            
            canvas_obj.drawString(x_position, y_position, text)
            
        except Exception as e:
            logging.error(f"Error drawing centered text: {str(e)}")
            # Fallback to original positioning
            canvas_obj.drawString(width/2 - 100, y_position, text)
    
    def _draw_left_aligned_text(self, canvas_obj, text: str, font_name: str, font_size: float, x_position: float, y_position: float, max_width: float = None):
        """
        Draw text left-aligned on the canvas.
        
        Args:
            canvas_obj: ReportLab canvas object
            text: Text to draw
            font_name: Font name
            font_size: Font size in points
            x_position: X position on the canvas
            y_position: Y position on the canvas
            max_width: Maximum width for text wrapping (optional)
        """
        try:
            # Get available font (preferred or fallback)
            available_font = self._get_available_font(font_name)
            canvas_obj.setFont(available_font, font_size)
            
            # Get text width
            text_width = self._get_text_width(text, available_font, font_size)
            
            # Handle text that's too wide
            if max_width and text_width > max_width:
                # Truncate text and add ellipsis
                while text_width > max_width and len(text) > 3:
                    text = text[:-1] + "..."
                    text_width = self._get_text_width(text, available_font, font_size)
            
            canvas_obj.drawString(x_position, y_position, text)
            
        except Exception as e:
            logging.error(f"Error drawing left-aligned text: {str(e)}")
            # Fallback to original positioning
            canvas_obj.drawString(x_position, y_position, text)
            
    def _draw_centered_paragraph(self, canvas_obj, text: str, font_name: str, font_size: float, y_position: float, max_width: float, leading: float):
        """
        Draw a paragraph centered horizontally on the canvas with text wrapping.
        
        Args:
            canvas_obj: ReportLab canvas object
            text: Text to draw
            font_name: Font name
            font_size: Font size in points
            y_position: Y position on the canvas
            max_width: Maximum width for the paragraph
            leading: Line spacing for the paragraph
        """
        try:
            available_font = self._get_available_font(font_name)
            
            # Create a paragraph style
            style = ParagraphStyle(
                name='CenteredParagraph',
                fontName=available_font,
                fontSize=font_size,
                leading=leading,
                alignment=TA_CENTER
            )
            
            # Create paragraph and wrap it
            p = Paragraph(text, style)
            width, height = landscape(A4)
            p_width, p_height = p.wrapOn(canvas_obj, max_width, height)
            
            # Draw the paragraph
            p.drawOn(canvas_obj, (width - max_width) / 2, y_position - p_height)

        except Exception as e:
            logging.error(f"Error drawing centered paragraph: {str(e)}")
            # Fallback to single-line text
            self._draw_centered_text(canvas_obj, text, font_name, font_size, y_position, max_width)

    def _draw_centered_text_in_column(self, canvas_obj, text: str, font_name: str, font_size: float, y_position: float, column_x_start: float, column_width: float):
        """
        Draw text centered horizontally within a specific column.
        
        Args:
            canvas_obj: ReportLab canvas object
            text: Text to draw
            font_name: Font name
            font_size: Font size in points
            y_position: Y position on the canvas
            column_x_start: The starting X position of the column
            column_width: The width of the column
        """
        try:
            available_font = self._get_available_font(font_name)
            canvas_obj.setFont(available_font, font_size)
            
            text_width = self._get_text_width(text, available_font, font_size)
            x_position = column_x_start + (column_width - text_width) / 2
            
            canvas_obj.drawString(x_position, y_position, text)

        except Exception as e:
            logging.error(f"Error drawing centered text in column: {str(e)}")
            # Fallback to default positioning
            canvas_obj.drawString(column_x_start, y_position, text)

    
    def generate_certificate(self, student_data: Dict[str, Any], output_path: str, template_path: str) -> bool:
        """
        Generate a single certificate PDF with personalized student information.
        
        This method creates a professional certificate layout with the following elements:
        - Student name prominently displayed
        - Course completion information
        - Completion date (formatted)
        - College/institution name
        
        Args:
            student_data (dict): Dictionary containing student information
            output_path (str): Path where the certificate PDF should be saved
            template_path (str): Path to the background PDF template
            
        Returns:
            bool: True if generation successful, False otherwise
        """
        try:
            # Create a temporary in-memory PDF for the text layer
            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=landscape(A4))
            
            # Student name - centered above the horizontal divider
            student_name = student_data['name'].upper()
            self._draw_centered_text(c, student_name, "Lora-Regular", 28, 290, max_width=400)
            
            # Course completion section - using paragraph for wrapping
            course_text = f"The awardee has successfully completed the {student_data['event_type']} on “{student_data['course_type']}” conducted on {self.format_date(student_data['completion_date'])} at"
            self._draw_centered_paragraph(c, course_text, "Lora-Bold", 14.3, 260, max_width=500, leading=20)
            
            self._draw_centered_text(c, student_data['college_name'], "Lora-Bold", 14.3, 205, max_width=400)

            # Mentor details centered within the same column as the course text
            column_width = 500  # Same as course_text max_width
            width, height = landscape(A4)
            column_x_start = (width - column_width) / 2
            
            self._draw_centered_text_in_column(c, student_data['mentor_signature'], "AlexBrush", 18, 152, column_x_start, column_width)
            self._draw_centered_text_in_column(c, student_data['mentor_name'], "Lora-Regular", 12, 122, column_x_start, column_width)
            
            c.save()
            
            # Move to the beginning of the StringIO buffer
            packet.seek(0)
            
            # Create a new PDF with the background template
            template_pdf = PdfReader(open(template_path, "rb"))
            output_pdf = PdfWriter()
            
            # Get the first page of the template
            template_page = template_pdf.pages[0]
            
            # Merge the text layer onto the template
            text_pdf = PdfReader(packet)
            template_page.merge_page(text_pdf.pages[0])
            
            # Add the merged page to the output
            output_pdf.add_page(template_page)
            
            # Write the final PDF to a file
            with open(output_path, "wb") as f:
                output_pdf.write(f)
                
            logging.info(f"Generated certificate: {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error generating certificate for {student_data.get('name', 'Unknown')}: {str(e)}")
            return False

    
    def get_or_create_drive_folder(self, college_name: str, completion_date: str) -> str:
        """
        Search for or create a destination folder in Google Drive.
        
        Args:
            college_name: Name of the college
            completion_date: Completion date in MM/DD/YYYY format
            
        Returns:
            Google Drive folder ID
            
        Raises:
            CertificateGeneratorError: If folder creation fails
        """
        try:
            drive_service = get_drive_service()
            
            # Format the folder name: {college_name}-{date}
            date_obj = datetime.strptime(completion_date, "%m/%d/%Y")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            folder_name = f"{college_name}-{formatted_date}"
            
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if files:
                folder_id = files[0]['id']
                logging.info(f"Found existing folder: {folder_name} (ID: {folder_id})")
                return folder_id
            
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logging.info(f"Created new folder: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logging.error(f"Error creating Google Drive folder: {str(e)}")
            raise CertificateGeneratorError(f"Failed to create Google Drive folder: {str(e)}")
    
    def upload_certificate_to_drive(self, local_file_path: str, drive_folder_id: str, certificate_id: str) -> str:
        """
        Upload a certificate PDF to Google Drive folder.
        
        Args:
            local_file_path: Path to the local certificate file
            drive_folder_id: Google Drive folder ID
            certificate_id: Certificate ID for file naming
            
        Returns:
            Google Drive file ID of uploaded file
            
        Raises:
            CertificateGeneratorError: If upload fails
        """
        try:
            drive_service = get_drive_service()
            
            # Check if file already exists
            query = f"name='{certificate_id}.pdf' and '{drive_folder_id}' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            existing_files = results.get('files', [])
            
            if existing_files:
                # Update existing file
                file_id = existing_files[0]['id']
                media = MediaFileUpload(local_file_path, mimetype='application/pdf', resumable=True)
                file = drive_service.files().update(
                    fileId=file_id,
                    media_body=media,
                    fields='id'
                ).execute()
                logging.info(f"Updated existing certificate: {certificate_id}.pdf")
            else:
                # Create new file
                file_metadata = {
                    'name': f'{certificate_id}.pdf',
                    'parents': [drive_folder_id]
                }
                media = MediaFileUpload(local_file_path, mimetype='application/pdf', resumable=True)
                file = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logging.info(f"Uploaded new certificate: {certificate_id}.pdf")
            
            return file.get('id')
            
        except Exception as e:
            logging.error(f"Error uploading certificate to Google Drive: {str(e)}")
            raise CertificateGeneratorError(f"Failed to upload certificate to Google Drive: {str(e)}")
    
    def process_csv_file(self, csv_path: str, output_dir: str, template_path: str) -> Dict[str, Any]:
        """
        Process the entire CSV file and generate certificates for all valid entries.
        
        This method performs the following steps:
        1. Validates and reads the CSV file
        2. Creates the output directory if it doesn't exist
        3. Processes each row to generate individual certificates
        4. Handles errors gracefully and continues processing
        5. Provides a comprehensive summary of the operation
        
        Args:
            csv_path (str): Path to the input CSV file containing student data
            output_dir (str): Directory where generated certificates should be saved
            template_path (str): Path to the background PDF template
            
        Returns:
            dict: Dictionary containing generation summary
        """
        try:
            # Read and validate CSV data
            df = self.read_csv_data(csv_path)
            
            # Track CSV source and output directory
            self.generation_summary['csv_source'] = csv_path
            self.generation_summary['output_directory'] = os.path.abspath(output_dir)
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Process each row
            for index, row in df.iterrows():
                self.generation_summary['total_processed'] += 1
                
                try:
                    student_data = row.to_dict()
                    certificate_id = student_data['certificate_id']
                    output_path = os.path.join(output_dir, f"{certificate_id}.pdf")
                    
                    if self.generate_certificate(student_data, output_path, template_path):
                        self.generation_summary['successful'] += 1
                        # TODO: Re-enable Google Drive upload after testing
                        # drive_folder_id = self.get_or_create_drive_folder(student_data['college_name'], student_data['completion_date'])
                        # self.upload_certificate_to_drive(output_path, drive_folder_id, certificate_id)
                        self.generation_summary['file_locations'].append({
                            'certificate_id': certificate_id,
                            'name': student_data.get('name', 'Unknown'),
                            'file_path': os.path.abspath(output_path),
                            'file_size': os.path.getsize(output_path) if os.path.exists(output_path) else 0
                        })
                    else:
                        self.generation_summary['failed'] += 1
                        self.generation_summary['errors'].append({
                            'row': index + 1,
                            'name': student_data.get('name', 'Unknown'),
                            'error': 'PDF generation failed'
                        })
                        
                except Exception as e:
                    self.generation_summary['failed'] += 1
                    self.generation_summary['errors'].append({
                        'row': index + 1,
                        'name': row.get('name', 'Unknown'),
                        'error': str(e)
                    })
                    logging.error(f"Error processing row {index + 1}: {str(e)}")
            
            logging.info(f"Certificate generation completed:")
            logging.info(f"  Total processed: {self.generation_summary['total_processed']}")
            logging.info(f"  Successful: {self.generation_summary['successful']}")
            logging.info(f"  Failed: {self.generation_summary['failed']}")
            
            return self.generation_summary
            
        except Exception as e:
            logging.error(f"Error processing CSV file: {str(e)}")
            raise CertificateGeneratorError(f"Failed to process CSV file: {str(e)}")

def main():
    """
    Main function for certificate generation script.
    
    Handles command-line arguments and orchestrates the certificate generation process.
    """
    parser = argparse.ArgumentParser(description="Generate certificates from CSV data using a PDF template")
    parser.add_argument("csv_file", help="Path to the CSV file containing student data")
    parser.add_argument("template_file", help="Path to the background PDF template")
    parser.add_argument(
        "--output-dir",
        default="generated_certificates",
        help="Directory to save generated certificates (default: generated_certificates)"
    )
    
    args = parser.parse_args()
    
    try:
        generator = CertificateGenerator()
        summary = generator.process_csv_file(args.csv_file, args.output_dir, args.template_file)
        
        print("\n" + "="*60)
        print("CERTIFICATE GENERATION SUMMARY")
        print("="*60)
        print(f"Total processed: {summary['total_processed']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        
        if summary['errors']:
            print(f"\nErrors:")
            for error in summary['errors']:
                print(f"  Row {error['row']} ({error['name']}): {error['error']}")
        
        if summary['file_locations']:
            print(f"\nFile Storage Locations:")
            print(f"  Output Directory: {summary['output_directory']}")
            print(f"  CSV Source: {summary['csv_source']}")
            print(f"  Generated Files:")
            total_size = 0
            for file_info in summary['file_locations']:
                size_mb = file_info['file_size'] / (1024 * 1024)
                print(f"    {file_info['certificate_id']}.pdf ({file_info['name']}) - {size_mb:.2f} MB")
                total_size += file_info['file_size']
            total_size_mb = total_size / (1024 * 1024)
            print(f"  Total Size: {total_size_mb:.2f} MB")
        
        if summary['font_usage']:
            print(f"\nFont Usage Report:")
            if summary['font_usage']['custom_fonts_loaded']:
                print(f"  Custom Fonts Loaded: {', '.join(summary['font_usage']['custom_fonts_loaded'])}")
            if summary['font_usage']['fallback_fonts_used']:
                print(f"  Fallback Fonts Used:")
                for fallback in summary['font_usage']['fallback_fonts_used']:
                    print(f"    {fallback['original']} → {fallback['fallback']}")
            if summary['font_usage']['missing_fonts']:
                print(f"  Missing Fonts: {', '.join(summary['font_usage']['missing_fonts'])}")
        
        print("="*60)
        
    except Exception as e:
        logging.error(f"Certificate generation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
