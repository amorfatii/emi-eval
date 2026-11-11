import pytest
from multiprocessing import get_context
from unittest.mock import Mock, patch
import agate
from hypothesis import given, settings, strategies as st
from dbt.adapters.databricks.impl import DatabricksAdapter
TEXT_COLUMNS = ['table_database', 'table_schema', 'table_name', 'table_type', 'table_comment', 'table_owner', 'column_name', 'column_type', 'column_comment']

def _row(name='c', comment='x', index=0):
    return {'table_database': 'db', 'table_schema': 'sch', 'table_name': 'tbl', 'table_type': 'table', 'table_comment': comment, 'table_owner': 'root', 'column_name': name, 'column_index': index, 'column_type': 'string', 'column_comment': comment}

def _schema_table(rows):
    with patch('dbt.adapters.databricks.api_client.DatabricksApiClient'):
        with patch.object(DatabricksAdapter, '_list_relations_with_information') as li:
            li.return_value = [(Mock(), 'info')]
            with patch.object(DatabricksAdapter, '_get_columns_for_catalog') as gc:
                gc.return_value = rows
                adapter = DatabricksAdapter(Mock(flags={}), get_context('spawn'))
                return adapter._get_schema_for_catalog('database', 'schema', 'name')

def _assert_text(table):
    for name in TEXT_COLUMNS:
        if name in table.column_names:
            assert isinstance(table.columns[name].data_type, agate.Text)

def test_empty_schema_result_has_zero_rows():
    """A schema that returns no columns yields a table with zero rows."""
    assert len(_schema_table([]).rows) == 0

def test_empty_result_merges_with_populated_result():
    """Merging an empty schema result with a populated one does not raise a type conflict."""
    empty = _schema_table([])
    populated = _schema_table([_row()])
    merged = agate.Table.merge([populated, empty])
    assert len(merged.rows) == 1
    merged = agate.Table.merge([empty, populated])
    assert len(merged.rows) == 1

def test_empty_result_string_metadata_columns_are_text():
    """In an empty result, any string metadata column that is present is typed Text."""
    _assert_text(_schema_table([]))

def test_populated_result_string_metadata_columns_are_text():
    """In a populated result, the string metadata columns are typed Text."""
    table = _schema_table([_row()])
    assert 'column_name' in table.column_names
    _assert_text(table)

def test_numeric_looking_strings_in_text_columns_stay_text():
    """Metadata columns holding numeric-looking strings keep their text values."""
    table = _schema_table([_row(name='123')])
    _assert_text(table)
    assert table.rows[0]['column_name'] == '123'