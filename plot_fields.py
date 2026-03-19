#!/usr/bin/env python
# coding: utf-8

# Na Egeon, rodar como: ref_ds = get_field(ds_exps[ref_name], var, cycle, lead)
# Na máquina local, executar: ssh -N -f -L localhost:5006:localhost:5006 usuario@egeon.cptec.inpe.br
# Na máquina local, acessar: http://localhost:5006

import xarray as xr
import hvplot.xarray
import geoviews as gv
import cartopy.crs as ccrs
import holoviews as hv
import pandas as pd
import panel as pn

from functools import lru_cache
from holoviews.operation.datashader import rasterize
from collections import OrderedDict
from dask.distributed import Client, get_client

client = Client(
    processes=False,
    threads_per_worker=4,
    n_workers=1,
    memory_limit='32GB'  
)

pn.extension()
gv.extension('bokeh')

print(client.dashboard_link)

class DaskLRUCache:
    def __init__(self, maxsize=16):
        self.cache = OrderedDict()
        self.maxsize = maxsize

    def _make_key(self, exp_name, var, cycle, lead, level_value):
        return (exp_name, var, pd.Timestamp(cycle), int(lead), None if level_value is None else float(level_value))

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)

        if len(self.cache) > self.maxsize:
            old_key, old_val = self.cache.popitem(last=False)
            self._evict(old_key, old_val)

    def _evict(self, key, value):
        try:
            client = get_client()
            client.cancel(value)  
            print(f"Evicted {key} from cache and Dask")
        except Exception as e:
            print(f"Eviction warning: {e}")

    def clear(self):
        print("Clearing cache...")
        for key, val in self.cache.items():
            self._evict(key, val)
        self.cache.clear()

    def info(self):
        return {
            "size": len(self.cache),
            "keys": list(self.cache.keys())
        }

cache = DaskLRUCache(maxsize=32)

def add_time_coord(ds, start='2025-09-01 06:00', freq='6h'):
    n = ds.sizes['cycle']
    
    time = pd.date_range(start=start, periods=n, freq=freq)
    
    return ds.assign_coords(cycle=time)

ds_exps = {
    'EXP1': add_time_coord(xr.open_zarr('/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr/EXP1.zarr')),
    'EXP2': add_time_coord(xr.open_zarr('/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr/EXP2.zarr')),
    'EXP3': add_time_coord(xr.open_zarr('/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr/EXP3.zarr')),
    'EXP4': add_time_coord(xr.open_zarr('/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr/EXP4.zarr')),
    'EXP5': add_time_coord(xr.open_zarr('/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr/EXP5.zarr')),
    'EXP6': add_time_coord(xr.open_zarr('/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr/EXP6.zarr')),
    'EXP7': add_time_coord(xr.open_zarr('/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr/EXP7.zarr')),
}

VARS = ['pslc', 'psnm', 'uvel', 
        'vvel', 'temp', 'umes', 
        'zgeo', 'agpl', 'tp2m', 
        'u10m', 'v10m', 'q02m']

crs = ccrs.PlateCarree()

def format_level_value(value, dim_name):
    # detecta se a dimensão inoformada é pressão
    if 'lev' in dim_name.lower() or 'plev' in dim_name.lower():
        return f"{value/100:.0f}"  # converte de Pa para hPa
    return str(value)

def fix_latlon(ds):
    # converte as longitudes de 0 a 360 para -180 a 180
    if float(ds.lon.max()) > 180:
        ds = ds.assign_coords(lon=((ds.lon + 180) % 360) - 180)
        ds = ds.sortby('lon')
    # força as latitudes de forma crescente (-90 a 90)
    if float(ds.lat[0]) > float(ds.lat[-1]):
        ds = ds.sortby('lat')
    return ds

def get_field_cached(exp_name, var, cycle, lead, level_value=None):
    key = cache._make_key(exp_name, var, cycle, lead, level_value)

    cached = cache.get(key)
    if cached is not None:
        return cached

    ds = ds_exps[exp_name]

    if cycle not in ds.cycle.values:
        return None

    da = ds[var].sel(cycle=cycle, lead=lead)
    da = da.assign_coords(lat=ds.lat[::-1])

    vert_dim = get_vertical_dim(da)

    if vert_dim is not None and level_value is not None:
        da = da.sel({vert_dim: level_value})

    for dim in list(da.dims):
        if dim not in ['lat', 'lon']:
            if dim == vert_dim:
                continue
            da = da.isel({dim: 0})

    da = fix_latlon(da)

    da = da.persist()

    cache.set(key, da)

    return da

def make_plot(ds, title, clim=None):
    p = ds.hvplot.quadmesh(
        x='lon',
        y='lat',
        cmap='jet',
        geo=True,
        projection=crs,
        project=True,
        colorbar=True,
        rasterize=True
    )

    if clim is not None:
        p = p.opts(clim=clim)

    return (p * gv.feature.coastline).opts(title=title)

def get_vertical_dim(da):
    for dim in da.dims:
        if dim not in ['lat', 'lon', 'cycle', 'lead']:
            return dim
    return None

level = pn.widgets.Select(name='Nível vertical (hPa)', options=[], disabled=True) 

var_select = pn.widgets.Select(name='Variável', options=VARS, value='pslc')

@pn.depends(var_select.param.value, watch=True)
def update_level_widget(var):
    ds = ds_exps['EXP1']

    if var not in ds:
        level.options = []
        level.disabled = True
        return

    da = ds[var]

    vert_dim = get_vertical_dim(da)

    if vert_dim is None:
        level.options = []
        level.disabled = True
        return

    coords = da[vert_dim].values

    level.options = {
        format_level_value(v, vert_dim): v for v in coords
    }

    level.value = coords[0]
    level.disabled = False

update_level_widget(var_select.value)

clear_cache_btn = pn.widgets.Button(name='Limpar cache', button_type='danger')

def clear_cache(event):
    cache.clear()

clear_cache_btn.on_click(clear_cache)

cycle = pn.widgets.Select(
    name='Data (ciclos)',
    options={
        pd.to_datetime(t).strftime('%Y-%m-%d %H'): t
        for t in ds_exps['EXP1'].cycle.values
    }
)

lead_map = {
    f"{i*3}": i for i in ds_exps['EXP1'].lead.values
}

lead = pn.widgets.Select(
    name='Anl/Prev (horas)',
    options=lead_map,
    value=0
)

#diff_toggle = pn.widgets.Checkbox(name='Mostrar diferença (EXP - referência)', value=False)
diff_toggle = pn.widgets.Switch(name='Mostrar diferença (EXP - referência)', value=False)

ref_exp = pn.widgets.Select(name='Experimento referência', options=list(ds_exps.keys()), value='EXP1')

@pn.depends(
    var_select.param.value,
    cycle.param.value,
    lead.param.value,
    level.param.value,
    diff_toggle.param.value,
    ref_exp.param.value,
    watch=False
)
def update_plot(var, cycle, lead, level_value, diff, ref_name):

    print(var, cycle, lead, level_value, diff, ref_name)

    sample_da = ds_exps[ref_name][var]
    vert_dim = get_vertical_dim(sample_da)

    # 🔹 formatação do nível (uma vez só)
    if level_value is not None and vert_dim is not None:
        level_fmt = format_level_value(level_value, vert_dim)
        unit = "hPa" if 'lev' in vert_dim.lower() else ""
        level_str = f" | {level_fmt} {unit}" if unit else f" | {level_fmt}"
    else:
        level_str = ""

    plots = []

    ref_ds = get_field_cached(ref_name, var, cycle, lead, level_value)

    if ref_ds is None:
        return hv.Text(0.5, 0.5, f"{ref_name} sem dados para essa data")

    all_data = []

    for name in ds_exps:
        ds = get_field_cached(name, var, cycle, lead, level_value)

        if ds is None:
            continue

        if diff:
            ds = (ds - ref_ds).assign_attrs(ds.attrs)

        all_data.append(ds)

    if not all_data:
        return hv.Text(0.5, 0.5, "Sem dados para essa data").opts(title="Sem dados")

    all_concat = xr.concat(all_data, dim='exp')

    vmin = float(all_concat.min().compute())
    vmax = float(all_concat.max().compute())

    clim = (vmin, vmax)

    for name in ds_exps:
        ds = get_field_cached(name, var, cycle, lead, level_value)

        if ds is None:
            title = f"{name} | SEM DADOS"
            plots.append(hv.Text(0.5, 0.5, "Sem dados").opts(title=title))
            continue 

        if diff:
            ds_plot = ds - ref_ds
            title = f"{name} - {ref_name} | {var.upper()} | {pd.to_datetime(cycle):%Y-%m-%d %H} | +{lead*3}h{level_str}"
        else:
            ds_plot = ds
            title = f"{name} | {var.upper()} | {pd.to_datetime(cycle):%Y-%m-%d %H} | +{lead*3}h{level_str}"

        p = make_plot(ds_plot, title, clim=clim)
        plots.append(p)

    return hv.Layout(plots).cols(2)

cache_info = pn.pane.Markdown("")

def update_cache_info():
    info = cache.info()
    cache_info.object = f"""
**Cache size:** {info['size']}  
**Keys:** {info['keys']}
"""

pn.state.add_periodic_callback(update_cache_info, 2000)

controls = pn.Column(
    var_select,
    cycle,
    lead,
    level,
    ref_exp,
    diff_toggle,
    clear_cache_btn
)

plot_panel = pn.panel(update_plot, loading_indicator=True)

app = pn.Row(
    controls,
    pn.Column(plot_panel, cache_info)
)

app.servable()
