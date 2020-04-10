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

        # print('TANGOS_SIMULATION_FOLDER:', os.environ['TANGOS_SIMULATION_FOLDER'])
        print("TANGOS_DB_CONNECTION:", os.environ["TANGOS_DB_CONNECTION"])

        self.database = pd.HDFStore(self.args.filename)
        self.key = self.args.sim
        self.args.func()

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
            "halos",
            type=str,
            help="Name of file containing halo numbers, one per line.",
        )
        subparse_generate.add_argument(
            "--filename",
            type=str,
            help="Output filename for HDF5 database file.",
            default="data.hdf5",
        )
        subparse_generate.add_argument(
            "--properties",
            action="store",
            nargs="+",
            help="Initial properties with which to populate database.",
            default="log10(Mvir)",
        )
        subparse_generate.add_argument(
            "--hist",
            help="Add time-histogram property",
            action="store_true",
            default=False,
        )
        subparse_generate.add_argument(
            "--verbose", help="Verbose output", action="store_true"
        )
        subparse_generate.set_defaults(func=self.add_simulation)

        subparse_add = subparse.add_parser(
            "add-property", help="Add property to existing simulation"
        )

        subparse_add.add_argument("db", type=str, help="Database file")
        subparse_add.add_argument(
            "sim", type=str, help="Simulation name within Tangos."
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

        return parser, subparse

    def _get_halo_numbers(self):
        try:
            with open(self.args.halos) as f:
                halo_numbers = f.read().splitlines()
            return np.array(halo_numbers).astype(int)
        except ValueError as err:
            print(err, "Incorrect type for halo number (int)")
            sys.exit()
        except FileNotFoundError as err:
            print(err, "File not found")
            sys.exit()

    def _get_snapshot(self):
        try:
            snapshot = db.get_timestep(self.args.sim + "/%" + self.args.snap)
            return snapshot
        except RuntimeError as err:
            print(err, "Could not find snapshot")
            sys.exit()

    def _get_object(self, halo_number):
        obj = self.snapshot[int(halo_number)]
        return obj

    def add_simulation(self):
        self.halo_numbers = self._get_halo_numbers()
        self.snapshot = self._get_snapshot()

        self.current_t = self.snapshot.time_gyr
        self.delta_t = db.properties.TimeChunkedProperty.pixel_delta_t_Gyr
        self.time = np.arange(self.delta_t, self.current_t, self.delta_t)
        self.write_headers()
        self.add_property()

        if self.args.verbose:
            print("Generated database")

    def add_property(self):
        if self.args.hist:
            df = self.calculate_property(
                self.args.properties, get_prop=ts.histogram_properties
            )
        else:
            df = self.calculate_property(
                self.args.properties, get_prop=ts.structural_properties
            )

        try:
            self.data = self.database[self.key]
            self.data = pd.concat([self.data, df])
        except KeyError:
            self.data = df

        self.database[self.key] = self.data

        if self.args.verbose:
            print("Added properties:", self.args.properties)

    def write_headers(self):
        headers = {
            "sim": self.args.sim,
            "snap": self.args.snap,
            "current_t": self.current_t,
            "delta_t": self.delta_t,
        }
        for attr in headers.keys():
            self.database.root[self.key]._v_attrs[attr] = headers[attr]

    def calculate_property(self, properties, get_prop=ts.structural_properties):
        data = []
        for halo_number in self.halo_numbers:
            obj = self._get_object(halo_number)
            t, struct = get_prop(obj, properties)
            struct = [ts.pad_series(s, self.time, t) for s in struct]
            data.append(struct)

        import pdb

        pdb.set_trace()
        index = pd.MultiIndex.from_product(
            [self.halo_numbers, properties], names=["halo_number", "property"]
        )
        df = pd.DataFrame(data, columns=self.time, index=index)
        return df

    def delete_property(self, properties):
        return


class DefaultHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help()
        sys.exit(2)


if __name__ == "__main__":
    AnalysisDB()
