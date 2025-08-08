import logging, sys, os
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logging.info("email_sender loaded from: %s", __file__)
logging.info("cwd: %s", os.getcwd())
import os
import base64
import logging
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
from dotenv import load_dotenv
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_sender.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Custom exception classes
class EmailSenderError(Exception):
    pass
class AuthenticationError(EmailSenderError):
    pass
class FileError(EmailSenderError):
    pass
class EmailError(EmailSenderError):
    pass

# Load environment variables
load_dotenv()

def get_google_credentials():
    """Get Google API credentials"""
    try:
        SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        creds = None
        
        # Get token path from environment variable or use default
        token_path = os.getenv('TOKEN_PATH', 'token.json')
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        
        logging.info(f"Using token path: {token_path}")
        logging.info(f"Using credentials path: {credentials_path}")
        
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            logging.info(f"Loaded credentials from {token_path}")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logging.info("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                logging.info("No valid credentials found, initiating OAuth flow")
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
                logging.info(f"Saved credentials to {token_path}")
        
        return creds
    except Exception as e:
        logging.error(f"Failed to get Google credentials: {str(e)}")
        raise AuthenticationError(f"Failed to authenticate with Google: {str(e)}")

def download_certificate_from_drive(folder_id, certificate_id):
    """Download certificate file from Google Drive folder"""
    try:
        creds = get_google_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Search for the certificate file in the folder
        query = f"'{folder_id}' in parents and name='{certificate_id}.png'"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if not files:
            logging.warning(f"Certificate file {certificate_id}.png not found in Google Drive folder")
            return None
        
        file_id = files[0]['id']
        file_path = f"temp_certificate_{certificate_id}.png"
        
        # Download the file
        request = drive_service.files().get_media(fileId=file_id)
        with open(file_path, 'wb') as fh:
            response = request.execute()
            fh.write(response)
        
        logging.info(f"Successfully downloaded certificate {certificate_id}.png from Google Drive")
        return file_path
        
    except Exception as e:
        logging.error(f"Error downloading certificate {certificate_id}.png: {str(e)}")
        return None

def create_email_message(to_email, subject, body, attachment_path=None):
    """Create email message with optional attachment"""
    try:
        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Add attachment if provided
        if attachment_path:
            if not os.path.exists(attachment_path):
                raise FileNotFoundError(f"Attachment file not found: {attachment_path}")
                
            content_type, encoding = mimetypes.guess_type(attachment_path)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            
            main_type, sub_type = content_type.split('/', 1)
            with open(attachment_path, 'rb') as fp:
                attachment = MIMEBase(main_type, sub_type)
                attachment.set_payload(fp.read())
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition',
                                   'attachment', filename=os.path.basename(attachment_path))
                message.attach(attachment)
        
        logging.info(f"Successfully created email message for {to_email}")
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    except Exception as e:
        logging.error(f"Error creating email message: {str(e)}")
        raise EmailError(f"Failed to create email message: {str(e)}")

def send_email(to_email, subject, body, attachment_path=None):
    """Send email using Gmail API"""
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        message = create_email_message(to_email, subject, body, attachment_path)
        result = service.users().messages().send(userId="me", body=message).execute()
        
        logging.info(f"Successfully sent email to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {to_email}: {str(e)}")
        raise EmailError(f"Failed to send email to {to_email}: {str(e)}")

def main():
    """Main function to process and send emails - DYNAMIC VERSION"""
    try:
        logging.info("Starting email sending process")
        
        # Get environment variables - DYNAMIC: Check for both options
        CSV_FILE_ID = os.getenv('CSV_FILE_ID')
        LOCAL_CSV_PATH = os.getenv('LOCAL_CSV_PATH')
        
        csv_path = None
        is_downloaded_file = False
        
        # DYNAMIC CSV SOURCE DETECTION
        if LOCAL_CSV_PATH:
            # Use local CSV file - NO GOOGLE DRIVE NEEDED!
            if not os.path.exists(LOCAL_CSV_PATH):
                raise ValueError(f'Local CSV file not found: {LOCAL_CSV_PATH}')
            csv_path = LOCAL_CSV_PATH
            logging.info(f"Using local CSV file: {csv_path}")
            # No Google Drive authentication needed!
            
        elif CSV_FILE_ID:
            # Download CSV from Google Drive (existing functionality)
            csv_path = download_csv_from_drive(CSV_FILE_ID)
            is_downloaded_file = True
            logging.info(f"Downloaded CSV from Google Drive: {csv_path}")
            
        else:
            raise ValueError('Either CSV_FILE_ID or LOCAL_CSV_PATH environment variable must be set')
        
        # Read CSV data (same for both options)
        df = pd.read_csv(csv_path)
        
        # Validate CSV columns (same for both options)
        required_columns = ['name', 'email', 'certificate_id']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in CSV: {', '.join(missing_columns)}")
        
        # Email template (same for both options)
        subject = "Certificate of Participation"
        body_template = "Dear {name},\n\nThank you for participating in our event. Please find attached your certificate of participation.\n\nBest regards,\nPlutus Education"
        
        # Use local certificates directory (same for both options)
        certificates_dir = os.getenv('CERTIFICATES_DIR', "/Users/classplus/Downloads/certificates")
        
        # Send emails (same for both options)
        success_count = 0
        failure_count = 0
        
        for _, row in df.iterrows():
            try:
                name = row['name']
                email = row['email']
                # Support both PNG and PDF formats
                pdf_path = os.path.join(certificates_dir, f"{row['certificate_id']}.pdf")
                png_path = os.path.join(certificates_dir, f"{row['certificate_id']}.png")
                
                if os.path.exists(pdf_path):
                    certificate_path = pdf_path
                elif os.path.exists(png_path):
                    certificate_path = png_path
                else:
                    certificate_path = None
                
                if certificate_path is None or not os.path.exists(certificate_path):
                    logging.warning(f"Certificate file not found for {name} with ID {row['certificate_id']}")
                    continue
                    
                body = body_template.format(name=name)
                send_email(email, subject, body, certificate_path)
                success_count += 1
            except EmailError as e:
                logging.error(f"Failed to process email for {name} ({email}): {str(e)}")
                failure_count += 1
            except Exception as e:
                logging.error(f"Unexpected error for {name} ({email}): {str(e)}")
                failure_count += 1
        
        # Clean up only if we downloaded the CSV file
        if is_downloaded_file and csv_path and os.path.exists(csv_path):
            os.remove(csv_path)
            logging.info("Cleaned up downloaded CSV file")
        
        logging.info(f"Email sending process completed")
        logging.info(f"Summary: {success_count} emails sent successfully, {failure_count} failed")
        
    except Exception as e:
        logging.error(f"Critical error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()
