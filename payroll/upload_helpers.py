import logging
import zipfile
import os
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def validate_zip_file(file):
    """
    Validates the uploaded ZIP file for security and integrity.
    """
    # 1. Check Magic Bytes
    if not zipfile.is_zipfile(file):
        raise ValidationError("The uploaded file is not a valid ZIP file.")

    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            # 2. Limit entry count
            if len(zip_ref.infolist()) > 500:
                raise ValidationError("ZIP archive contains too many files (max 500).")
            
            total_uncompressed_size = 0
            for info in zip_ref.infolist():
                # 3. Zip-Slip Defense: prevent path traversal
                if info.filename.startswith('/') or '..' in info.filename:
                    logger.warning(f"Zip-Slip attempt detected: {info.filename}")
                    raise ValidationError("ZIP archive contains invalid file paths (traversal attempt).")
                
                # 4. Zip-Bomb Defense: limit individual and total size
                if info.file_size > 10 * 1024 * 1024: # 10MB per file
                    raise ValidationError(f"ZIP member {info.filename} exceeds 10MB limit.")
                
                total_uncompressed_size += info.file_size
                if total_uncompressed_size > 200 * 1024 * 1024: # 200MB total
                    raise ValidationError("Total uncompressed size of ZIP exceeds 200MB limit.")

    except ValidationError:
        raise
    except Exception as e:
        # Log the internal details before raising a generic error to the user
        logger.exception("ZIP validation internal error")
        raise ValidationError("An error occurred while validating the ZIP file.")
