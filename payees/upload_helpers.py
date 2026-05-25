import os
import logging
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


def validate_image(file):
    try:
        try:
            with Image.open(file) as img:
                img.verify()
        except (IOError, SyntaxError, UnidentifiedImageError) as e:
            logger.warning(f"Image validation failed: {e}", exc_info=True)
            raise ValidationError("The uploaded file is not a valid image.")
    finally:
        # Reset file pointer after verify() as it consumes the stream, always running on success or failure
        file.seek(0)


def user_directory_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/uploads/payees/bank-acknowledgement/user_<hrm_id>/<filename>
    base_filename, file_extension = os.path.splitext(filename)
    safe_base = get_valid_filename(base_filename)
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    safe_filename = f"{safe_base}_{timestamp}{file_extension}"
    return f"uploads/payees/bank-acknowledgement/user_" \
           f"{instance.payee.hrm_id}/{safe_filename}"
