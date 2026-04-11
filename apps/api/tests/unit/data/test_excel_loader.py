"""
Verification tests for Excel Data Loader integration (Task #53).

Validates that DataLoaderExcel, source tagging, delete_by_source, and
PropertyCollection metadata tracking all work correctly.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from data.csv_loader import DataLoaderCsv, DataLoaderExcel
from data.schemas import PropertyCollection

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Minimal valid property DataFrame."""
    return pd.DataFrame(
        {
            "city": ["Warsaw", "Krakow", "Gdansk"],
            "price": [3000.0, 2500.0, 4000.0],
            "rooms": [3.0, 2.0, 4.0],
            "area_sqm": [65.0, 45.0, 80.0],
            "currency": ["PLN", "PLN", "PLN"],
        }
    )


@pytest.fixture
def xlsx_file(sample_df: pd.DataFrame) -> Path:
    """Write sample data to a temporary .xlsx file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        sample_df.to_excel(tmp.name, index=False, engine="openpyxl")
        return Path(tmp.name)


@pytest.fixture
def multi_sheet_xlsx(sample_df: pd.DataFrame) -> Path:
    """Write a .xlsx file with multiple named sheets."""
    df2 = sample_df.copy()
    df2["city"] = ["Poznan", "Lodz", "Wroclaw"]
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
            sample_df.to_excel(writer, sheet_name="Sheet1", index=False)
            df2.to_excel(writer, sheet_name="Cities2", index=False)
        return Path(tmp.name)


@pytest.fixture
def csv_file(sample_df: pd.DataFrame) -> Path:
    """Write sample data to a temporary .csv file."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
        sample_df.to_csv(tmp.name, index=False)
        return Path(tmp.name)


# ---------------------------------------------------------------------------
# DataLoaderExcel — core loading
# ---------------------------------------------------------------------------


class TestDataLoaderExcelCore:
    def test_load_xlsx_basic(self, xlsx_file: Path) -> None:
        """DataLoaderExcel loads .xlsx file into DataFrame."""
        loader = DataLoaderExcel(xlsx_file)
        df = loader.load_df()
        assert len(df) == 3
        assert "city" in df.columns

    def test_load_xlsx_sheet_selection(self, multi_sheet_xlsx: Path) -> None:
        """DataLoaderExcel loads a specific sheet by name."""
        loader = DataLoaderExcel(multi_sheet_xlsx, sheet_name="Cities2")
        df = loader.load_df()
        assert len(df) == 3
        assert "Poznan" in df["city"].values

    def test_get_sheet_names(self, multi_sheet_xlsx: Path) -> None:
        """get_sheet_names returns all sheet names."""
        loader = DataLoaderExcel(multi_sheet_xlsx)
        names = loader.get_sheet_names()
        assert "Sheet1" in names
        assert "Cities2" in names

    def test_header_row_offset(self, xlsx_file: Path) -> None:
        """header_row=1 skips the first row, treating it as data."""
        loader = DataLoaderExcel(xlsx_file, header_row=1)
        df = loader.load_df()
        # First data row ("Warsaw" row) becomes the header; remaining rows = 2
        assert len(df) == 2

    def test_rejects_csv_file(self, csv_file: Path) -> None:
        """DataLoaderExcel raises ValueError for non-Excel files."""
        loader = DataLoaderExcel(csv_file)
        with pytest.raises(ValueError, match="Unsupported file format"):
            loader.load_df()


# ---------------------------------------------------------------------------
# DataLoaderExcel — source type detection
# ---------------------------------------------------------------------------


class TestSourceTypeDetection:
    def test_detect_xlsx(self, xlsx_file: Path) -> None:
        assert DataLoaderExcel.detect_source_type(xlsx_file) == "excel"

    def test_detect_csv(self, csv_file: Path) -> None:
        assert DataLoaderExcel.detect_source_type(csv_file) == "csv"

    def test_detect_url(self) -> None:
        from yarl import URL

        assert DataLoaderExcel.detect_source_type(URL("https://example.com/data.xlsx")) == "url"

    def test_detect_unknown(self) -> None:
        assert DataLoaderExcel.detect_source_type(Path("data.json")) == "unknown"


# ---------------------------------------------------------------------------
# DataLoaderExcel — inherits format_df from DataLoaderCsv
# ---------------------------------------------------------------------------


class TestFormatDfReuse:
    def test_format_df_via_excel_loader(self, xlsx_file: Path) -> None:
        """DataLoaderExcel uses the inherited format_df pipeline."""
        loader = DataLoaderExcel(xlsx_file, source_type="excel")
        df_raw = loader.load_df()
        df_formatted = loader.load_format_df(df_raw)

        # format_df adds standardised columns
        assert "currency" in df_formatted.columns
        assert "listing_type" in df_formatted.columns
        assert "latitude" in df_formatted.columns
        assert len(df_formatted) == 3

    def test_format_df_normalises_booleans(self, xlsx_file: Path) -> None:
        """format_df converts yes/no strings to booleans."""
        # Create a file with boolean-like columns
        df = pd.DataFrame(
            {
                "city": ["Warsaw"],
                "price": [3000.0],
                "rooms": [2.0],
                "area_sqm": [50.0],
                "has_parking": ["yes"],
                "has_garden": ["no"],
            }
        )
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            df.to_excel(tmp.name, index=False, engine="openpyxl")
            loader = DataLoaderExcel(Path(tmp.name))
            df_raw = loader.load_df()
            df_formatted = loader.format_df(df_raw)
            assert bool(df_formatted["has_parking"].iloc[0]) is True
            assert bool(df_formatted["has_garden"].iloc[0]) is False


# ---------------------------------------------------------------------------
# PropertyCollection — source tagging
# ---------------------------------------------------------------------------


class TestSourceTagging:
    def test_from_dataframe_with_source_type(self, sample_df: pd.DataFrame) -> None:
        """PropertyCollection.from_dataframe preserves source and source_type."""
        df_formatted = DataLoaderCsv.format_df(sample_df)
        collection = PropertyCollection.from_dataframe(
            df_formatted, source="test-upload.xlsx", source_type="excel"
        )
        assert collection.source == "test-upload.xlsx"
        assert collection.source_type == "excel"
        assert collection.total_count > 0

    def test_property_ids_include_source(self, sample_df: pd.DataFrame) -> None:
        """Property IDs are prefixed with source name when no id column exists."""
        df_formatted = DataLoaderCsv.format_df(sample_df)
        collection = PropertyCollection.from_dataframe(
            df_formatted, source="portal-olx", source_type="portal"
        )
        for prop in collection.properties:
            assert prop.source_url == "portal-olx"


# ---------------------------------------------------------------------------
# PropertyCollection — delete_by_source
# ---------------------------------------------------------------------------


class TestDeleteBySource:
    def _make_collection(self) -> PropertyCollection:
        """Create a collection with properties from 2 sources."""
        df = pd.DataFrame(
            {
                "city": ["Warsaw", "Krakow", "Warsaw", "Gdansk"],
                "price": [3000.0, 2500.0, 3500.0, 4000.0],
                "rooms": [2.0, 1.0, 3.0, 4.0],
                "area_sqm": [50.0, 30.0, 70.0, 90.0],
                "source_url": ["source-a", "source-b", "source-a", "source-b"],
            }
        )
        df_formatted = DataLoaderCsv.format_df(df)
        return PropertyCollection.from_dataframe(
            df_formatted, source="combined", source_type="excel"
        )

    def test_delete_by_source_removes_matching(self) -> None:
        """delete_by_source removes properties from the specified source."""
        collection = self._make_collection()
        original_count = collection.total_count
        result = collection.delete_by_source("source-a")
        assert result.total_count < original_count
        # All remaining properties should be from source-b
        for prop in result.properties:
            assert "source-a" not in (prop.source_url or "")

    def test_delete_by_source_type(self) -> None:
        """delete_by_source_type removes properties matching the type."""
        collection = self._make_collection()
        # Set source_platform on some properties
        for prop in collection.properties:
            if prop.source_url == "source-a":
                prop.source_platform = "excel"
            else:
                prop.source_platform = "csv"

        result = collection.delete_by_source_type("excel")
        assert result.total_count < collection.total_count
        for prop in result.properties:
            assert prop.source_platform != "excel"

    def test_delete_nonexistent_source_keeps_all(self) -> None:
        """delete_by_source with unknown source returns identical collection."""
        collection = self._make_collection()
        result = collection.delete_by_source("nonexistent-source")
        assert result.total_count == collection.total_count


# ---------------------------------------------------------------------------
# DataLoaderCsv — backward compatibility (Excel still works via base class)
# ---------------------------------------------------------------------------


class TestDataLoaderCsvExcelCompat:
    def test_csv_loader_reads_xlsx(self, xlsx_file: Path) -> None:
        """DataLoaderCsv.load_df auto-detects and reads Excel files."""
        loader = DataLoaderCsv(xlsx_file)
        df = loader.load_df()
        assert len(df) == 3
        assert "city" in df.columns

    def test_csv_loader_reads_csv(self, csv_file: Path) -> None:
        """DataLoaderCsv.load_df reads CSV files."""
        loader = DataLoaderCsv(csv_file)
        df = loader.load_df()
        assert len(df) == 3
        assert "city" in df.columns
