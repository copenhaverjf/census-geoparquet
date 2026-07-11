# File: Census_Data_To_GeoParquet_Script.py
# Author: Logan Marko
# Description: Using the Census Data API and the Census TIGERweb GeoServices Rest API, 
#              this python script takes a county or zip code tabulation area, state, 
#              vintage, and survey (ACS 5-Year or Decennial Census) and outputs a 
#              GeoParquet file that contains the results for the variables in the 
#              Census_Data_To_GeoParquet_ACS_5_Year_Variables file in the chosen geographies.
# Notes: The nonstandard version of JSON returned by the Census Data API is parsed as
#        a list of lists.
#
#        For User Input Validation, range is given 1 to len(valid_things) because the
#        first element explains structure instead of holding data.
#
#        All but the last get_string hold 50 variables because the Census Data API
#        takes a maximum of 50 variables per call.
#
#        The "Tables" and "Individual Variables" should not be removed from the
#        Census_Data_To_GeoParquet_ACS_5_Year_Variables file for organizational reasons.
#
#        It appears that for zctas geo id and ucgid are the same.
#
#        It appears the layer numbers for things like block groups and zctas on:
#        https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb
#        are sometimes changed. A match statement has been hardcoded for this issue.


import json
import os
import sys

import geopandas as gpd
import requests
from shapely.geometry import shape


## User Input Validation ##

if len(sys.argv) != 5:
  print(f"usage: {sys.argv[0]} county_or_zip_code_tabulation_area state vintage survey")
  sys.exit()

# What and when is being measured.
acs_5_year = False
decennial_census = False
vintage = 0

# Where is being measured.
state = ""
state_code = ""
county = False
county_code = ""
zcta = False # zip_code_tabulation_area
zcta_ucgid = ""

if sys.argv[4] == "ACS 5-Year":
  acs_5_year = True
elif sys.argv[4] == "Decennial Census":
  decennial_census = True
else:
  print(f"usage: {sys.argv[0]} county_or_zip_code_tabulation_area state vintage survey")
  print("survey options: \"ACS 5-Year\" or \"Decennial Census\"")
  sys.exit()

if not sys.argv[3].isdecimal():
  print(f"usage: {sys.argv[0]} county_or_zip_code_tabulation_area state vintage survey")
  print("vintage should be a number, for example, \"2023\"")
  sys.exit()
vintage = sys.argv[3]

if acs_5_year:
  states_reference_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=NAME&for=state:*&key={os.environ['CENSUS_DATA_API_KEY']}"
  valid_states = json.loads(requests.get(states_reference_query).text)
  #print(valid_states)

  for i in range(1, len(valid_states)):
    # valid_states[i] structure: [State Name, State Code]
    #print(valid_states[i])
    if sys.argv[2] == valid_states[i][0]:
      state_code = valid_states[i][1]
      state = sys.argv[2]
      break
  #print(state_code)
  #print(valid_state)
  if state == "":
    print(f"usage: {sys.argv[0]} county_or_zip_code_tabulation_area state vintage survey")
    print("state was not valid")
    sys.exit()

  counties_reference_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=NAME&for=county:*&in=state:{state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
  valid_counties = json.loads(requests.get(counties_reference_query).text)
  #print(valid_counties)

  for i in range(1, len(valid_counties)):
    # valid_counties[i] structure: [County Name, State Code, County Code]
    #print(valid_counties[i])
    if (sys.argv[1] + ", " +  sys.argv[2]) == valid_counties[i][0]:
      county = True
      county_code = valid_counties[i][2]
      break
  #print(county_code)
  #print(valid_county)
  if county_code == "":
    zcta_reference_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=NAME&ucgid=pseudo(0400000US{state_code}$8600000)&key={os.environ['CENSUS_DATA_API_KEY']}"
    valid_zctas = json.loads(requests.get(zcta_reference_query).text)
    #print(valid_zctas)
    for i in range(1, len(valid_zctas)):
      # valid_zctas[i] structure: ['ZCTA5 00000", 'ucgid']
      #print(valid_zctas[i])
      if ("ZCTA5 " + sys.argv[1]) == valid_zctas[i][0]:
        zcta = True
        zcta_ucgid = valid_zctas[i][1]
        break
    if zcta_ucgid == "":
      print(f"usage: {sys.argv[0]} county_or_zip_code_tabulation_area state vintage survey")
      print("county_or_zip_code_tabulation_area was not valid")
      sys.exit()

  #print(zcta_ucgid)
  #print(county_code)


  ## Collect Data Tables/Variables From File ##

  try:
    variables = json.loads(open("Census_Data_To_GeoParquet_ACS_5_Year_Variables", "rt").read())
  except:
    print("Census_Data_To_GeoParquet_ACS_5_Year_Variables file does not exist.")
    sys.exit()
  #print(variables)
  # variables structure: [["Tables", "Table 1", ..., "Table n"], ["Individual Variables", "Variable 1", ..., "Variable n"]]


  ## Call APIs and Merge Responses on Geo Ids ##

  geo_id_sort = {}
  geo_id_sort_keys = geo_id_sort.keys()
  # nested dictionary
  # {geo_id_1: {variable 1: value 1, ..., variable n: value n}, ..., geo_id_n {...}}

  get_strings = []
  # list of strings for the Census Data API get function, max of 50 variables per call


  ## Tables ##

  if len(variables[0]) != 1: # Check if there are tables to pull.
    for i in range(1, len(variables[0])):
      # variables[0] structure: ['Tables', 'Table 1', ..., 'Table n']
      #print(variables[0][i])
      if county:
        block_group_data_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=group({variables[0][i]})&for=block%20group&in=state:{state_code}%20county:{county_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
        census_table_data = json.loads(requests.get(block_group_data_query).text)
        # census_table_data[ ] structure: ["Variable 1", ..., "Variable n", "geo id", "Name", "state", "county", "tract", "block group"]
        #print(census_table_data)
        #print() # these two print statements are for making space between tables
        #print()
        table_variables = census_table_data[0]
        for j in range(1, len(census_table_data)):
          #print(census_table_data[j][-6][9:]) # geo id,
          #[9:] is for chopping off the beginning that the census data starts geo ids with but the map data doesn't
          if census_table_data[j][-6][9:] not in geo_id_sort_keys:
            geo_id_sort[census_table_data[j][-6][9:]] = {}
          for k in range(0, len(table_variables) - 6): # geo id to block group is not needed, they're already in the map data
            geo_id_sort[census_table_data[j][-6][9:]][table_variables[k]] = census_table_data[j][k]
  #print(geo_id_sort)
      else: # zcta was chosen
        zcta_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=group({variables[0][i]})&ucgid={zcta_ucgid}&key={os.environ['CENSUS_DATA_API_KEY']}"
        #print(zcta_query)
        census_table_data = json.loads(requests.get(zcta_query).text)
        # census_table_data[ ] structure: ["Variable 1", ..., "Variable n", "geo_id", "name", "ucgid"]
        #print(census_table_data)
        #print() # these two print statements are for making space between tables
        #print()
        #print(census_table_data[1][-3][9:])
        #[9:] is for chopping off the beginning that the census data starts geo ids with but the map data doesn't
        table_variables = census_table_data[0]
        if census_table_data[1][-3][9:] not in geo_id_sort_keys:
          geo_id_sort[census_table_data[1][-3][9:]] = {}
        for j in range(0, len(census_table_data[0]) - 3): # geo_id, name, and ucgid are not needed here, they're already in the map data
          geo_id_sort[census_table_data[1][-3][9:]][census_table_data[0][j]] = census_table_data[1][j]
  #print(geo_id_sort)

  ## Individual Variables ##

  if len(variables[1]) != 1: # Check if there are individual variables to pull
    get_string = ""
    variable_counter = 0
    for i in range(1, len(variables[1])): 
      # variables[1] structure: ['Individual Variables', 'Variable 1', ..., 'Variable n']
      if variable_counter == 49:
        get_strings.append(get_string)
        get_string = ""
        variable_counter = 0
      if variable_counter == 0: 
        get_string = get_string + f"{variables[1][i]}"
        variable_counter = variable_counter + 1
      else:
        get_string = get_string + f",{variables[1][i]}"
        variable_counter = variable_counter + 1
    get_strings.append(get_string)
  #print(get_strings)
    if county:
      for i in range(0, len(get_strings)):
        # i structure: 'Variable 1,...,Variable 50'
        block_group_data_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get={get_strings[i]}&for=block%20group&in=state:{state_code}%20county:{county_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
        census_data = json.loads(requests.get(block_group_data_query).text)
        #print(census_data)
        individual_variables = census_data[0]
        #print(individual_variables)
        for j in range(1, len(census_data)):
          # j structure: ["Variable 1", ..., "Variable n", "state", "county", "tract", "block group"]
          geo_id = census_data[j][-4] + census_data[j][-3] + census_data[j][-2] + census_data[j][-1]
          #print(geo_id)
          if geo_id not in geo_id_sort_keys:
            geo_id_sort[geo_id] = {}
          for k in range(0, len(individual_variables) - 4): # The state, county, tract, and block group are not needed here.
            # The mapping data already has them.
            geo_id_sort[geo_id][individual_variables[k]] = census_data[j][k]
    else: # zcta was chosen
      for i in range(0, len(get_strings)):
        # i structure: 'Variable 1,...,Variable 50'
        zcta_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get={get_strings[i]}&ucgid={zcta_ucgid}&key={os.environ['CENSUS_DATA_API_KEY']}"
        census_data = json.loads(requests.get(zcta_query).text)
        #print(census_data)
        individual_variables = census_data[0]
        #print(individual_variables)
        if census_data[1][-1][9:] not in geo_id_sort_keys:
          geo_id_sort[census_data[1][-1][9:]] = {}
        for j in range(0, len(individual_variables) - 1): # geo id is not needed here. It is in the map data.
          geo_id_sort[census_data[1][-1][9:]][census_data[0][j]] = census_data[1][j]
  #print(geo_id_sort)
  #for i in geo_id_sort:
    #print(geo_id_sort[i])


  ## Colect Map Data From the Census TIGERweb GeoServices Rest API ##
  if county:
    match vintage:
      case "2021" | "2022":
        layer = 8
      case "2012" | "2013" | "2014" | "2015" | "2016" | "2017" | "2018" | "2019" | "2023" | "2024" | "2025" :
        layer = 10
      case _:
        print(f"Map data does not exist for {vintage}")
        sys.exit()
    block_group_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{layer}/query?where=(COUNTY=%27{county_code}%27%20AND%20STATE=%20%27{state_code}%27)&outFields=*&f=geojson"
    #print(block_group_map_query)
    census_map_data = json.loads(requests.get(block_group_map_query).text)
    #print(census_map_data)
  else: # zcta was chosen
    if 2012 <= int(vintage) and int(vintage) <= 2019:
      layer = 2
    elif int(vintage) == 2021 or int(vintage) == 2022:
      layer = 0
    elif 2023 <= int(vintage) and int(vintage) <= 2025:
      layer = 2
    else:
      print(f"{sys.argv[4]}: map data does not exist for {vintage}")
      sys.exit()
    zcta_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{layer}/query?where=ZCTA5=%27{sys.argv[1]}%27&outFields=*&f=geojson"
    census_map_data = json.loads(requests.get(zcta_map_query).text)
    #print(census_map_data)



records = []
for feature in census_map_data["features"]:
  geom = shape(feature["geometry"]) #parse GeoJSON geometry
  props = feature.get("properties", {}) #whatever is already on the feature
  #print(props)
  #props['GEOID']
  record = {
    "geometry": geom,
    **props,
  }
  #print(variables_sorted_by_geo_id[props['GEOID']])
  for j in geo_id_sort[props['GEOID']]:
    #print(j)
    #print(variables_sorted_by_geo_id[props['GEOID']][j])
    record[j] = geo_id_sort[props['GEOID']][j]

  records.append(record)
gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
output_file_name = f"{sys.argv[1]} {sys.argv[2]}.geoparquet"
gdf.to_parquet(output_file_name.replace(' ', '_'))
