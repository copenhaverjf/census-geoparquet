# census-geoparquet

This python script takes a location type (county, place, or zip code), a location, a state, a vintage, and a survey (ACS 5-Year or Decennial Census)
The Census Data API is used to fetch data. Block group resolution if available is used for counties otherwise census tract resolution is used on a per variable basis.
The ACS 5-Year tables to be pulled are from the Census\_Data\_To\_GeoParquet\_ACS\_5\_Year\_Tables file.
This file is in the format of the nonstandard JSON that the Census Data API returns (a Python list of lists).

The first list is: ["Detailed Tables", "Table 1",...,"Table n"].

The second list is: ["Subject Tables", "Table 1",...,"Table n"].

The TIGERweb GeoServices REST API is called to collect the map data for the user's chosen geogrpahy.
The results of both APIs are merged and outputed as a GeoParquet file.

# Important Notes
The map data for places appears to be empty. Besides this problem, places should be supported.
The scaffolding is in place to add Decennial Census support later.


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

Third, set the tables in the Census\_Data\_To\_GeoParquet\_ACS\_5\_Year\_Tables file.

Fourth, run the script giving it a location\_type, location, state, vintage, and survey.

Example:

your\_way\_of\_running\_python Census\_Data\_To\_GeoParquet\_Script.py County "Philadelphia County" Pennsylvania 2023 "ACS 5-Year"

Will output:
Philadelphia\_County\_Pennsylvania\_2023\_ACS\_5\_Year.geoparquet

DuckDB, with its spatial extension, can be used to query specific variables for Philadelphia County from this GeoParquet file.
