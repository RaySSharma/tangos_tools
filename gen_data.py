#!/usr/bin/env python

import sys
import os
import argparse
import tangos as db
import pandas as pd
import numpy as np
import time_series as ts

# Todo
# store.root.df._v_attrs to store attributes
# 
class AnalysisDB(object):

    def __init__(self):
        self.parser, self.subparse = self._get_parser_object()
        self.args = self.parser.parse_args(sys.argv[1:])
        

        print('TANGOS_SIMULATION_FOLDER:', os.environ['TANGOS_SIMULATION_FOLDER'])
        print('TANGOS_DB_CONNECTION:', os.environ['TANGOS_DB_CONNECTION'])

        self.args.func()

    def _get_parser_object(self):
        parser = DefaultHelpParser()
        subparse = parser.add_subparsers()

        subparse_generate = subparse.add_parser('generate', help='Generate new database framework, or add simulations to existing database')
        subparse_generate.add_argument('sim', type=str, help='Simulation name within Tangos.')
        subparse_generate.add_argument('snap', type=str, help='Most recent timestep in time-series, or snapshot of interest.')
        subparse_generate.add_argument('halos', type=str, help='Name of file containing halo numbers, one per line.')
        subparse_generate.add_argument('--dbtype', type=str, help='Type of database to build', choices=['series', 'single'], default='series')
        subparse_generate.add_argument('--output', type=str, help='Output filename for HDF5 database file.', default='data.hdf5')
        subparse_generate.add_argument('--initial', type=str, help='Initial property to populate database with', default='log10(Mvir)')
        subparse_generate.add_argument('-v', '--verbose', help='Verbose output', action='store_true')
        subparse_generate.set_defaults(func=self.generate_database)

        subparse_add = subparse.add_parser('add', help='Add property to existing database')
        subparse_add.add_argument('db', type=str, help='Database file')
        subparse_add.add_argument('key', type=str, help='Key name within database')
        subparse_add.add_argument('properties', action='store', nargs='+', help='Names of Tangos halo properties to calculate')
        subparse_add.add_argument('-v', '--verbose' , help='Verbose output', action='store_true')

        return parser, subparse

    def _get_halo_numbers(self):
        try:
            with open(self.args.halos) as f:
                halo_numbers = f.read().splitlines()
            return np.array(halo_numbers).astype(int)
        except ValueError as err:
            print(err, 'Incorrect type for halo number (int)')
            sys.exit()
    
    def _get_snapshot(self):
        try:
            snapshot = db.get_timestep(self.args.sim + '/%' + self.args.snap)
            return snapshot
        except RuntimeError as err:
            print(err, 'Could not find snapshot')
            sys.exit()

    def generate_database(self):
        ''' Generate framework for database file
        '''
        self.halo_numbers = self._get_halo_numbers()
        self.snapshot = self._get_snapshot()

        self.current_t = self.snapshot.time_gyr
        self.delta_t = db.properties.TimeChunkedProperty.pixel_delta_t_Gyr
        self.time = np.arange(self.delta_t, self.current_t, self.delta_t)

        initial_prop = [self.args.initial]

        df = self.calculate_property(initial_prop, get_prop=ts.structural_properties)
        key = self.args.sim
        self.data = df
        self.data.to_hdf(self.args.output, mode='w', key=key)

        headers = self.gather_headers()
        headers.to_hdf(self.args.output, mode='w', key=key+'/header')

        if self.args.verbose:
            print('Generated database')


    def gather_headers(self):
        header = np.array([self.args.sim, self.args.snap, self.current_t, self.delta_t]).T
        df = pd.DataFrame(columns=['sim', 'snap', 'current_t', 'delta_t'])
        df.loc[0] = header
        return df 
        
    def add_histogram_property(self, properties):
        new_df = self.calculate_property(properties, get_prop=ts.histogram_properties)
        self.data = pd.concat([self.data, new_df])

    def add_structural_property(self, properties):
        new_df = self.calculate_property(properties, get_prop=ts.structural_properties)
        self.data = pd.concat([self.data, new_df])

    def calculate_property(self, properties, get_prop=ts.structural_properties):
        data = []
        for halo_number in self.halo_numbers:
            obj = self.get_object(halo_number)
            t, struct = get_prop(obj, properties)
            struct = ts.pad_series(struct, self.time, t)
            data.append(struct)

        index = pd.MultiIndex.from_product([self.halo_numbers, properties], names=['halo_number', 'property'])
        df = pd.DataFrame(data, columns=self.time, index=index)
        return df

    def get_object(self, halo_number):
        obj = self.snapshot[int(halo_number)]
        return obj

    def delete_property(self, properties):
        self.data

class DefaultHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)
        
if __name__ == "__main__":
    AnalysisDB()