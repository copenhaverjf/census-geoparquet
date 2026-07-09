# census-geoparquet

This script takes a state and county from the user.

The Census Data API is called to fetch block group resolution data based upon the Census\_Data\_To\_GeoParquet\_Variables file.
This file is in the format of the nonstandard JSON that the Census Data API returns (a Python list of lists).

The TIGERweb GeoServices REST API is called to collect the map data for the user's chosen county at the block group level.

The results of both APIs are merged and outputed as a GeoParquet file.


# How to Use

First, declare an environment variable called "CENSUS\_DATA\_API\_KEY=your key for the Census Data API"

Second, make sure all of the following Python packages/modules are installed:
  "json" for the API calls
  "os" for getting the Census Data API key out of the environment variable
  "sys" for the command line arguments

  "geopandas" for writing the GeoParquet file
  "requests" for the API calls
  "shapely" for writing the GeoParquet file
  "pyarrow" for writing the GeoParquet file

Third, set the variables in the Census\_Data\_To\_GeoParquet\_Variables file 
(a nested python list of strings, one for "Tables" and one for "Individual Variables" in that order).

Fourth, run the script giving it a state and county.


# Plans for Improvement

Letting the user select between different vintages and between the ACS and the decennial census.
Not recording the state, county, tract, and block group twice in the GeoParquet output file.
Adding support for ZCTA resolution and tables/variables that have census tract resolution but not block group resolution.
