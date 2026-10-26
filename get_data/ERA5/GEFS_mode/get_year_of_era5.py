#!/usr/bin/env python

import cdsapi
import argparse

def format_year(value):
    """Parses the input to an integer and formats it as a 4-digit string."""
    try:
        return f"{int(value):04d}"
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid year: '{value}'. Must be an integer.")

def format_two_digits(value):
    """Parses the input to an integer and formats it as a 2-digit string."""
    try:
        return f"{int(value):02d}"
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid input: '{value}'. Must be an integer.")

### -------------------- lowest level ---------------------------------------------------

def download_lowest_model_level(args):
    """ Download the lowest model level through MARS server """

    # 1. Download atmospheric data for Level 137
    for param in ['130', '131', '132', '133']:  # t, u, v, q
        client = cdsapi.Client()
        client.retrieve('reanalysis-era5-complete', {
            'class': 'ea',
            'year':args.year,
            'month':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12'
            ],
            'day':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12',
                '13','14','15',
                '16','17','18',
                '19','20','21',
                '22','23','24',
                '25','26','27',
                '28','29','30',
                '31'
            ],
            'expver': '1',
            'levelist': '137',
            'levtype': 'ml',
            'param': param,
            'stream': 'oper',
            'time': '00/to/23/by/1',
            'type': 'an',
            'grid'    : '0.25/0.25',
            'format'  : 'netcdf',
        }, f"ERA5_y{args.year}_lev137_{param}.nc")

    return None

### -------------------- standard level ---------------------------------------------------
# we have to split the instant and accumulated fields, otherwise they get bundled inside zip file

def download_single_level_inst(args):
    """ instantaneous field near surface """

    variables= [
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "2m_dewpoint_temperature",   # needed for specific humidity
        "2m_temperature",
        "mean_sea_level_pressure",
        "sea_surface_temperature",
        "surface_pressure",          # needed for specific humidity
        "geopotential",
        "sea_ice_cover",
    ]

    dataset = "reanalysis-era5-single-levels"
    for v in variables:
        request = {
            "product_type": ["reanalysis"],
            "variable": v,
            "year": [str(args.year)],
            'month':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12'
            ],
            'day':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12',
                '13','14','15',
                '16','17','18',
                '19','20','21',
                '22','23','24',
                '25','26','27',
                '28','29','30',
                '31'
            ],
            "time": [
                "00:00", "01:00", "02:00",
                "03:00", "04:00", "05:00",
                "06:00", "07:00", "08:00",
                "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00",
                "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
                "21:00", "22:00", "23:00"
            ],
            "data_format": "netcdf",
            "download_format": "unarchived"
        }
    
        client = cdsapi.Client()
        client.retrieve(dataset, request).download()
        client.retrieve(dataset, request, f"ERA5_y{args.year}_inst_{v}.nc")
    return None


def download_single_level_accum(args):
    """ instantaneous field near surface """

    variables= [
        "surface_latent_heat_flux",
        "surface_net_solar_radiation",
        "surface_net_thermal_radiation",
        "surface_sensible_heat_flux",
        "surface_solar_radiation_downwards",
        "surface_thermal_radiation_downwards"
    ]

    dataset = "reanalysis-era5-single-levels"
    for v in variables:
        request = {
            "product_type": ["reanalysis"],
            "variable": v,
            "year": [str(args.year)],
            'month':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12'
            ],
            'day':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12',
                '13','14','15',
                '16','17','18',
                '19','20','21',
                '22','23','24',
                '25','26','27',
                '28','29','30',
                '31'
            ],
            "time": [
                "00:00", "01:00", "02:00",
                "03:00", "04:00", "05:00",
                "06:00", "07:00", "08:00",
                "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00",
                "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
                "21:00", "22:00", "23:00"
            ],
            "data_format": "netcdf",
            "download_format": "unarchived"
        }
    
        client = cdsapi.Client()
        client.retrieve(dataset, request, f"ERA5_y{args.year}_diag_fluxes_{v}.nc")
    return None


def download_single_level_avg(args):
    """ mean rates freshwater/radiative fluxes """

    variables= [
        "mean_snowfall_rate",
        "mean_surface_downward_long_wave_radiation_flux",
        "mean_surface_downward_short_wave_radiation_flux",
        "mean_total_precipitation_rate",
    ]

    dataset = "reanalysis-era5-single-levels"

    for v in variables:
        request = {
            "product_type": ["reanalysis"],
            "variable": v,
            "year": [str(args.year)],
            'month':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12'
            ],
            'day':[
                '01','02','03',
                '04','05','06',
                '07','08','09',
                '10','11','12',
                '13','14','15',
                '16','17','18',
                '19','20','21',
                '22','23','24',
                '25','26','27',
                '28','29','30',
                '31'
            ],
            "time": [
                "00:00", "01:00", "02:00",
                "03:00", "04:00", "05:00",
                "06:00", "07:00", "08:00",
                "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00",
                "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
                "21:00", "22:00", "23:00"
            ],
            "data_format": "netcdf",
            "download_format": "unarchived"
        }
    
        client = cdsapi.Client()
        client.retrieve(dataset, request, f"ERA5_y{args.year}_mean_fluxes_{v}.nc")

    return None


### -------------------- main script  ---------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Format date components into 4-digit and 2-digit strings.")

    # Define the arguments using the custom formatting functions
    parser.add_argument('-y', '--year', type=format_year, required=True, help="Year (e.g., 2026 or 99)")
    parser.add_argument('--with_diag_fluxes', action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    # The arguments are now pre-formatted strings
    print(f"Formatted Year:  {args.year}")

    # lowest model level
    download_lowest_model_level(args)

    # near-surface
    download_single_level_inst(args)

    # air density surface from wave model (may or may not be used)
    #download_single_level_wave(args)

    # heat fluxes (diagnostics)
    if args.with_diag_fluxes:
        download_single_level_accum(args)

    # freshwater/radiative fluxes
    download_single_level_avg(args)

if __name__ == "__main__":
    main()