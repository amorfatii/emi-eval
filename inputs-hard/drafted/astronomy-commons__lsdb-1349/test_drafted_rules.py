import inspect
from pathlib import Path
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
import lsdb
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'tests' / 'data'
SMALL_SKY = DATA / 'small_sky'
COLLECTION = DATA / 'small_sky_order1_source_collection'

def _parquet_files(base: Path):
    return sorted((p for p in (base / 'dataset').rglob('*.parquet') if p.is_file()))

def _filename_param():
    params = inspect.signature(lsdb.catalog.Catalog.write_catalog).parameters
    for name in params:
        if name not in ('catalog_name', 'default_columns') and ('file' in name or 'name' in name):
            return name
    return None