#!/bin/bash

# Certificate Generation and Email Sending Workflow
# This script automates the entire process of generating certificates and sending them via email

# Exit on any error
set -e

# Display usage information
show_usage() {
  echo "Usage: $0 <csv_file> <template_pdf> [output_dir]"
  echo ""
  echo "Arguments:"
  echo "  csv_file      Path to the CSV file containing student data"
  echo "  template_pdf  Path to the PDF template for certificates"
  echo "  output_dir    Optional: Directory to save certificates (default: 'certificates')"
  echo ""
  echo "Example:"
  echo "  $0 real_students.csv /path/to/template.pdf certificates"
  exit 1
}

# Check for required arguments
if [ "$#" -lt 2 ]; then
  show_usage
fi

# Set variables from arguments
CSV_FILE="$1"
TEMPLATE_PDF="$2"
OUTPUT_DIR="${3:-certificates}"

# Check if files exist
if [ ! -f "$CSV_FILE" ]; then
  echo "Error: CSV file '$CSV_FILE' not found"
  exit 1
fi

if [ ! -f "$TEMPLATE_PDF" ]; then
  echo "Error: Template PDF '$TEMPLATE_PDF' not found"
  exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
  echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
pip install -r requirements.txt

# Update .env file for email sending
echo "Configuring environment for email sending..."
cat > .env << EOL
# Environment variables for Automated Student Email Workflow

# Using local CSV file
LOCAL_CSV_PATH=$(pwd)/$CSV_FILE

# Local certificates directory
CERTIFICATES_DIR=$(pwd)/$OUTPUT_DIR

# Email settings
EMAIL_SUBJECT_TEMPLATE=Certificate of Participation
EMAIL_BODY_TEMPLATE=Dear {name},\n\nThank you for participating in our event. Please find attached your certificate of participation.\n\nBest regards,\nPlutus Education
EOL

# Generate certificates
echo "\n========================================"
echo "STEP 1: GENERATING CERTIFICATES"
echo "========================================\n"
echo "Generating certificates using $CSV_FILE and $TEMPLATE_PDF..."
python3 certificate_generator.py "$CSV_FILE" "$TEMPLATE_PDF" --output-dir "$OUTPUT_DIR"

# Send emails
echo "\n========================================"
echo "STEP 2: SENDING EMAILS"
echo "========================================\n"
echo "Sending emails with certificates..."
python3 email_sender.py

echo "\n========================================"
echo "WORKFLOW COMPLETED SUCCESSFULLY"
echo "========================================\n"
echo "Certificates were generated and emails were sent."
echo "Check the log files for details:"
echo "  - Certificate generation: certificate_generator.log"
echo "  - Email sending: email_sender.log"

# Deactivate virtual environment
deactivate