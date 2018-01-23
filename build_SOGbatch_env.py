""" build_SOGbatch_env: A script for build SOG batch run environments.
This script reads a yaml input file and produces the editfiles, run
directories, and batchfile required to execute a SOG batch command for a
suite of SOG model runs. This script requires specific YAML field names
and values, and is designed to produce primarily the varied forcing and river
chemistry runs of Moore-Maley et al. 2016 and Moore-Maley et al. 2018
(in review). The example YAML file SOG_test.yaml should be preserved and a
copy should be made to accompany this script as it migrates.
"""

from dateutil.parser import parse
from datetime import datetime
import subprocess
import yaml
import os

# ------------------ Begin local funtion definitions --------------------------


def vary_forcing_parser(key, editfile_dict, forcing_inputs, run_year, run_tag):
    """
    """

    # Extra string for cloud fraction
    string = ''
    if key is 'river':
        string = '_flows'
    elif key is 'cloud':
        string = '_fraction'

    # Vary forcing True or False
    if forcing_inputs[0]:
        editfile_dict[key + string] = {
            'value': True,
        }
        run_tag = run_tag + '_{}'.format(key)

        # Fixed
        if forcing_inputs[1]:
            editfile_dict[key + string + '_fixed'] = {
                'value': True,
            }
            editfile_dict[key + string + '_value'] = {
                'value': forcing_inputs[2],
            }
            run_tag = run_tag + '_fix{:.0f}'.format(forcing_inputs[2])

        # Fraction
        if forcing_inputs[3] != 1:
            editfile_dict[key + string + '_fraction'] = {
                'value': forcing_inputs[3],
            }
            run_tag = run_tag + '_frac{:.0f}'.format(forcing_inputs[3]*100)

        # Add
        if forcing_inputs[4] != 0:
            editfile_dict[key + string + '_addition'] = {
                'value': forcing_inputs[4],
            }
            run_tag = run_tag + '_add{:.0f}'.format(forcing_inputs[4])

        # Shift
        if forcing_inputs[5] != 0 or forcing_inputs[6] != 0:
            run_tag = run_tag + '_shift'

            # By year
            if forcing_inputs[5] != 0:
                editfile_dict[key + string + '_shift'] = {
                    'value': forcing_inputs[5] - run_year,
                }
                run_tag = run_tag + '{:d}'.format(forcing_inputs[5])

            # By day
            if forcing_inputs[6] != 0:
                editfile_dict[key + string + '_shift'] = {
                    'value': editfile_dict[key + string + '_shift'] +
                    forcing_inputs[6]/365,
                }
                run_tag = run_tag + '_{:.0f}'.format(forcing_inputs[6])

    return editfile_dict, run_tag


def populate_editfile_dict(
    editfile_dict, datetimes, run_path, initial_path,
    ctd_dir, nuts_dir, init_files, hoffmueller=True
):
    """
    """

    # Parse timestamps
    datetime_start, datetime_end = map(parse, datetimes)

    # Assign paths and times to editfile dict
    editfile_dict.update({
        'initial_conditions': {
            'init_datetime': {
                'value': datetime_start,
            },
            'CTD_file': {
                'value': os.path.join(initial_path, ctd_dir, init_files[0]),
            },
            'nutrients_file': {
                'value': os.path.join(initial_path, nuts_dir, init_files[1]),
            },
        },
        'end_datetime': {
            'value': datetime_end,
        },
        'timeseries_results': {
            'std_physics': {
                'value': os.path.join(run_path, 'timeseries/std_phys_SOG.out'),
            },
            'user_physics': {
                'value': os.path.join(
                    run_path, 'timeseries/user_phys_SOG.out',
                ),
            },
            'std_biology': {
                'value': os.path.join(run_path, 'timeseries/std_bio_SOG.out'),
            },
            'user_biology': {
                'value': os.path.join(run_path, 'timeseries/user_bio_SOG.out'),
            },
            'std_chemistry': {
                'value': os.path.join(run_path, 'timeseries/std_chem_SOG.out'),
            },
            'user_chemistry': {
                'value': os.path.join(
                    run_path, 'timeseries/user_chem_SOG.out',
                ),
            },
        },
        'profiles_results': {
            'profile_file_base': {
                'value': os.path.join(run_path, 'profiles/SOG'),
            },
            'user_profile_file_base': {
                'value': os.path.join(run_path, 'profiles/SOG-user'),
            },
            'halocline_file': {
                'value': os.path.join(run_path, 'profiles/halo-SOG.out'),
            },
            'hoffmueller_file': {
                'value': os.path.join(run_path, 'profiles/hoff-SOG.dat'),
            },
            'user_hoffmueller_file': {
                'value': os.path.join(run_path, 'profiles/hoff-SOG-user.dat'),
            },
            'hoffmueller_start_year': {
                'value': datetime_start.year,
            },
            'hoffmueller_start_day': {
                'value': (
                    datetime_start - datetime(datetime_start.year, 1, 1)
                ).days + 2,
            },
            'hoffmueller_end_year': {
                'value': datetime_end.year,
            },
            'hoffmueller_end_day': {
                'value': (
                    datetime_end - datetime(datetime_end.year, 1, 1)
                ).days,
            },
        },
    })

    if not hoffmueller:
        editfile_dict['profiles_results'].update({
            'hoffmueller_end_year': {
                'value': datetime_start.year,
            },
            'hoffmueller_end_day': {
                'value': (
                    datetime_start - datetime(datetime_start.year, 1, 1)
                ).days + 3,
            },
        })

    return editfile_dict


# ------------------ End local funtion definitions ----------------------------

# Read batch yaml
with open('SOG_river.yaml', 'r') as f:
    data = yaml.load(f)

# Paths
results_path = os.path.join(
    data['paths']['runs_directory'], data['batch_name'],
)
initial_path = data['paths']['initial']
ctd_dir = data['initialization']['ctd_directory']
nuts_dir = data['initialization']['nutrients_directory']

# Check for forcing fields
vary_forcings = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]
if 'forcing' in data:
    if 'vary' in data['forcing']:
        vary_forcings = data['forcing']['vary']

# Check for river chemistry fields
vary_river_chem = False
river_TA, river_pH = [0, 0], [0]
if 'freshwater_chemistry' in data:
    vary_river_chem = True
    river_TA = data['freshwater_chemistry']['river_TA']
    river_pH = data['freshwater_chemistry']['river_pH']

# Build root directories
subprocess.call(['mkdir', data['batch_name']])
subprocess.call(['mkdir', os.path.join(data['batch_name'], 'editfiles')])
subprocess.call(['mkdir', results_path])

# Initialize batchfile dict
batchfile_dict = {
    'max_concurrent_jobs': data['max_concurrent_jobs'],
    'SOG_executable': os.path.join(data['paths']['SOG_code'], 'SOG'),
    'base_infile': os.path.join(data['paths']['SOG_code'], 'infile.yaml'),
    'jobs': [],
}

# Loop through datetimes
for datetimes, init_files in zip(
    data['initialization']['datetimes'],
    data['initialization']['files']
):

    # Parse run_year
    run_year = parse(datetimes[0]).year + 1

    # Build directories
    subprocess.call(['mkdir', os.path.join('editfiles', str(run_year))])
    subprocess.call(['mkdir', os.path.join(results_path, str(run_year))])

    # Loop through forcing scenarios
    for vary_forcing in vary_forcings:

        # Initialize editfile dict and run tag
        editfile_dict = {}
        run_tag = '{:d}'.format(run_year)

        # Parse forcing vary inputs
        forcing_inputs = {
            'wind': vary_forcing[:7],
            'river': vary_forcing[7:14],
            'cloud': vary_forcing[14:],
        }
        if any([
            forcing_inputs['wind'][0],
            forcing_inputs['river'][0],
            forcing_inputs['cloud'][0],
        ]):
            editfile_dict['vary'] = {}
            for key in ['wind', 'river', 'cloud']:
                editfile_dict['vary'], run_tag = vary_forcing_parser(
                    key, editfile_dict['vary'], forcing_inputs[key],
                    run_year, run_tag,
                )

        # Loop through river chemistry scenarios
        for TA in river_TA:
            for pH in river_pH:

                chem_tag = run_tag

                # Assign river chem params to editfile dict and update run_tag
                # (if they exist)
                if vary_river_chem:
                    editfile_dict['physics'] = {
                        'fresh_water': {'river_CO2_chemistry': {
                            'river_TA_record': {'value': TA[0]},
                            'river_total_alkalinity': {'value': TA[1]},
                            'river_pH': {'value': pH},
                        }}
                    }
                    if TA[0]:
                        TA_val = 'var'
                        editfile_dict['forcing_data'] = {
                            'major_river_forcing_file': {
                                'value': '../SOG-forcing/rivers/FraserTA.dat',
                            },
                        }
                    else:
                        TA_val = str(TA[1])
                    chem_tag = chem_tag + '_TA{}pH{:.0f}'.format(TA_val, pH*10)

                # Build paths and directories
                editfile_path = os.path.join(
                    data['batch_name'], 'editfiles', str(run_year),
                    'editfile_' + chem_tag,
                )
                run_path = os.path.join(results_path, str(run_year), chem_tag)
                subprocess.call(['mkdir', run_path])
                subprocess.call([
                    'mkdir', os.path.join(run_path, 'timeseries'),
                ])
                subprocess.call(['mkdir', os.path.join(run_path, 'profiles')])

                # Build editfile
                editfile_dict = populate_editfile_dict(
                    editfile_dict, datetimes, run_path, initial_path,
                    ctd_dir, nuts_dir, init_files, hoffmueller=True,
                )

                # Append run list in batchfile
                batchfile_dict['jobs'].append({
                    chem_tag: {
                        'edit_files': [editfile_path],
                        'outfile': os.path.join(
                            run_path, '{}.out'.format(chem_tag)
                        ),
                    }
                })

                # Write editfile yaml
                with open(editfile_path, 'w') as f:
                    yaml.dump(editfile_dict, f, default_flow_style=False)

                # Clear forcing data key from editfile dict
                editfile_dict.pop('forcing_data', None)

with open('run_{}_{}'.format(data['machine'], data['batch_name']), 'w') as f:
    yaml.dump(batchfile_dict, f, default_flow_style=False)
