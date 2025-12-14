#!/usr/bin/python
import os
import time
import logging
import argparse
from datetime import datetime

# You must have rocketpdf and pikepdf installed:
# pip install rocketpdf pikepdf

try:
    from rocketpdf import RocketPDF
    from pikepdf import Pdf, PdfError
except ImportError as e:
    print(f"Error: Required library not found. Please run 'pip install rocketpdf pikepdf'")
    print(f"Details: {e}")
    exit(1)

# ⎯⎯ Configuration ⎯⎯
SOURCE_DIR = 'input_docs'
DESTINATION_DIR = 'output_pdfs'
# LOG_FILE path is determined in main based on DESTINATION_DIR

# ⎯⎯ Setup Functions ⎯⎯

def setup_directories(dest_dir: str):
    """
    Creates the source and destination directories if they don't exist.

    Args:
        dest_dir: The path to the output directory.
    """
    os.makedirs(SOURCE_DIR, exist_ok=True)
    os.makedirs(dest_dir, exist_ok=True)

def setup_logging(dest_dir: str) -> str:
    """
    Initializes the logging system to output to a file and the console.

    Args:
        dest_dir: The path to the output directory where the log file will reside.

    Returns:
        The full path to the log file.
    """
    LOG_FILE = os.path.join(dest_dir, 'conversion_log.log')
    
    # Configure logging to write to file
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Also log to console for immediate feedback
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # Use a simpler format for console output
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console.setFormatter(formatter)
    
    # Clear existing handlers (ensures no duplicate console output if run repeatedly)
    root_logger = logging.getLogger('')
    if not root_logger.handlers:
        root_logger.addHandler(console)
        
    logging.info("⎯⎯ Program Start ⎯⎯")
    return LOG_FILE

# ⎯⎯ Core Processing Functions ⎯⎯

def convert_docx_to_pdf(source_path: str, dest_path: str, skip_existing: bool) -> bool:
    """
    Converts a .docx file to a .pdf file using rocketpdf.
    
    Handles skipping conversion if the destination PDF already exists and the skip flag is set.

    Args:
        source_path: The full path to the input .docx file.
        dest_path: The full path where the output .pdf file should be written.
        skip_existing: If True, skips conversion if dest_path already exists.

    Returns:
        True on conversion success or if the file was skipped, False on failure.
    """
    if skip_existing and os.path.exists(dest_path):
        logging.warning(f"SKIPPED: PDF already exists at '{dest_path}'.")
        # Return True so that the file is still considered for validation/deletion
        return True 
        
    try:
        pdf_converter = RocketPDF()
        pdf_converter.convert(source_path, dest_path)
        logging.info(f"SUCCESS: Converted '{source_path}' to '{dest_path}'")
        return True
    except Exception as e:
        logging.error(f"CONVERSION_FAIL: Failed to convert '{source_path}'. Error: {e}")
        return False

def validate_pdf(pdf_path: str) -> bool:
    """
    Validates a PDF file using pikepdf's native Python API.
    
    The act of opening the PDF with Pdf.open() forces pikepdf to check the file's
    structural integrity. It raises PdfError if the file is invalid or corrupt.

    Args:
        pdf_path: The full path to the PDF file to validate.

    Returns:
        True if the PDF is valid, False otherwise.
    """
    try:
        # Using a 'with' statement ensures the file handle is properly closed.
        with Pdf.open(pdf_path) as pdf:
            pass # File opened successfully, so it's valid.

        logging.info(f"VALIDATION_SUCCESS: '{pdf_path}' is a valid PDF.")
        return True

    except PdfError as e:
        # Catch errors related to invalid PDF structure or corruption.
        logging.warning(f"VALIDATION_FAIL: '{pdf_path}' is INVALID/CORRUPTED. Error: {e}")
        return False
        
    except FileNotFoundError:
        # Catch case where the previous conversion step failed to create the file.
        logging.error(f"VALIDATION_ERROR: File not found at '{pdf_path}'. Cannot validate.")
        return False
        
    except Exception as e:
        # Catch any other unexpected file access or I/O errors.
        logging.error(f"VALIDATION_ERROR: Could not open '{pdf_path}' for validation. Unexpected Error: {e}")
        return False

def remove_source_file(source_path: str, remove_original: bool):
    """
    Removes the original source file if the 'remove_original' flag is True.

    Args:
        source_path: The full path to the file to be removed.
        remove_original: A boolean flag indicating whether to perform the removal.
    """
    if remove_original:
        try:
            os.remove(source_path)
            logging.info(f"CLEANUP: Removed original file '{source_path}'.")
        except OSError as e:
            logging.error(f"CLEANUP_FAIL: Could not remove '{source_path}'. Error: {e}")

def process_directory_recursively(args: argparse.Namespace) -> dict:
    """
    Recursively finds all .docx files, converts them, and validates the output.

    Args:
        args: The parsed command-line arguments containing directory paths and flags.

    Returns:
        A dictionary summarizing the results of all operations.
    """
    results = {
        'files_found': 0,
        'conversion_success': 0,
        'conversion_fail': 0,
        'validation_success': 0,
        'validation_fail': 0,
        'files_removed': 0,
        'files_skipped': 0
    }

    # os.walk traverses the directory tree recursively.
    for root, _, files in os.walk(args.source_dir):
        # Logic to preserve the directory structure in the destination
        relative_path = os.path.relpath(root, args.source_dir)
        current_dest_dir = os.path.join(args.destination_dir, relative_path)
        os.makedirs(current_dest_dir, exist_ok=True)

        for filename in files:
            if filename.lower().endswith('.docx'):
                results['files_found'] += 1
                source_file_path = os.path.join(root, filename)
                
                # Construct the output PDF filename
                pdf_filename = filename[:-5] + '.pdf' # Remove .docx and add .pdf
                dest_file_path = os.path.join(current_dest_dir, pdf_filename)
                
                # 1. Convert
                conversion_result = convert_docx_to_pdf(
                    source_file_path, dest_file_path, args.skip_existing
                )
                
                # Check if the file was skipped and the conversion method returned True
                if conversion_result and args.skip_existing and os.path.exists(dest_file_path):
                    if 'SKIPPED' in open(LOG_FILE, 'r').read() and f"'{dest_file_path}'" in open(LOG_FILE, 'r').read(): # Crude check for log entry
                        results['files_skipped'] += 1
                        
                if conversion_result:
                    results['conversion_success'] += 1
                    
                    # 2. Validate
                    if validate_pdf(dest_file_path):
                        results['validation_success'] += 1
                        
                        # 3. Optional Removal: ONLY if valid
                        if args.remove_original:
                            remove_source_file(source_file_path, args.remove_original)
                            results['files_removed'] += 1
                    else:
                        results['validation_fail'] += 1
                else:
                    results['conversion_fail'] += 1
                
    return results

# ⎯⎯ Argument Parsing and Main Execution ⎯⎯

def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments to control program behavior.

    Returns:
        The parsed command-line arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Recursively convert DOCX files to validated PDF format using rocketpdf and pikepdf.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Optional Flag for Deletion
    parser.add_argument(
        '-r', '--remove-original', 
        action='store_true',
        help="If set, the original .docx file will be deleted ONLY IF the resulting PDF is valid."
    )
    
    # Optional Flag for Skipping Existing
    parser.add_argument(
        '-s', '--skip-existing', 
        action='store_true',
        help="If set, skips the conversion process if the resulting .pdf file already exists."
    )
    
    # Optional Overrides for Directories
    parser.add_argument(
        '-i', '--source-dir', 
        type=str,
        default=SOURCE_DIR,
        help=f"Input directory containing .docx files (default: {SOURCE_DIR})"
    )
    parser.add_argument(
        '-o', '--destination-dir', 
        type=str,
        default=DESTINATION_DIR,
        help=f"Output directory for .pdf files and log (default: {DESTINATION_DIR})"
    )
    
    return parser.parse_args()

def main():
    """
    The main execution function. Handles setup, processing, timing, and summary generation.
    
    Usage Examples:
    
    1. Default Run (Convert all, don't remove, don't skip):
       python script_name.py
       
    2. Convert, Validate, and Remove Originals (If valid):
       python script_name.py -r
       
    3. Skip Existing PDFs and Convert New Ones:
       python script_name.py -s
       
    4. Run with all flags and custom directories:
       python script_name.py -r -s -i /path/to/docs -o /path/to/output
    """
    args = parse_args()
    start_time = time.time()
    
    # 1. Setup
    setup_directories(args.destination_dir)
    global LOG_FILE 
    LOG_FILE = setup_logging(args.destination_dir)
    
    logging.info(f"Source Directory: {args.source_dir}")
    logging.info(f"Destination Directory: {args.destination_dir}")
    logging.info(f"Log File: {LOG_FILE}")
    logging.info(f"Remove Original DOCX: {'YES' if args.remove_original else 'NO'}")
    logging.info(f"Skip Existing PDFs: {'YES' if args.skip_existing else 'NO'}")
    
    # 2. Processing
    logging.info("Starting recursive file conversion and validation...")
    results = process_directory_recursively(args)
    
    # 3. Time Measurement and Summary
    end_time = time.time()
    total_time = end_time - start_time
    
    # Generate the Summary
    summary = f"""
⎯⎯ PROCESSING SUMMARY ⎯⎯
Total Execution Time: {total_time:.2f} seconds

Files Processed:
  - DOCX Files Found: {results['files_found']}
  - Files Skipped (Already Existed): {results['files_skipped']}

Conversion Results:
  - Successful Conversions: {results['conversion_success']}
  - Failed Conversions: {results['conversion_fail']}

Validation Results:
  - Valid PDFs: {results['validation_success']}
  - Invalid/Corrupt PDFs: {results['validation_fail']}
  
Cleanup Results:
  - Original DOCX Files Removed: {results['files_removed']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    
    # Log the summary
    logging.info(summary)
    
    # Also print it to the console for immediate viewing
    print(summary)
    logging.info("⎯⎯ Program End ⎯⎯")

if __name__ == "__main__":
    main()
