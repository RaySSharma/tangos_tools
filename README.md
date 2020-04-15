# tangos_tools

*tangos_tools* is a Python3 package that makes it easy to scrape properties from a pre-existing [Tangos](https://pynbody.github.io/tangos/) database, and places them within a portable HDF5 file that is easily accessed with [Pandas](https://pandas.pydata.org/).

Primary features include:
* Calculate many properties for many halos at once
* Save time-series data in an easy-to-query format
* Save properties from many simulations in the same HDF5 file
* Easily remove previously saved properties
* Data is stored within a small HDF5 database rather than accessed from a large *Tangos* database.

## Requirements
* numpy >= 1.17.2
* pandas >= 0.25.1
* tangos >= 1.0.9

## Getting started

*tangos_tools* can be run through the `run_tools.py` script. In order to find your existing *Tangos* database, the `TANGOS_DB_CONNECTION` environment variable must be [set correctly](https://pynbody.github.io/tangos/index.html).

Below are some examples of the various features. Each feature has its own help function for clarifying syntax, `./run_tools.py <arg> --help`

```
$ ./run_tools.py --help

usage: run_tools.py [-h]
                            {add-simulation,add-property,delete-property} ...

positional arguments:
  {add-simulation,add-property,delete-property}
    add-simulation      Add simulations to new or existing database
    add-property        Add property to existing simulation
    delete-property     Remove properties from existing database

optional arguments:
  -h, --help            show this help message and exit
```

### Adding Simulations
We first instantiate the new *tangos_tools* database from the existing *Tangos* simulation `tutorial_changa` at timestep `448`. We can use the `--filename` flag to specify a name for the new database, and the `--verbose` flag to get additional console output.

```
$ ./run_tools.py add-simulation tutorial_changa 448 --filename test_database.h5 --verbose

TANGOS_DB_CONNECTION: /home/RaySSharma/tangos_tools/tangos_data.db
Generated database: /home/RaySSharma/tangos_tools/test_database.h5
```

### Adding Properties
Next we can add properties to the database. At the moment, only time-series data is fully supported. Properties are by default calculated for the main progenitor branch of input halos, ending at the timestep supplied when generating the database. Halos are supplied via a text file, with one halo number per line.

We add the `Mvir` property as well as the `halo_number()` and `dm_density_profile
[-1]` live calculations for halos in the `halos.dat` file. Note the quotes around the live calculation properties.

```
$ ./run_tools.py add-property data.h5 tutorial_changa halos.dat Mvir 'halo_number()' 'dm_density_profile[-1]' --verbose

TANGOS_DB_CONNECTION: /home/RaySSharma/tangos_tools/tangos_data.db
Added properties: Mvir halo_number() dm_density_profile[-1]
```

Time-histogram properties can also be added to the same database with the same syntax but including the `--hist` flag. 

```
$ ./run_tools.py add-property data.h5 tutorial_changa halos.dat SFR_histogram --hist
```

### Removing Properties
Finally we can remove properties from the *tangos_tools* database. Here we remove the 'Mvir' property.

```
$ ./run_tools.py delete-property data.h5 tutorial_changa Mvir --verbose

TANGOS_DB_CONNECTION: /home/RaySSharma/tangos_tools/tangos_data.db
Removed properties: Mvir
```

## Accessing the New Data

The new database can be accessed at any time during this process using *Pandas*.

There are two primary ways to access the `tutorial_changa` simulation outputs within the new database.

1) The entire database file can be read in:
```
>>> import pandas
>>> database = pandas.HDFStore('test_database.h5', mode='r')
>>> database.keys()
['/tutorial_changa']
```
Here we see that the simulation we added is now a key within the HDF5 file, which can be easily accessed and placed within a *Pandas* DataFrame:
```
>>> df = database['tutorial_changa']
```

2) The specific simulation can be read directly into a *Pandas* DataFrame:
```
>>> import pandas
>>> df = pandas.read_hdf('test_database.h5', key='tutorial_changa', mode='r')
```