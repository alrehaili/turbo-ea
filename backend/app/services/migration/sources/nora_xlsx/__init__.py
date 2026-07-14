"""NORA/DGA data-collection template source adapter ([FORK] — WP6.6)."""

from app.services.migration.registry import register_source
from app.services.migration.sources.nora_xlsx.adapter import NoraXlsxSource

register_source(NoraXlsxSource())
