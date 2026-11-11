import base64
import numpy as np
import pytest
import ujson
import xarray as xr
from hypothesis import given, settings, strategies as st
from obspec_utils.registry import ObjectStoreRegistry
from obstore.store import LocalStore
from virtualizarr.parsers import KerchunkJSONParser, KerchunkParquetParser
from virtualizarr.parsers.kerchunk.translator import manifest_from_kerchunk_chunk_dict
from virtualizarr.xarray import open_virtual_dataset
pytest.importorskip('kerchunk')

def _registry():
    return ObjectStoreRegistry({'file://': LocalStore()})

def _data_of(manifest, key='0'):
    return manifest.dict()[key]['data']

def _inlined_ref(tmp_path):
    from kerchunk.hdf import SingleHdf5ToZarr
    nc = tmp_path / 'f.nc'
    ds = xr.Dataset({'a': (('x',), np.arange(5, dtype='float32'))}, coords={'x': np.arange(5)})
    ds.to_netcdf(nc, engine='h5netcdf')
    return SingleHdf5ToZarr(str(nc), inline_threshold=1000).translate()

def _inlined_chunk_values(ref):
    out = {}
    for k, v in ref['refs'].items():
        if isinstance(v, str) and (not k.split('/')[-1].startswith('.')):
            out[k] = v
    return out

def _decode(v):
    if v.startswith('base64:'):
        return base64.b64decode(v[len('base64:'):])
    return v.encode('utf-8')