#!/usr/bin/env python

import sys
import os
import argparse
import tangos as db
import pandas as pd
import numpy as np
import time_series as ts


class AnalysisDB(object):
    def __init__(self):
        self.parser, self.subparse = self._get_parser_object()
        self.args = self.parser.parse_args(sys.argv[1:])

        print("TANGOS_DB_CONNECTION:", os.environ["TANGOS_DB_CONNECTION"])

        self.database = pd.HDFStore(self.args.filename)
        self.key = self.args.sim
        self.args.func()
        self.database.close()

    def _get_parser_object(self):
        parser = DefaultHelpParser()
        subparse = parser.add_subparsers()

        subparse_generate = subparse.add_parser(
            "add-simulation", help="Add simulations to new or existing database"
        )

        subparse_generate.add_argument(
            "sim", type=str, help="Simulation name within Tangos."
        )
        subparse_generate.add_argument(
            "snap",
            type=str,
            help="Most recent timestep in time-series, or snapshot of interest.",
        )
        subparse_generate.add_argument(
            "--filename",
            type=str,
            help="Output filename for HDF5 database file.",
            default="data.h5",
        )
        subparse_generate.add_argument(
            "--verbose", help="Verbose output", action="store_true"
        )
        subparse_generate.set_defaults(func=self.add_simulation)


        subparse_add = subparse.add_parser(
            "add-property", help="Add property to existing simulation"
        )

        subparse_add.add_argument("filename", type=str, help="Database file")
        subparse_add.add_argument(
            "sim", type=str, help="Simulation name within Tangos."
        )
        subparse_add.add_argument(
            "halos",
            type=str,
            help="Name of file containing halo numbers, one per line.",
        )
        subparse_add.add_argument(
            "properties",
            action="store",
            nargs="+",
            help="Names of Tangos halo properties to calculate",
        )
        subparse_add.add_argument(
            "--hist",
            help="Add time-histogram property",
            action="store_true",
            default=False,
        )
        subparse_add.add_argument(
            "--verbose", help="Verbose output", action="store_true"
        )
        subparse_add.set_defaults(func=self.add_property)


        subparse_delete = subparse.add_parser(
            "delete-property", help="Remove properties from existing database"
        )
        subparse_delete.add_argument("filename", type=str, help="Database file")
        subparse_delete.add_argument(
            "sim", type=str, help="Simulation name within Tangos."
        )
        subparse_delete.add_argument(
            "properties",
            action="store",
            nargs="+",
            help="Names of Tangos halo properties to remove",
        )
        subparse_delete.add_argument(
            "--verbose", help="Verbose output", action="store_true"
        )
        subparse_delete.set_defaults(func=self.delete_property)

        return parser, subparse

    def _get_halo_numbers(self):
        try:
            with open(self.args.halos) as f:
                halo_numbers = f.read().splitlines()
            return np.array(halo_numbers).astype(int)
        except ValueError as err:
            print(err, "Incorrect type for halo number (int)")
        except FileNotFoundError as err:
            print(err, "File not found")
        sys.exit()

    def _get_snapshot(self):
        try:
            snapshot = db.get_timestep(self.sim + "/%" + self.snap)
            return snapshot
        except RuntimeError as err:
            print(err, "Could not find snapshot")
        except AttributeError:
            print(err, "Could not find snapshot")
        sys.exit()

    def _get_object(self, halo_number):
        try:
            obj = self.snapshot[int(halo_number)]
            return obj
        except KeyError as err:
            print(err, "Could not find snapshot")
        sys.exit()

    def _get_headers(self):
        keys = ["sim", "snap", "current_t", "delta_t"]
        headers = {}
        for key in keys:
            headers[key] = self.database.root[self.key]._v_attrs[key]
        return headers

    def add_simulation(self):
        self.sim = self.args.sim
        self.snap = self.args.snap
        self.snapshot = self._get_snapshot()

        self.current_t = self.snapshot.time_gyr
        self.delta_t = db.properties.TimeChunkedProperty.pixel_delta_t_Gyr
        self.time = np.arange(self.delta_t, self.current_t, self.delta_t)
        self.format_dataframe() 
        self._write_headers()

        if self.args.verbose:
            print("Generated database")

    def _write_headers(self):
        headers = {
            "sim": self.sim,
            "snap": self.snap,
            "current_t": self.current_t,
            "delta_t": self.delta_t,
        }
        for attr in headers.keys():
            self.database.root[self.key]._v_attrs[attr] = headers[attr]

    def format_dataframe(self):
        index = pd.MultiIndex.from_product([[], []], names=["halo_number", "property"])
        self.data = pd.DataFrame(columns=self.time, index=index)
        self.database[self.key] = self.data
        
    def add_property(self):
        self.headers = self._get_headers()
        self.sim = self.headers['sim']
        self.snap = self.headers['snap']
        self.current_t = self.headers['current_t']
        self.delta_t = self.headers['delta_t']
        self.time = np.arange(self.delta_t, self.current_t, self.delta_t)

        self.snapshot = self._get_snapshot()
        self.halo_numbers = self._get_halo_numbers()

        if self.args.hist:
            new_df = self.calculate_property(
                self.args.properties, get_prop=ts.histogram_properties
            )
        else:
            new_df = self.calculate_property(
                self.args.properties, get_prop=ts.structural_properties
            )

        try:
            old_df = self.database[self.key]
            self.data = pd.concat([old_df, new_df])
        except KeyError as err:
            print(err, 'Simulation not found within database.')

        self.database[self.key] = self.data
        self._write_headers()

        if self.args.verbose:
            print("Added properties:", self.args.properties)

    def calculate_property(self, properties, get_prop=ts.structural_properties):
        num_rows = len(self.halo_numbers) * len(properties)
        num_cols = len(self.time)
        data = []
        for halo_number in self.halo_numbers:
            obj = self._get_object(halo_number)
            t, prop = get_prop(obj, properties, self.time)
            data.append(prop)
        data = np.asarray(data).reshape(num_rows, num_cols)
        index = pd.MultiIndex.from_product(
            [self.halo_numbers, properties], names=["halo_number", "property"]
        )
        df = pd.DataFrame(data, columns=self.time, index=index)
        return df

    def delete_property(self):
        properties = self.args.properties
        self.headers = self._get_headers()
        self.sim = self.headers['sim']
        self.snap = self.headers['snap']
        self.current_t = self.headers['current_t']
        self.delta_t = self.headers['delta_t']
        self.data = self.database[self.key]

        if np.in1d(properties, self.data.index.get_level_values(1)).all():
            self.database[self.key] = self.data.query('property not in @properties')
            print('Removed properties:', *properties)
        else:
            failed = [prop for prop in properties if prop not in self.data.index.get_level_values(1)]
            print('Properties not found:', *failed)
        self._write_headers()
class DefaultHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help()
        sys.exit(2)


if __name__ == "__main__":
    AnalysisDB()
