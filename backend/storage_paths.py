"""
storage_paths.py
================
Single source of truth for all on-disk paths.
Every path is scoped under  <root>/<user_id>/<file_id>/
so each user's data is structurally isolated.

Usage:
    from storage_paths import paths

    p = paths(user_id, file_id)
    p.pdf          # pdf_store/<user_id>/<file_id>/original.pdf
    p.embeddings   # embeddings_store/<user_id>/<file_id>/embeddings.pkl
    p.images_dir   # images/<user_id>/<file_id>/
    p.page_image(3)# images/<user_id>/<file_id>/page_3.png
"""

import os
from dataclasses import dataclass


# ── configurable roots (override via env vars if needed) ─────────────────────
PDF_ROOT        = os.getenv("PDF_ROOT",        "pdf_store")
EMBEDDINGS_ROOT = os.getenv("EMBEDDINGS_ROOT", "embeddings_store")
IMAGES_ROOT     = os.getenv("IMAGES_ROOT",     "images")


@dataclass(frozen=True)
class FilePaths:
    user_id: str
    file_id: str

    # ── directory helpers ─────────────────────────────────────────────────────
    @property
    def pdf_dir(self) -> str:
        return os.path.join(PDF_ROOT, self.user_id, self.file_id)

    @property
    def embeddings_dir(self) -> str:
        return os.path.join(EMBEDDINGS_ROOT, self.user_id, self.file_id)

    @property
    def images_dir(self) -> str:
        return os.path.join(IMAGES_ROOT, self.user_id, self.file_id)

    # ── file paths ────────────────────────────────────────────────────────────
    @property
    def pdf(self) -> str:
        return os.path.join(self.pdf_dir, "original.pdf")

    @property
    def embeddings(self) -> str:
        return os.path.join(self.embeddings_dir, "embeddings.pkl")

    def page_image(self, page_number: int) -> str:
        return os.path.join(self.images_dir, f"page_{page_number}.png")

    # ── URL paths (served by FastAPI StaticFiles) ─────────────────────────────
    def page_image_url(self, page_number: int) -> str:
        """
        Returns the URL path for a page image, relative to the static mount.
        e.g. /images/<user_id>/<file_id>/page_3.png
        """
        return f"/images/{self.user_id}/{self.file_id}/page_{page_number}.png"

    # ── fs helpers ────────────────────────────────────────────────────────────
    def makedirs(self):
        """Create all directories needed for this file. Call once on upload."""
        os.makedirs(self.pdf_dir,        exist_ok=True)
        os.makedirs(self.embeddings_dir, exist_ok=True)
        os.makedirs(self.images_dir,     exist_ok=True)

    def delete_all(self):
        """Remove every file (and dirs if empty) associated with this file_id."""
        import shutil
        for directory in (self.pdf_dir, self.embeddings_dir, self.images_dir):
            if os.path.exists(directory):
                shutil.rmtree(directory)


def paths(user_id: str, file_id: str) -> FilePaths:
    """Convenience factory — import this and call paths(uid, fid)."""
    return FilePaths(user_id=user_id, file_id=file_id)