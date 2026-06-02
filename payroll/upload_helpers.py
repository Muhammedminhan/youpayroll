import logging
import zipfile
import os
import ntpath
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def form16_extracted_path(instance, filename):
    """
    Returns the path for extracting Form16 files.
    """
    return f'uploads/payroll/form16_extracted/{filename}'

def validate_zip_file(file):
    """
    Validates the uploaded ZIP file for security and integrity.
    """
    try:
        # 1. Check Magic Bytes
        if not zipfile.is_zipfile(file):
            raise ValidationError("The uploaded file is not a valid ZIP file.")

        # Reset file pointer after is_zipfile call
        file.seek(0)

        with zipfile.ZipFile(file, 'r') as zip_ref:
            # 2. Limit entry count
            if len(zip_ref.infolist()) > 500:
                raise ValidationError("ZIP archive contains too many files (max 500).")
            
            total_uncompressed_size = 0
            for info in zip_ref.infolist():
                # 3. Zip-Slip Defense: prevent path traversal (reject backslashes and catch standard traversal)
                clean_path = info.filename.replace('\\', '/')
                norm_path = os.path.normpath(clean_path)
                has_drive = bool(ntpath.splitdrive(info.filename)[0])
                if (
                    os.path.isabs(clean_path)
                    or ntpath.isabs(info.filename)
                    or has_drive
                    or norm_path.startswith('/')
                    or norm_path.startswith('..')
                    or '..' in norm_path.split('/')
                    or '\\' in info.filename
                ):
                    logger.warning("Zip-Slip attempt detected in ZIP member path")
                    raise ValidationError("ZIP archive contains invalid file paths (traversal attempt).")
                
                # 4. Zip-Bomb Defense: limit individual size and compression ratio
                if info.file_size > 10 * 1024 * 1024: # 10MB per file
                    raise ValidationError(f"ZIP member {info.filename} exceeds 10MB limit.")
                
                # Reject if compression ratio is unreasonably high (>100x)
                if info.file_size > 0 and info.compress_size == 0:
                    raise ValidationError(f"ZIP member {info.filename} is highly compressed (Zip Bomb attempt).")

                if info.compress_size > 0 and (info.file_size / info.compress_size) > 100:
                    raise ValidationError(f"ZIP member {info.filename} is highly compressed (Zip Bomb attempt).")
                
                total_uncompressed_size += info.file_size
                if total_uncompressed_size > 200 * 1024 * 1024: # 200MB total
                    raise ValidationError("Total uncompressed size of ZIP exceeds 200MB limit.")

    except ValidationError:
        raise
    except Exception:
        # Log the internal details before raising a generic error to the user
        logger.exception("ZIP validation internal error")
        raise ValidationError("An error occurred while validating the ZIP file.")
    finally:
        # Guarantee file pointer reset for subsequent consumers
        file.seek(0)
