import io
import zipfile
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .forms import PayRunForm
from .models import Form16, Form16Entry, PayRun, PayRunStatusChoices
from .serializers import Form16EntrySerializer
from .tasks import extract_form16_zip_task
from .upload_helpers import form16_extracted_path, validate_zip_file
from .utils import get_latest_payrun


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_zip(entries):
    """
    Build an in-memory ZIP and return a seekable BytesIO.

    ``entries`` is a list of (arcname, data_bytes) tuples.  Pass
    ``compress_type=zipfile.ZIP_STORED`` (default) or
    ``compress_type=zipfile.ZIP_DEFLATED`` per entry when needed by
    wrapping in a dict: {'name': arcname, 'data': data, 'compress': ...}.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for entry in entries:
            if isinstance(entry, dict):
                zf.writestr(
                    zipfile.ZipInfo(entry['name']),
                    entry['data'],
                    compress_type=entry.get('compress', zipfile.ZIP_STORED),
                )
            else:
                arcname, data = entry
                zf.writestr(arcname, data)
    buf.seek(0)
    return buf


def _make_zip_with_info(info, data, compress_type=zipfile.ZIP_STORED):
    """Build a ZIP whose single entry uses a pre-built ZipInfo object."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr(info, data, compress_type=compress_type)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# PayRunForm tests (pre-existing)
# ---------------------------------------------------------------------------

class Form16UploadPathTest(TestCase):
    def test_form16_entry_upload_path_matches_extraction_task_directory(self):
        self.assertEqual(
            form16_extracted_path(None, 'form16.pdf'),
            'uploads/payroll/form16/extracted/form16.pdf',
        )


class Form16EntrySerializerTest(TestCase):
    def test_form16_entry_uses_unambiguous_related_form16_fields(self):
        form16 = Form16.objects.create(
            financial_year='2025-26',
            form16_zip_file=SimpleUploadedFile('form16.zip', b'PK\x05\x06' + b'\x00' * 18),
        )
        entry = Form16Entry.objects.create(
            financial_year=form16,
            form_16=SimpleUploadedFile('form16.pdf', b'%PDF-1.4'),
        )

        data = Form16EntrySerializer(entry).data

        self.assertEqual(data['financial_year_id'], form16.pk)
        self.assertEqual(data['form16_financial_year'], '2025-26')
        self.assertNotIn('form16_pk', data)
        self.assertNotIn('form16_id', data)
        self.assertNotIn('financial_year', data)


class Form16SignalTest(TestCase):
    def test_logs_only_when_extraction_task_is_dispatched_on_commit(self):
        with mock.patch('payroll.tasks.extract_form16_zip_task.delay') as mock_delay, \
                mock.patch('payroll.signals.logger.info') as mock_info:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                form16 = Form16.objects.create(
                    financial_year='2025-26',
                    form16_zip_file=SimpleUploadedFile('form16.zip', b'PK\x05\x06' + b'\x00' * 18),
                )

            self.assertEqual(len(callbacks), 1)
            mock_delay.assert_not_called()
            mock_info.assert_not_called()

            callbacks[0]()

            mock_delay.assert_called_once_with(form16.pk)
            mock_info.assert_called_once_with(
                f"Dispatched Form16 extraction task for ID {form16.pk}"
            )


class PayRunFormTest(TestCase):
    def test_latest_payrun_uses_period_before_created_at(self):
        older_period_created_later = PayRun.objects.create(
            month=12,
            year=2025,
            status=PayRunStatusChoices.APPROVED,
        )
        latest_period = PayRun.objects.create(
            month=1,
            year=2026,
            status=PayRunStatusChoices.DUE,
        )

        self.assertEqual(get_latest_payrun(), latest_period)
        self.assertNotEqual(get_latest_payrun(), older_period_created_later)

    def test_suggested_next_period(self):
        # Create an approved payrun for Dec 2025
        PayRun.objects.create(month=12, year=2025, status=PayRunStatusChoices.APPROVED)

        form = PayRunForm()
        self.assertEqual(form.fields['month'].initial, 1)
        self.assertEqual(form.fields['year'].initial, 2026)
        self.assertTrue(form.fields['month'].disabled)

    def test_rejected_payrun_suggests_next_period(self):
        # Create a rejected payrun for Jan 2026
        PayRun.objects.create(month=1, year=2026, status=PayRunStatusChoices.REJECTED)

        form = PayRunForm()
        self.assertEqual(form.fields['month'].initial, 2)
        self.assertEqual(form.fields['year'].initial, 2026)
        self.assertTrue(form.fields['month'].disabled)
        self.assertTrue(form.fields['year'].disabled)


# ---------------------------------------------------------------------------
# validate_zip_file tests
# ---------------------------------------------------------------------------

class ValidateZipFileTest(TestCase):
    """Unit tests for payroll.upload_helpers.validate_zip_file.

    Each test targets a specific security/integrity branch so that a
    regression in any one check is caught immediately.
    """

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_valid_zip_passes(self):
        """A well-formed ZIP with safe paths and reasonable sizes must pass."""
        buf = _make_zip([
            ('report.pdf', b'%PDF-dummy-content'),
            ('data/payslip.csv', b'name,amount\nAlice,1000'),
        ])
        # Should not raise
        validate_zip_file(buf)
        # File pointer must be reset to 0 after validation (for subsequent consumers)
        self.assertEqual(buf.tell(), 0)

    # ------------------------------------------------------------------
    # Non-ZIP / corrupt file
    # ------------------------------------------------------------------

    def test_non_zip_magic_bytes_rejected(self):
        """A file with non-ZIP magic bytes must raise ValidationError."""
        buf = io.BytesIO(b'Not a zip file at all \xff\xfe')
        buf.seek(4)
        with self.assertRaises(ValidationError) as ctx:
            validate_zip_file(buf)
        self.assertIn('not a valid zip', str(ctx.exception).lower())
        self.assertEqual(buf.tell(), 0)

    # ------------------------------------------------------------------
    # Zip-Slip / path traversal
    # ------------------------------------------------------------------

    def test_path_traversal_dotdot_rejected(self):
        """An entry with '../' traversal must raise ValidationError."""
        info = zipfile.ZipInfo('../etc/passwd')
        buf = _make_zip_with_info(info, b'root:x:0:0')
        with self.assertRaises(ValidationError) as ctx:
            validate_zip_file(buf)
        self.assertIn('invalid file path', str(ctx.exception).lower())

    def test_path_traversal_nested_dotdot_rejected(self):
        """A nested traversal like 'safe/../../etc/shadow' must be rejected."""
        info = zipfile.ZipInfo('safe/../../etc/shadow')
        buf = _make_zip_with_info(info, b'shadow-data')
        with self.assertRaises(ValidationError) as ctx:
            validate_zip_file(buf)
        self.assertIn('invalid file path', str(ctx.exception).lower())

    def test_path_traversal_windows_backslash_rejected(self):
        """An entry with Windows-style backslash path must be rejected."""
        info = zipfile.ZipInfo('..\\windows\\system32\\evil.dll')
        buf = _make_zip_with_info(info, b'MZ-dummy')
        with self.assertRaises(ValidationError) as ctx:
            validate_zip_file(buf)
        self.assertIn('invalid file path', str(ctx.exception).lower())

    def test_absolute_path_rejected(self):
        """An entry with an absolute path must be rejected."""
        info = zipfile.ZipInfo('/etc/cron.d/evil')
        buf = _make_zip_with_info(info, b'evil cron job')
        with self.assertRaises(ValidationError) as ctx:
            validate_zip_file(buf)
        self.assertIn('invalid file path', str(ctx.exception).lower())

    # ------------------------------------------------------------------
    # Entry count limit
    # ------------------------------------------------------------------

    def test_too_many_entries_rejected(self):
        """A ZIP with more than 500 entries must be rejected."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            for i in range(501):
                zf.writestr(f'file_{i}.txt', b'x')
        buf.seek(0)
        with self.assertRaises(ValidationError) as ctx:
            validate_zip_file(buf)
        self.assertIn('too many files', str(ctx.exception).lower())

    def test_exactly_500_entries_allowed(self):
        """Exactly 500 entries must pass the entry-count check."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            for i in range(500):
                zf.writestr(f'file_{i}.txt', b'x')
        buf.seek(0)
        # Should not raise
        validate_zip_file(buf)

    # ------------------------------------------------------------------
    # Per-file size limit (10 MB)
    # ------------------------------------------------------------------

    def test_single_file_exceeds_10mb_rejected(self):
        """A single member larger than 10 MB must be rejected."""
        big_data = b'A' * (10 * 1024 * 1024 + 1)  # 10 MB + 1 byte
        info = zipfile.ZipInfo('big_file.bin')
        info.file_size = len(big_data)
        info.compress_size = len(big_data)  # stored, no compression
        buf = _make_zip_with_info(info, big_data, compress_type=zipfile.ZIP_STORED)
        with self.assertRaises(ValidationError) as ctx:
            validate_zip_file(buf)
        self.assertIn('exceeds 10mb', str(ctx.exception).lower())

    # ------------------------------------------------------------------
    # Zip-bomb: compression ratio > 100×
    # ------------------------------------------------------------------

    def test_high_compression_ratio_rejected(self):
        """An entry with compress_size=0 (impossible ratio) must be rejected."""
        # We craft a ZipInfo whose metadata claims file_size >> compress_size.
        # zipfile won't actually store it that way, so we patch the infolist
        # by building the zip then monkey-patching the ZipInfo object that
        # validate_zip_file will read via infolist().
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('normal.txt', b'hello')
        buf.seek(0)

        # Re-open and patch the ZipInfo to simulate a bomb ratio
        with zipfile.ZipFile(buf, 'r') as zf:
            infos = zf.infolist()
        infos[0].file_size = 9 * 1024 * 1024   # claims 9 MB uncompressed (less than 10MB limit)
        infos[0].compress_size = 1                # but only 1 byte compressed

        # Patch ZipFile.infolist so validate_zip_file sees our tampered entry
        import unittest.mock as mock
        buf.seek(0)
        with mock.patch.object(zipfile.ZipFile, 'infolist', return_value=infos):
            with self.assertRaises(ValidationError) as ctx:
                validate_zip_file(buf)
        self.assertIn('zip bomb', str(ctx.exception).lower())

    def test_zero_compress_size_with_nonzero_file_size_rejected(self):
        """compress_size == 0 with file_size > 0 signals a bomb attempt."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('file.txt', b'data')
        buf.seek(0)

        with zipfile.ZipFile(buf, 'r') as zf:
            infos = zf.infolist()
        infos[0].file_size = 1024
        infos[0].compress_size = 0  # impossible in a real file

        import unittest.mock as mock
        buf.seek(0)
        with mock.patch.object(zipfile.ZipFile, 'infolist', return_value=infos):
            with self.assertRaises(ValidationError) as ctx:
                validate_zip_file(buf)
        self.assertIn('zip bomb', str(ctx.exception).lower())

    # ------------------------------------------------------------------
    # Total uncompressed size cap (200 MB)
    # ------------------------------------------------------------------

    def test_total_size_exceeds_200mb_rejected(self):
        """Aggregate uncompressed size over 200 MB must be rejected."""
        # Use patched ZipInfos to avoid actually allocating 200 MB in memory.
        import unittest.mock as mock

        infos = []
        chunk = 10 * 1024 * 1024  # 10 MB each, ratio = 1 (safe per-file)
        for i in range(21):       # 21 × 10 MB = 210 MB total → over limit
            zi = zipfile.ZipInfo(f'chunk_{i}.bin')
            zi.file_size = chunk
            zi.compress_size = chunk
            infos.append(zi)

        buf = _make_zip([('placeholder.txt', b'x')])
        with mock.patch.object(zipfile.ZipFile, 'infolist', return_value=infos):
            with self.assertRaises(ValidationError) as ctx:
                validate_zip_file(buf)
        self.assertIn('200mb', str(ctx.exception).lower())


class ExtractForm16ZipTaskTest(TestCase):
    def test_passes_open_file_directly_to_zipfile(self):
        opened_zip_file = mock.Mock()
        opened_zip_file.read.side_effect = AssertionError("ZIP archive was read fully into memory")

        form16_file = mock.MagicMock()
        form16_file.open.return_value.__enter__.return_value = opened_zip_file

        form16 = mock.Mock()
        form16.form16_zip_file = form16_file
        form16.is_extracted = False

        zip_ref = mock.MagicMock()
        zip_ref.namelist.return_value = []

        with (
            mock.patch('payroll.tasks.Form16.objects.get', return_value=form16),
            mock.patch('payroll.tasks.zipfile.ZipFile') as zip_file_cls,
        ):
            zip_file_cls.return_value.__enter__.return_value = zip_ref
            extract_form16_zip_task(1)

        zip_file_cls.assert_called_once_with(opened_zip_file, 'r')
        opened_zip_file.read.assert_not_called()
        self.assertEqual(
            form16.extraction_summary,
            "No PDF or XML Form 16 files found in the ZIP archive.",
        )
        form16.save.assert_called_once_with(update_fields=['is_extracted', 'extraction_summary'])

    def test_records_invalid_pan_filename_in_extraction_summary(self):
        zip_ref = mock.MagicMock()
        zip_ref.namelist.return_value = ['changed-zoho-name.pdf']
        zip_ref.read.return_value = b'%PDF-form16'

        form16_file = mock.MagicMock()
        form16 = mock.Mock()
        form16.form16_zip_file = form16_file
        form16.is_extracted = False

        with (
            mock.patch('payroll.tasks.Form16.objects.get', return_value=form16),
            mock.patch('payroll.tasks.zipfile.ZipFile') as zip_file_cls,
            mock.patch('payroll.tasks.default_storage.exists', return_value=False),
        ):
            zip_file_cls.return_value.__enter__.return_value = zip_ref
            extract_form16_zip_task(1)

        self.assertIn("Extracted 0 file(s).", form16.extraction_summary)
        self.assertIn(
            "- changed-zoho-name.pdf: could not derive a valid PAN from filename",
            form16.extraction_summary,
        )
        form16.save.assert_called_once_with(update_fields=['is_extracted', 'extraction_summary'])
