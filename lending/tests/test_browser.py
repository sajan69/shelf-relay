from datetime import timedelta
from pathlib import Path

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag
from django.utils import timezone
from playwright.sync_api import expect, sync_playwright

from .helpers import item, staff


@tag("browser")
@override_settings(DEBUG=True, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class BrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.actor = staff()
        self.item = item(self.actor)
        self.engine = sync_playwright().start()
        self.addCleanup(self.engine.stop)
        self.browser = self.engine.chromium.launch()
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page()
        self.page.goto(self.live_server_url)
        expect(self.page.get_by_role("heading", name="Welcome to ShelfRelay.")).to_be_visible()
        self.page.get_by_label("Username", exact=False).fill("manager")
        self.page.get_by_label("Password", exact=False).fill("test-only-long-password")
        self.page.get_by_role("button", name="Sign in", exact=True).click()
        expect(
            self.page.get_by_role("heading", name="Ready for the next handover.")
        ).to_be_visible()

    def test_reserve_handover_incomplete_return_and_resolve(self):
        page = self.page
        page.get_by_role("heading", name="Camera kit", exact=True).get_by_role(
            "link"
        ).click()
        page.get_by_role("link", name="Reserve this item").click()
        page.get_by_label("Borrower display name", exact=False).fill("Demo · Sam")
        now = timezone.localtime(timezone.now())
        page.get_by_label("Start", exact=False).fill(
            (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M")
        )
        page.get_by_label("Due back", exact=False).fill(
            (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        )
        page.get_by_role("button", name="Save reservation").click()
        expect(page.get_by_role("status")).to_contain_text("Reservation saved")
        page.get_by_role("button", name="Record handover").click()
        page.get_by_role("link", name="Receive return").click()
        page.get_by_label("Body", exact=True).check()
        page.get_by_role("button", name="Record return", exact=True).click()
        expect(page.get_by_text("Missing at return: Cable")).to_be_visible()
        expect(page.get_by_role("link", name="Reserve this item")).to_have_count(0)
        page.get_by_label("What was recovered or resolved?").fill(
            "Cable recovered from case"
        )
        page.get_by_role("button", name="Resolve attention flag").click()
        expect(page.get_by_role("link", name="Reserve this item")).to_be_visible()
        expect(page.get_by_text("Missing at return: Cable")).to_be_visible()
        Path("artifacts").mkdir(exist_ok=True)
        page.screenshot(path="artifacts/handover.png", full_page=True)

    def test_mobile_search_no_overflow_or_external_network(self):
        page = self.page
        external = []
        page.on(
            "request",
            lambda request: (
                external.append(request.url)
                if not request.url.startswith(self.live_server_url)
                else None
            ),
        )
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_label("Find equipment").fill("Camera")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(
            page.get_by_role("heading", name="Camera kit", exact=True)
        ).to_be_visible()
        self.assertTrue(
            page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        )
        self.assertEqual(external, [])
        Path("artifacts").mkdir(exist_ok=True)
        page.screenshot(path="artifacts/mobile.png", full_page=True)
