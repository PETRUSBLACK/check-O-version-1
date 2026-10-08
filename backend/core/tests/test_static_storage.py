"""
The static files setting that took the admin down.

Switching production to WhiteNoise's manifest storage turned on its strictness:
any template asking for a static path that was not collected raises ValueError,
and the page becomes a 500. Jazzmin's admin templates reference
'vendor/bootswatch', a directory, which is never in the manifest.

What made it expensive was how it presented. The admin login page does not touch
that path, so it rendered perfectly. Logging in then succeeded and redirected to
the admin index, which does touch it — so the 500 looked like a rejected login
or a broken database, and an afternoon went into checking database credentials
that were fine all along.

These tests are cheap and exist so nobody "tidies" the storage class back to the
strict one without understanding what it costs.
"""

from django.test import SimpleTestCase

from core.storage import ForgivingManifestStaticFilesStorage


class StaticStorageTest(SimpleTestCase):
    def test_the_production_static_storage_does_not_raise_on_a_missing_entry(self):
        """
        manifest_strict = False is the whole point of the subclass. With it True,
        every admin page after login is a 500.
        """
        self.assertIs(ForgivingManifestStaticFilesStorage.manifest_strict, False)

    def test_it_still_hashes_and_compresses(self):
        """
        Forgiving, not toothless: hashed filenames are what let browsers cache
        static files forever and still pick up a change on deploy.
        """
        from whitenoise.storage import CompressedManifestStaticFilesStorage

        self.assertTrue(
            issubclass(
                ForgivingManifestStaticFilesStorage,
                CompressedManifestStaticFilesStorage,
            )
        )

    def test_production_settings_use_it(self):
        """
        Reading the setting out of prod.py directly: importing the module needs
        SECRET_KEY and friends, so parse the one line instead.
        """
        from pathlib import Path

        prod = Path(__file__).resolve().parent.parent.parent / "config" / "settings" / "prod.py"
        text = prod.read_text(encoding="utf-8")
        self.assertIn("core.storage.ForgivingManifestStaticFilesStorage", text)
        self.assertNotIn(
            '"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}',
            text,
            "the strict class is what broke the admin — see this module's docstring",
        )
