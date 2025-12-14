#!/usr/bin/python
import os
import time
import logging
import argparse
from datetime import datetime

# ⎯⎯ IMPORT LIBRARIES ⎯⎯
# We only need pikepdf for this standalone script.
try:
    from pikepdf import Pdf, PdfError
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install pikepdf'")
    print(f"Details: {e}")
    exit(1)
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

# ⎯⎯ Configuration ⎯⎯
SOURCE_DIR = 'input_pdfs' # Default folder name changed to reflect input type
LOG_FILE = '' # Global variable set in setup_logging

# ⎯⎯ Status Constants for Processing ⎯⎯
PDF_SUCCESS = 1
PDF_FAIL = 0

# ⎯⎯ Setup Functions ⎯⎯

def setup_directories(source_dir: str):
    """
    Creates the source directory if it doesn't exist.

    Args:
        source_dir: The path to the input directory.
    """
    os.makedirs(source_dir, exist_ok=True)
    
def setup_logging(source_dir: str) -> str:
    """
    Initializes the logging system to output to a file and the console.
    The log file is placed in the source directory for easy correlation.

    Args:
        source_dir: The path to the input directory where the log file will reside.

    Returns:
        The full path to the log file.
    """
    global LOG_FILE 
    LOG_FILE = os.path.join(source_dir, 'pdf_optimization_log.log')
    
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
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console.setFormatter(formatter)
    
    # Clear existing handlers
    root_logger = logging.getLogger('')
    if not root_logger.handlers:
        root_logger.addHandler(console)
        
    logging.info("⎯⎯ PDF Optimizer Start ⎯⎯")
    return LOG_FILE

# ⎯⎯ Core Processing Function ⎯⎯

def validate_and_compress_pdf(pdf_path: str, skip_existing: bool) -> tuple[int, bool]:
    """
    Validates a PDF file using pikepdf, and if valid, compresses it in place.
    The skip_existing flag is now used to skip optimization if the file has been processed recently.

    Args:
        pdf_path: The full path to the PDF file to validate and compress.
        skip_existing: If True, skips optimization if the output file is newer than the script log.

    Returns:
        A tuple (status: int, is_compressed: bool).
    """
    file_size_before = 0
    file_size_after = 0
    is_compressed = False

    try:
        file_size_before = os.path.getsize(pdf_path)
        
        # 1. Skip Check (using log file timestamp as a proxy for "processed")
        if skip_existing and os.path.exists(LOG_FILE):
             # Check if the PDF file is older than the last time the script successfully ran
             pdf_modified_time = os.path.getmtime(pdf_path)
             log_modified_time = os.path.getmtime(LOG_FILE)
             
             # If the PDF was last modified BEFORE the log was created/updated, skip.
             if pdf_modified_time < log_modified_time:
                 logging.warning(f"SKIPPED: '{pdf_path}' is older than the last optimization run (log file).")
                 # Return success so it's not counted as a failure, but is_compressed is False
                 return PDF_SUCCESS, False

        # 2. Validation (Pdf.open() raises PdfError if corrupt)
        # 3. Compression/Optimization
        with Pdf.open(pdf_path) as pdf:
            pdf.save(pdf_path, optimize_version=True)
            
        file_size_after = os.path.getsize(pdf_path)

        if file_size_after < file_size_before:
            reduction = ((file_size_before - file_size_after) / file_size_before) * 100
            logging.info(f"OPTIMIZATION_SUCCESS: '{pdf_path}' valid and compressed. Size reduced by {reduction:.2f}%.")
            is_compressed = True
        else:
            logging.info(f"OPTIMIZATION_SUCCESS: '{pdf_path}' valid. No size reduction (Size: {file_size_after} bytes).")
            is_compressed = True
            
        return PDF_SUCCESS, is_compressed

    except PdfError as e:
        # Catch errors related to invalid PDF structure or corruption.
        logging.warning(f"VALIDATION_FAIL: '{pdf_path}' is INVALID/CORRUPTED. Error: {e}")
        return PDF_FAIL, False
        
    except FileNotFoundError:
        # Catch case where the file doesn't exist (e.g., deleted during processing).
        logging.error(f"VALIDATION_ERROR: File not found at '{pdf_path}'. Cannot optimize.")
        return PDF_FAIL, False
        
    except Exception as e:
        # Catch any other unexpected file access or I/O errors.
        logging.error(f"VALIDATION_ERROR: Could not process '{pdf_path}'. Unexpected Error: {e}")
        return PDF_FAIL, False

def process_directory_recursively(args: argparse.Namespace) -> dict:
    """
    Recursively finds all .pdf files, validates, and optimizes them in place.

    Args:
        args: The parsed command-line arguments containing directory paths and flags.

    Returns:
        A dictionary summarizing the results of all operations.
    """
    results = {
        'files_found': 0,
        'optimization_success': 0,
        'optimization_fail': 0,
        'files_skipped': 0,
        'size_reduction_count': 0
    }

    # os.walk traverses the directory tree recursively. 
    for root, _, files in os.walk(args.source_dir):
        
        for filename in files:
            if filename.lower().endswith('.pdf'):
                results['files_found'] += 1
                pdf_file_path = os.path.join(root, filename)
                
                # 1. Validate and Optimize
                status, size_reduced = validate_and_compress_pdf(
                    pdf_file_path, args.skip_existing
                )
                
                # 2. Update counts
                if status == PDF_SUCCESS:
                    # Determine if the success was a skip or an actual optimization attempt
                    if "SKIPPED" in open(LOG_FILE, 'r').read() and f"'{pdf_file_path}'" in open(LOG_FILE, 'r').read():
                         # This complex log check is needed if we want to separate "Success" from "Skipped" 
                         # when using the log file timestamp check.
                         results['files_skipped'] += 1
                    else:
                        results['optimization_success'] += 1
                        if size_reduced:
                            results['size_reduction_count'] += 1
                else: 
                    results['optimization_fail'] += 1
                
    return results

# ⎯⎯ Argument Parsing and Main Execution ⎯⎯

def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments to control program behavior.

    Returns:
        The parsed command-line arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Recursively validate and compress PDF files using pikepdf.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Optional Flag for Skipping Existing
    parser.add_argument(
        '-s', '--skip-existing', 
        action='store_true',
        help="If set, skips optimization if the PDF file is older than the last log file timestamp (i.e., already processed)."
    )
    
    # Optional Overrides for Directories
    parser.add_argument(
        '-i', '--source-dir', 
        type=str,
        default=SOURCE_DIR,
        help=f"Input directory containing .pdf files (default: {SOURCE_DIR})"
    )
    
    return parser.parse_args()

def main():
    """
    The main execution function. Handles setup, processing, timing, and summary generation.
    
    Usage Examples:
    
    1. Default Run (Optimize all PDFs):
       python pdf_optimizer.py
       
    2. Optimize, skipping files already processed:
       python pdf_optimizer.py -s
       
    3. Run on a specific folder:
       python pdf_optimizer.py -i /path/to/my/pdfs
    """
    args = parse_args()
    start_time = time.time()
    
    # 1. Setup
    setup_directories(args.source_dir)
    # Log file is created and its modification time will be used for '-s' check.
    setup_logging(args.source_dir) 
    
    logging.info(f"Source Directory: {args.source_dir}")
    logging.info(f"Log File: {LOG_FILE}")
    logging.info(f"Skip Previously Optimized Files: {'YES' if args.skip_existing else 'NO'}")
    
    # 2. Processing
    logging.info("Starting recursive PDF validation and optimization...")
    results = process_directory_recursively(args)
    
    # 3. Time Measurement and Summary
    end_time = time.time()
    total_time = end_time - start_time
    
    # Generate the Summary
    summary = f"""
⎯⎯ PROCESSING SUMMARY ⎯⎯
Total Execution Time: {total_time:.2f} seconds

Files Processed:
  - PDF Files Found: {results['files_found']}
  - Files Skipped (Already Processed): {results['files_skipped']}

Optimization Results:
  - Successfully Validated & Processed: {results['optimization_success']}
  - Files with Size Reduction: {results['size_reduction_count']}
  - Failed (Invalid/Corrupt) PDFs: {results['optimization_fail']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    
    # Log the summary
    logging.info(summary)
    
    # Also print it to the console for immediate viewing
    print(summary)
    logging.info("⎯⎯ Program End ⎯⎯")

if __name__ == "__main__":
    main()
