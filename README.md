# census-geoparquet

This python script takes a county or zip code, a state, a vintage, and a survey (ACS 5-Year).
The Census Data API is called to fetch block group resolution data based upon the Census\_Data\_To\_GeoParquet\_ACS\_5\_Year\_Variables file.
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

Third, set the variables in the Census\_Data\_To\_GeoParquet\_ACS\_5\_Year\_Variables file 
(a nested Python list of strings, one for "Tables" and one for "Individual Variables" in that order).

Fourth, run the script giving it a county or zip code, the state that contains that county or zip code, a vintage year, and a survey.

Example:

your\_way\_of\_running\_python Census\_Data\_To\_GeoParquet\_Script.py "Philadelphia County" Pennsylvania 2023 "ACS 5-Year"


# Plans for Improvement

Support for the Decennial Census and tables/variables that have census tract resolution but not block group resolution.
