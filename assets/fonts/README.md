# Font Files for Certificate Generation

This directory contains the custom fonts required for certificate generation.

## Required Font Files

The following font files must be placed in this directory for the certificate generator to work properly:

### Unna Font Family
- `Unna-Bold.ttf` - Used for "CERTIFICATE" title (64pt)
- `Unna-Italic.ttf` - Used for "Of Participation" subtitle (64pt)

### Lora Font Family
- `Lora-Bold.ttf` - Used for various bold text elements:
  - "THIS CERTIFICATE IS PROUDLY PRESENTED TO" (14.9pt)
  - Course description text (14.3pt)
  - Mentor name (11.4pt)
- `Lora-Regular.ttf` - Used for:
  - Student name (28pt)
  - "MENTOR" label (10.5pt)

### Moontime Font
- `Moontime.ttf` - Used for mentor signature (26pt)

## Font Specifications

According to the PRD, the exact font specifications are:
- Unna Bold 64pt: "CERTIFICATE" (uppercase)
- Unna Italic 64pt: "Of Participation"
- Lora Bold 14.9pt: "THIS CERTIFICATE IS PROUDLY PRESENTED TO" (uppercase)
- Lora 28pt: Student name (uppercase)
- Lora Bold 14.3pt: Course description text
- Lora Bold 11.4pt: Mentor name
- Lora 10.5pt: "MENTOR" (uppercase)
- Moontime 26pt: Mentor signature

## Installation

1. Download the required font files from their respective sources
2. Place the `.ttf` files in this directory
3. Ensure the filenames match exactly as listed above

## Font Sources

- **Unna**: Available on Google Fonts
- **Lora**: Available on Google Fonts  
- **Moontime**: Custom font - obtain from the design team

## Notes

- The certificate generator will log warnings if font files are missing
- Font fallback mechanisms are implemented for graceful degradation
- All fonts must be in TrueType (.ttf) format 