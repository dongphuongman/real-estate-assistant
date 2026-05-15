"""
Excel data loader for property data ingestion.

Supports .xlsx files (via openpyxl), with optional .xls (xlrd) and
.ods (odfpy) support when those extras are installed.

Provides:
- Sheet detection and selection (by name or index)
- Configurable header row
- Reuse of format_df normalization from csv_loader
- PropertyCollection integration for validated output
"""

import logging
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse

import pandas as pd

from data.csv_loader import DataLoaderCsv
from data.schemas import PropertyCollection

logger = logging.getLogger(__name__)

# Supported Excel extensions
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".ods"}


def _is_url(path: Path | str) -> bool:
    """Check if path is a URL."""
    s = str(path)
    return s.startswith(("http://", "https://"))


def _get_suffix(path: Path | str) -> str:
    """Extract suffix from path or URL."""
    s = str(path)
    parsed = urlparse(s)
    p = parsed.path if parsed.scheme and parsed.netloc else s
    return Path(p).suffix.lower()


class ExcelDataLoader:
    """
    Standalone Excel data loader with sheet selection and normalization.

    This loader reads Excel files (.xlsx, .xls, .ods), applies the shared
    ``format_df`` normalization pipeline from ``DataLoaderCsv``, and
    optionally converts the result into a validated ``PropertyCollection``.

    Supports both local file paths and URLs (http/https).

    Usage::

        loader = ExcelDataLoader("properties.xlsx", sheet_name="Listings")
        df = loader.load()                       # raw DataFrame
        df_norm = loader.load_normalized()       # normalized DataFrame
        collection = loader.load_collection()     # PropertyCollection

    Args:
        file_path: Path to the Excel file, or URL (http/https).
        sheet_name: Sheet name to load. None loads the first sheet.
        sheet_index: Sheet index (0-based) as alternative to name.
            Ignored when ``sheet_name`` is provided.
        header_row: Row number to use as header (0-indexed, default 0).
        max_rows: Optional cap on number of rows to return.
    """

    def __init__(
        self,
        file_path: Path | str,
        sheet_name: Optional[str] = None,
        sheet_index: Optional[int] = None,
        header_row: int = 0,
        max_rows: Optional[int] = None,
    ) -> None:
        self._raw_path = file_path
        self.file_path = (
            Path(file_path) if isinstance(file_path, str) and not _is_url(file_path) else file_path
        )
        self.sheet_name = sheet_name
        self.sheet_index = sheet_index
        self.header_row = header_row
        self.max_rows = max_rows

        # Validate file exists (only for local paths, not URLs)
        if not _is_url(file_path):
            p = Path(file_path)
            if p.exists() and not p.is_file():
                raise ValueError(f"Not a file: {p}")
            if not p.exists():
                logger.warning("Excel file not found: %s", p)

        # Validate extension
        suffix = _get_suffix(file_path)
        if suffix and suffix not in EXCEL_EXTENSIONS:
            raise ValueError(
                f"Unsupported format '{suffix}'. Supported: {', '.join(sorted(EXCEL_EXTENSIONS))}"
            )

    # ------------------------------------------------------------------
    # Sheet discovery
    # ------------------------------------------------------------------

    def get_sheet_names(self) -> List[str]:
        """
        Return sheet names in the workbook.

        Returns an empty list when the local file does not exist.
        For URLs, delegates to pandas which handles remote reads.
        """
        file_str = str(self._raw_path)
        suffix = _get_suffix(file_str)

        # For local paths, check existence
        if not _is_url(file_str):
            p = Path(file_str)
            if not p.exists():
                logger.warning("Excel file not found: %s", p)
                return []

        try:
            if suffix == ".xlsx":
                import openpyxl

                wb = openpyxl.load_workbook(file_str, read_only=True, data_only=True)
                names = list(wb.sheetnames)
                wb.close()
                return names

            if suffix == ".xls":
                import xlrd  # optional

                workbook = xlrd.open_workbook(file_str)
                return list(workbook.sheet_names())

            if suffix == ".ods":
                try:
                    from odf.opendocument import load

                    doc = load(file_str)
                    return list(doc.spreadsheets.keys())
                except ImportError:
                    xf = pd.ExcelFile(file_str, engine="odf")
                    names = list(xf.sheet_names)
                    xf.close()
                    return names

            # Fallback: let pandas detect the engine
            xf = pd.ExcelFile(file_str)
            names = list(xf.sheet_names)
            xf.close()
            return names

        except ImportError as exc:
            raise ImportError(
                "Excel file reading requires optional dependencies. "
                "For .xlsx: openpyxl. For .xls: xlrd. For .ods: odfpy."
            ) from exc
        except Exception as exc:
            logger.error("Failed to read sheet names from %s: %s", file_str, exc)
            raise

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _resolve_sheet(self) -> Optional[str]:
        """Return the pandas sheet_name argument."""
        if self.sheet_name:
            return self.sheet_name
        if self.sheet_index is not None:
            return self.sheet_index
        return None  # first sheet

    def _read_kwargs(self) -> dict[str, Any]:
        """Build keyword arguments for ``pd.read_excel``."""
        suffix = _get_suffix(self._raw_path)
        kwargs: dict[str, Any] = {}

        sheet = self._resolve_sheet()
        if sheet is not None:
            kwargs["sheet_name"] = sheet

        kwargs["header"] = self.header_row

        # Engine selection
        if suffix == ".xlsx":
            kwargs["engine"] = "openpyxl"
        elif suffix == ".xls":
            try:
                import importlib.util

                if importlib.util.find_spec("xlrd"):
                    kwargs["engine"] = "xlrd"
            except Exception:
                pass
        elif suffix == ".ods":
            try:
                import importlib.util

                if importlib.util.find_spec("odf"):
                    kwargs["engine"] = "odf"
            except Exception:
                pass

        return kwargs

    def load(self) -> pd.DataFrame:
        """
        Load the Excel file into a raw DataFrame.

        Returns:
            DataFrame with the raw contents of the selected sheet.

        Raises:
            ValueError: If the file is not a supported Excel format.
            ImportError: If the required engine library is not installed.
        """
        file_str = str(self._raw_path)
        suffix = _get_suffix(file_str)
        if suffix not in EXCEL_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: {suffix}. "
                f"Excel loader supports: {', '.join(sorted(EXCEL_EXTENSIONS))}"
            )

        kwargs = self._read_kwargs()
        df = pd.read_excel(file_str, **kwargs)

        logger.info(
            "Excel loaded from %s (sheet=%s, header_row=%d, rows=%d)",
            file_str,
            self._resolve_sheet() or "default",
            self.header_row,
            len(df),
        )
        return df

    def load_normalized(self) -> pd.DataFrame:
        """
        Load and normalize the Excel data using ``format_df``.

        Applies the shared normalization pipeline from ``DataLoaderCsv``
        (column renaming, type coercion, missing-value filling, etc.).
        """
        df = self.load()
        df_norm = DataLoaderCsv.format_df(df, rows_count=self.max_rows)
        logger.info("Normalized %d rows from %s", len(df_norm), self.file_path)
        return df_norm

    def load_collection(
        self,
        source: Optional[str] = None,
    ) -> PropertyCollection:
        """
        Load, normalize, and validate into a ``PropertyCollection``.

        Args:
            source: Optional source identifier attached to each property.

        Returns:
            ``PropertyCollection`` with validated ``Property`` objects.
        """
        df_norm = self.load_normalized()
        collection = PropertyCollection.from_dataframe(
            df_norm,
            source=source or str(self.file_path),
            source_type="excel",
        )
        logger.info(
            "Created PropertyCollection with %d properties from %s",
            collection.total_count,
            self.file_path,
        )
        return collection
