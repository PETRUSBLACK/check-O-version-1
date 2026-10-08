"""
How static files are served in production.

WhiteNoise's manifest storage renames every static file to include a hash of its
contents — style.a1b2c3.css — so browsers can cache them forever and still pick
up a change the moment one is deployed. That part is worth having.

What is not worth having is its strictness. If any template asks for a static
path that was not collected, manifest storage raises ValueError and the whole
page becomes a 500. Django Jazzmin's admin templates do exactly that: they
reference 'vendor/bootswatch', which is a directory rather than a file, so it
never lands in the manifest.

The symptom was horrible to read. The admin login page rendered fine, because it
does not touch that path, and then logging in succeeded and redirected to the
admin index — which does — so the error looked like a failed login or a broken
database connection. It was neither.

manifest_strict = False keeps the hashing and falls back to the plain, unhashed
path for anything missing. A stale cache on one asset is a far better outcome
than an unreachable admin.
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Hashed, compressed static files that do not take the site down."""

    manifest_strict = False
