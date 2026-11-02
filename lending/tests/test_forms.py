from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from lending.forms import ReserveForm, ReturnForm, clean_components
from lending.views import csv_label


class FormTests(SimpleTestCase):
    def test_components_reject_duplicates_empty_and_large_lists(self):
        for raw in ["", "Body\nBody", "x" * 61, "\n".join(str(i) for i in range(21))]:
            with self.assertRaises(ValidationError):
                clean_components(raw)
        self.assertEqual(clean_components("Body\n Cable \n"), ["Body", "Cable"])

    def test_positive_bounded_window_and_required_borrower(self):
        now = timezone.now()
        for start, end in [
            (now, now),
            (now, now - timedelta(hours=1)),
            (now, now + timedelta(days=31)),
            (now - timedelta(days=1), now),
        ]:
            self.assertFalse(
                ReserveForm({"borrower": "Demo", "start": start, "end": end}).is_valid()
            )
        self.assertTrue(
            ReserveForm(
                {"borrower": "Demo", "start": now, "end": now + timedelta(hours=1)}
            ).is_valid()
        )

    @override_settings(TIME_ZONE="Australia/Sydney")
    def test_dst_ambiguous_and_nonexistent_are_rejected(self):
        with timezone.override("Australia/Sydney"):
            for date in ["2026-10-04T02:30", "2026-04-05T02:30"]:
                form = ReserveForm(
                    {"borrower": "Demo", "start": date, "end": "2026-10-04T04:00"}
                )
                self.assertFalse(form.is_valid())
                self.assertIn("start", form.errors)

    def test_checklist_unknown_choices_not_silently_ignored(self):
        self.assertFalse(ReturnForm(["Body"], {"returned": ["8"]}).is_valid())
        self.assertTrue(ReturnForm(["Body"], {"returned": []}).is_valid())

    def test_csv_formula_labels_include_fullwidth_and_leading_space(self):
        for value in ["=SUM(1)", "  +123", "＠cmd", "-x"]:
            self.assertTrue(csv_label(value).startswith("'"))
        self.assertEqual(csv_label("Camera"), "Camera")
