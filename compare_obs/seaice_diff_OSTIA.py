#!/usr/bin/env python

#  Gemini was used to assist with developing this code.
# The code has been reviewed, edited, and validated by NWS staff.

import argparse
from datetime import datetime
import os
import warnings

import xesmf

from grids import create_grid_OSTIA, create_grid_RTOFS, create_regular_grid
from plotting import plot_polar_seaice_diff
from readers import read_HYCOM, read_MOM, read_OSTIA
from utils import str2bool, valid_date

warnings.filterwarnings("ignore", module="xesmf")




# --- main
def main():
    """Execute the main workflow to compute and plot RTOFS Seaice differences.

    Parses command-line arguments, reads observation and model grids,
    remaps seaice fields onto a regular 1x1 degree grid using xESMF (reusing or
    generating remapping weights), computes biases, and plots comparison results.
    """
    # Initialize the parser
    parser = argparse.ArgumentParser(
        description="Script to plot RTOFS SeaIce concentration against OSTIA."
    )

    # Required arguments
    parser.add_argument(
        "--ref_model", required=True, help="Path to the reference model."
    )
    parser.add_argument(
        "--dev_model", required=True, help="Path to the dev model."
    )
    parser.add_argument(
        "--obs", required=True, help="Path to the observations."
    )
    parser.add_argument(
        "--date",
        required=True,
        type=valid_date,
        help="Date to process (format: YYYY-MM-DD).",
    )
    parser.add_argument(
        "--days_offset",
        required=False,
        type=int,
        default=0,
        help="Add days for nowcast (down to -1) /forecast (up to 4). (default: 0)",
    )

    # Optional arguments
    parser.add_argument(
        "--grid",
        required=False,
        default=None,
        help="(Optional) Path to the model grid.",
    )

    parser.add_argument(
        "--ref_model_is_hycom",
        type=str2bool,
        required=False,
        default=True,
        help="(Optional) Is the reference model HYCOM? Accepts true/false. (default: true)",
    )

    parser.add_argument(
        "--use_forecast_t0",
        type=str2bool,
        required=False,
        default=False,
        help="(Optional) Use output from forecast for t = 0 (default: false). Only valid for RTOFS 2.X",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Print out the variables to verify
    print("--- Parsed Arguments ---")
    print(f"Reference Model : {args.ref_model}")
    print(f"Dev Model       : {args.dev_model}")
    print(f"Observations    : {args.obs}")
    print(f"Date            : {args.date}")
    print(f"Offset in days  : {args.days_offset}")
    print(f"Ref Model is HYCOM  : {args.ref_model_is_hycom}")
    print(f"Use t0 from forecast (HYCOM only)  : {args.use_forecast_t0}")

    if args.grid:
        print(f"Model Grid      : {args.grid}")
    else:
        print("Model Grid      : Not provided")

    seaice_ostia = read_OSTIA(args, "sea_ice_fraction")
    if args.ref_model_is_hycom:
        icecov_ref = read_HYCOM(args, "ice_coverage")
    else:
        icecov_ref = read_MOM(args, "ice_coverage")
    icecov_dev = read_MOM(args, "ice_coverage")

    grid_1x1 = create_regular_grid()
    print("reg grid created")

    cdate = datetime.strftime(args.date, "%Y%m%d")
    grid_ostia = create_grid_OSTIA(
        f"{args.obs}/{cdate}120000-UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc"
    )
    print("OSTIA grid created")

    grid_rtofs_ref = create_grid_RTOFS(args.grid, icecov_ref)
    print("RTOFS grid created")
    grid_rtofs_dev = create_grid_RTOFS(args.grid, icecov_dev)
    print("RTOFS grid created")

    # we should save weights offline
    if os.path.exists("esmf_wgts_ostia_1x1.nc"):
        remap_ostia = xesmf.Regridder(
            grid_ostia,
            grid_1x1,
            "conservative_normed",
            periodic=True,
            weights="esmf_wgts_ostia_1x1.nc",
        )
    else:
        print("remapping OSTIA, this may takes some time...")
        remap_ostia = xesmf.Regridder(
            grid_ostia, grid_1x1, "conservative_normed", periodic=True
        )
        remap_ostia.to_netcdf("esmf_wgts_ostia_1x1.nc")

    seaice_ostia_1x1deg = remap_ostia(seaice_ostia)

    if os.path.exists("esmf_wgts_rtofs_ref_1x1.nc"):
        remap_rtofs_ref = xesmf.Regridder(
            grid_rtofs_ref,
            grid_1x1,
            "conservative_normed",
            periodic=True,
            weights="esmf_wgts_rtofs_ref_1x1.nc",
        )
    else:
        print("remapping RTOFS ref, this may takes some time...")
        remap_rtofs_ref = xesmf.Regridder(
            grid_rtofs_ref, grid_1x1, "conservative_normed", periodic=True
        )
        remap_rtofs_ref.to_netcdf("esmf_wgts_rtofs_ref_1x1.nc")

    rtofs_ref_1x1 = remap_rtofs_ref(icecov_ref)

    if os.path.exists("esmf_wgts_rtofs_dev_1x1.nc"):
        remap_rtofs_dev = xesmf.Regridder(
            grid_rtofs_dev,
            grid_1x1,
            "conservative_normed",
            periodic=True,
            weights="esmf_wgts_rtofs_dev_1x1.nc",
        )
    else:
        print("remapping RTOFS dev, this may takes some time...")
        remap_rtofs_dev = xesmf.Regridder(
            grid_rtofs_dev, grid_1x1, "conservative_normed", periodic=True
        )
        remap_rtofs_dev.to_netcdf("esmf_wgts_rtofs_dev_1x1.nc")

    rtofs_dev_1x1 = remap_rtofs_dev(icecov_dev)

    fig = plot_polar_seaice_diff(grid_1x1, rtofs_ref_1x1, rtofs_dev_1x1, seaice_ostia_1x1deg, date=args.date, offset=args.days_offset)

    # change date and plot title to match nowcast/forecast
    if args.days_offset < 0:
        fout = (
            f"compare_seaice_{args.date}_tminus{-1 * args.days_offset:02g}days.png"
        )
    else:
        fout = f"compare_seaice_{args.date}_tplus{args.days_offset:02g}days.png"
    fig.savefig(fout, bbox_inches="tight", dpi=50)


if __name__ == "__main__":
    main()


# example:
#python seaice_diff_OSTIA.py --ref_model /scratch5/NCEPDEV/rstprod/Santha.Akella/data/rtofs/v2p5/output --dev_model /scratch5/NCEPDEV/rstprod/Santha.Akella/data/rtofs/v3_exp/May2026 --obs /scratch3/NCEPDEV/marine/Raphael.Dussin/obs/gridded/OSTIA_near_realtime --date 2025-12-21 --ref_model_is_hycom yes --grid /scratch3/NCEPDEV/global/role.glopara/fix/mom6/20250128/008/ocean_hgrid.nc --days_offset 0

