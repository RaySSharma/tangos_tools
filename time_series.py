import numpy as np
import tangos as db

def histogram_properties(obj, properties):
    """ Live-calculate each histogram property in 'properties'
    
    Arguments:
        obj {tangos.core.halo.Halo, tangos.core.halo.BH (object)} -- Tangos halo/BH object
        properties {list} -- Ldist of desired histogram properties that exist within Tangos database for that object
    
    Returns:
        histogram {list} -- Time-series histogram data
    """
    histogram = []
    for i, prop in enumerate(properties):
        try:
            histogram.append(list(obj.calculate(prop)))
        except db.live_calculation.NoResultsError as err:
            print(err, 'Property not calculated for this object:', prop)
        except KeyError as err:
            print(err, 'Property not found:', prop)

    return histogram

def structural_properties(halo, properties):
    """ Calculate history of each structural property in 'properties'
    
    Arguments:
        halo {tangos.core.halo.Halo (object)} -- Tangos halo object
        properties {list} -- List of desired properties that exist within Tangos database

    Returns:
        structural {list} -- Structural data for main progenitor line
    """
    try:
        structural = halo.calculate_for_progenitors('t()', *properties)
    except KeyError as err:
        print(err, 'Property not found')   
        structural = []

    return structural

def pad_series(to_pad, time_set, time_subset, pad_value=np.nan):
    ''' Fill a copy of "to_pad" with "pad_value" where "time_subset" does not match "time_set"
    '''
    ix = np.array([np.argmin(abs(time_set - idx)) for idx in time_subset])
    padded = np.array([pad_value]*len(time_set))
    padded[ix] = to_pad
    return padded
