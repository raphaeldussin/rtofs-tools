#!/usr/bin/env python

# Gemini was used to assist with developing this code.
# The code has been reviewed, edited, and validated by NWS staff.

from datetime import datetime, timedelta
from glob import glob
import xarray as xr

__all__ = [
    "read_HYCOM",
    "read_MOM",
    "read_OSTIA",
    "read_CMEMS",
    "read_model",
    "read_obs",
]

# Variable to file kind mappings for HYCOM 2D files
HYCOM_VAR_KINDS = {
    "sst": "prog",
    "sss": "prog",
    "ssh": "diag",
    "ice_coverage": "ice",
}

# Variable to filename pattern mappings for CMEMS observation files
CMEMS_VAR_PATTERNS = {
    "sos": "dataset-sss-ssd-*-daily_{cdate}T1200Z_P*.nc",
    "adt": "dt_global_allsat_phy_l4_{cdate}_*.nc",
}


def read_HYCOM(args, var, file_kind=None, model_dir=None):
    """Read a 2D surface variable from HYCOM RTOFS output.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing base date ('date'),
        reference model directory ('ref_model'), forecast/nowcast offset ('days_offset'),
        and optional 'use_forecast_t0'.
    var : str
        Variable to extract (e.g., 'sst', 'sss', 'ssh', 'ice_coverage').
    file_kind : str, optional
        HYCOM 2D file category ('prog', 'diag', or 'ice'). If None, inferred
        from `var` (defaulting to 'prog').
    model_dir : str, optional
        Path to model directory. If None, defaults to `args.ref_model`.

    Returns
    -------
    xarray.DataArray
        The 2D HYCOM data array with the extra Arctic boundary row removed.
    """
    cdate = datetime.strftime(args.date, "%Y%m%d")
    days_offset = args.days_offset
    model_dir = model_dir or getattr(args, "ref_model", None)
    use_forecast_t0 = getattr(args, "use_forecast_t0", False)

    if (days_offset > 0.0) or use_forecast_t0:  # is forecast
        tplus = 24 * days_offset
        lead = f"f{tplus:03g}"
    else:
        if days_offset < -1:
            raise ValueError("days offset cannot be less than -1 day")
        tminus = 24 * (1 + days_offset)
        lead = f"n{tminus:03g}"

    if file_kind is None:
        file_kind = HYCOM_VAR_KINDS.get(var, "prog")

    ncfile = f"{model_dir}/rtofs.{cdate}/rtofs_glo_2ds_{lead}_{file_kind}.nc"
    print(f"reading {var} from {ncfile}")
    data = xr.open_dataset(ncfile)[var].squeeze()[:-1, :]  # hycom has one more row
    return data


def read_MOM(args, var, suffix=None, model_dir=None):
    """Read a 2D surface variable from MOM RTOFS output.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing dev model directory ('dev_model'),
        base date ('date'), and forecast/nowcast offset ('days_offset').
    var : str
        Variable to extract (e.g., 'sst', 'sss', 'ssh', 'ice_coverage').
    suffix : str, optional
        Filename suffix (e.g., '.nc' or '.ice.nc'). If None, inferred
        from `var` ('.ice.nc' for ice coverage, '.nc' otherwise).
    model_dir : str, optional
        Path to model directory. If None, defaults to `args.dev_model`.

    Returns
    -------
    xarray.DataArray
        The 2D MOM data array.
    """
    cdate = datetime.strftime(args.date, "%Y%m%d")
    days_offset = args.days_offset
    model_dir = model_dir or getattr(args, "dev_model", None)

    if days_offset > 0.0:  # is forecast
        tplus = 24 * days_offset
        lead = f"f{tplus:03g}"
    else:  # days_offset <= 0 is nowcast
        tminus = -1 * 24 * days_offset
        lead = f"tm{tminus:03g}"

    if suffix is None:
        suffix = ".ice.nc" if var in ("ice_coverage", "ice") else ".nc"

    ncfile = f"{model_dir}/rtofs.{cdate}/rtofs_glo_2ds.{lead}{suffix}"
    print(f"reading {var} from {ncfile}")
    data = xr.open_dataset(ncfile)[var].squeeze()
    return data


def read_OSTIA(args, var="analysed_sst", offset=None):
    """Read gridded observation data from OSTIA NetCDF files.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing base date ('date'),
        observations directory ('obs'), and forecast/nowcast offset ('days_offset').
    var : str, optional
        Variable to extract (e.g., 'analysed_sst', 'sea_ice_fraction').
        Default is 'analysed_sst'.
    offset : float, optional
        Offset to subtract from the data (e.g., 273.15 for Kelvin to Celsius).
        If None, defaults to 273.15 for 'analysed_sst' and 0.0 for all other variables.

    Returns
    -------
    xarray.DataArray
        The 2D squeezed and offset-adjusted OSTIA data array.
    """
    date_offset = args.date + timedelta(days=args.days_offset)
    cdate = datetime.strftime(date_offset, "%Y%m%d")
    ncfile = (
        f"{args.obs}/{cdate}120000-UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc"
    )
    print(f"reading {var} from {ncfile}")
    data = xr.open_dataset(ncfile)[var].squeeze()

    if offset is None:
        offset = 273.15 if var == "analysed_sst" else 0.0
    if offset:
        data = data - offset

    return data


def read_CMEMS(args, var, pattern=None):
    """Read gridded observation data from CMEMS NetCDF files.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing base date ('date'),
        observations directory ('obs'), and forecast/nowcast offset ('days_offset').
    var : str
        Variable to extract (e.g., 'sos' for SSS, 'adt' for SSH).
    pattern : str, optional
        Filename glob template with '{cdate}' placeholder. If None,
        selected automatically based on `var`.

    Returns
    -------
    xarray.DataArray
        The 2D squeezed CMEMS data array.
    """
    date_offset = args.date + timedelta(days=args.days_offset)
    cdate = datetime.strftime(date_offset, "%Y%m%d")

    if pattern is None:
        pattern = CMEMS_VAR_PATTERNS.get(var)
        if pattern is None:
            raise ValueError(
                f"No default file pattern for CMEMS variable '{var}'. "
                f"Please pass `pattern` explicitly."
            )

    glob_pattern = f"{args.obs}/{pattern.format(cdate=cdate)}"
    obsfile_thisdate = glob(glob_pattern)
    print(obsfile_thisdate)
    assert len(obsfile_thisdate) == 1, (
        f"Expected exactly 1 CMEMS file matching {glob_pattern}, "
        f"found {len(obsfile_thisdate)}"
    )
    ncfile = obsfile_thisdate[0]
    print(f"reading {var} from {ncfile}")
    data = xr.open_dataset(ncfile)[var].squeeze()
    return data


def read_model(args, model, var, file_kind=None, model_dir=None):
    """Generic reader dispatching to HYCOM or MOM RTOFS models.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    model : str
        Model identifier ('hycom' or 'mom', case-insensitive).
    var : str
        Variable to extract.
    file_kind : str, optional
        HYCOM file kind ('prog', 'diag', 'ice') or MOM file suffix ('.nc', '.ice.nc').
    model_dir : str, optional
        Path to model directory. If None, defaults to `args.ref_model` for HYCOM
        or `args.dev_model` for MOM.

    Returns
    -------
    xarray.DataArray
        Extracted 2D data array.
    """
    model_type = model.lower()
    if model_type == "hycom":
        return read_HYCOM(args, var, file_kind=file_kind, model_dir=model_dir)
    elif model_type == "mom":
        return read_MOM(args, var, suffix=file_kind, model_dir=model_dir)
    else:
        raise ValueError(f"Unsupported model '{model}'. Choose 'hycom' or 'mom'.")


def read_obs(args, obs_source, var, offset=None, pattern=None):
    """Generic reader dispatching to OSTIA or CMEMS observations.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    obs_source : str
        Observation source ('ostia' or 'cmems', case-insensitive).
    var : str
        Variable to extract.
    offset : float, optional
        Offset to subtract (OSTIA only).
    pattern : str, optional
        File pattern template (CMEMS only).

    Returns
    -------
    xarray.DataArray
        Extracted 2D data array.
    """
    source_type = obs_source.lower()
    if source_type == "ostia":
        return read_OSTIA(args, var, offset=offset)
    elif source_type == "cmems":
        return read_CMEMS(args, var, pattern=pattern)
    else:
        raise ValueError(
            f"Unsupported observation source '{obs_source}'. Choose 'ostia' or 'cmems'."
        )
