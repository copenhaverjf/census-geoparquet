# File: Census_Data_To_GeoParquet_Script.py
# Author: Logan Marko
# Description: This script calls the Census Data API and the Census TIGERweb
#              GeoServices Rest API for data based upon a user chosen state 
#              and county. The data is at Census Block Group resolution. The 
#              data from both APIs is outputed to a GeoParquet file.

import json
import os
import sys

import geopandas as gpd
import requests
from shapely.geometry import shape


## User Input Validation ##
if len(sys.argv) != 3:
  print(f"usage: {sys.argv[0]} state county");
  sys.exit()

states_reference_query = f"https://api.census.gov/data/2023/acs/acs5?get=NAME&for=state:*&key={os.environ['CENSUS_DATA_API_KEY']}"

valid_states = json.loads(requests.get(states_reference_query).text)
#print(valid_states)

valid_state_flag = False

for i in valid_states:
  # i structure: [State Name, State Code]
  #print(i)
  if i[0] == 'NAME': # First data item explains structure instead of holding data.
    continue
  if sys.argv[1] == i[0]:
    user_state_code = i[1]
    valid_state_flag = True
    break

if valid_state_flag == False:
  print(f"usage: {sys.argv[0]} state county");
  sys.exit()
#print(user_state_code)


counties_reference_query = f"https://api.census.gov/data/2023/acs/acs5?get=NAME&for=county:*&in=state:{user_state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"

valid_counties = json.loads(requests.get(counties_reference_query).text)
#print(valid_counties)

valid_county_flag = False
for i in valid_counties:
  # i structure: [County Name, State Code, County Code]
  #print(i)
  if i[0] == 'NAME': # First data item explains structure instead of holding data.
    continue
  if (sys.argv[2] + ", " + sys.argv[1]) == i[0]:
    user_county_code = i[2]
    valid_county_flag = True
    break

#print(valid_county_flag)
if valid_county_flag == False:
  print(f"usage: {sys.argv[0]} state county");
  sys.exit()
#print(user_county_code)

## Collect Tables/Variables From File ##

try:
  variables = json.loads(open("Census_Data_To_GeoParquet_Variables", "rt").read())
except:
  print("Census_Data_To_GeoParquet_Variables file does not exist.")
  sys.exit()
#print(variables)


## Call APIs and Merge Responses on GEO_ID

variables_sorted_by_geo_id = {}
sorted_variables_keys = variables_sorted_by_geo_id.keys()
# nested dictionary
# {geo_id_1: {variable 1: value 1, ..., variable n, value n}, ..., geo_id_n {...}}
individual_variables = []
# list of strings, maximum of 50 variables per string

if len(variables[0]) != 1: # skip if no tables to pull
  for i in variables[0]:
    # variables[0] parsed structure: ['Tables', 'Table 1', ..., 'Table n']
    if i == 'Tables':
      continue
    else:
      block_group_data_query = f"https://api.census.gov/data/2023/acs/acs5?get=group({i})&for=block%20group&in=state:{user_state_code}%20county:{user_county_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
      census_table_data = json.loads(requests.get(block_group_data_query).text)
      #print(census_table_data)
      #print() # these two print statements are for making space between tables
      #print()
      variable_names = census_table_data[0]
      for j in range(0, 6):
        # take out the stuff after the variable names
        variable_names.pop()
      #print(variable_names)
      for j in range(1, len(census_table_data)):
        # j structure: ["variable 1", ..., "variable n", "geo id", "NAME", "state", "county", "tract", "block group"]
        #print(census_table_data[j][-6][9:]) # geo id, [9:] is for chopping off the 1500000US that the census data starts geo ids with but the map data doesn't
        if census_table_data[j][-6][9:] not in sorted_variables_keys:
          variables_sorted_by_geo_id[census_table_data[j][-6][9:]] = {}
          for k in range(0, len(variable_names)):
            variables_sorted_by_geo_id[census_table_data[j][-6][9:]][variable_names[k]] = census_table_data[j][k]
        else:
          for k in range(0, len(variable_names)):
            variables_sorted_by_geo_id[census_table_data[j][-6][9:]][variable_names[k]] = census_table_data[j][k]

if len(variables[1]) != 1: # skip if no individual variables to pull
  string_of_variables = ""
  variable_counter = 0
  for i in range(1, len(variables[1])): # skip variables[1][0] 'Individual Variables'
    # variables[1] parsed structure: ['Individual Variables', 'Variable 1', ..., 'Variable n']
    if variable_counter == 49:
      individual_variables.append(string_of_variables)
      string_of_variables = ""
      variable_counter = 0
    if variable_counter == 0: 
      string_of_variables = string_of_variables + f"{variables[1][i]}"
      variable_counter = variable_counter + 1
    else:
      string_of_variables = string_of_variables + f",{variables[1][i]}"
      variable_counter = variable_counter + 1
  individual_variables.append(string_of_variables)
  #print(individual_variables)

  for i in range(0, len(individual_variables)):
  # i structure: 'Variable 1,...,Variable 50'
    block_group_data_query = f"https://api.census.gov/data/2023/acs/acs5?get={individual_variables[i]}&for=block%20group&in=state:{user_state_code}%20county:{user_county_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
    census_data = json.loads(requests.get(block_group_data_query).text)
    #print(census_data)
    variable_names = census_data[0]
    #print(variable_names)
    for j in range(1, len(census_data)):
      # j structure: ["variable 1", ..., "variable n", "state", "county", "tract", "block group"]
      geo_id = census_data[j][-4] + census_data[j][-3] + census_data[j][-2] + census_data[j][-1]
      #print(geo_id)
      if geo_id not in sorted_variables_keys:
          variables_sorted_by_geo_id[geo_id] = {}
          for k in range(0, len(variable_names)):
            variables_sorted_by_geo_id[geo_id][variable_names[k]] = census_data[j][k]
      else:
        for k in range(0, len(variable_names)):
          variables_sorted_by_geo_id[geo_id][variable_names[k]] = census_data[j][k]

#print(variables_sorted_by_geo_id)
#for i in variables_sorted_by_geo_id:
  #print(variables_sorted_by_geo_id[i])

block_group_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer/10/query?where=(COUNTY=%27{user_county_code}%27%20AND%20STATE=%20%27{user_state_code}%27)&outFields=*&f=geojson"

census_map_data = json.loads(requests.get(block_group_map_query).text)
#print(census_map_data)

records = []
for feature in census_map_data["features"]:
  geom = shape(feature["geometry"]) #parse GeoJSON geometry
  props = feature.get("properties", {}) #whatever is already on the feature
  #props['GEOID']
  record = {
    "geometry": geom,
    **props,
  }
  #print(variables_sorted_by_geo_id[props['GEOID']])
  for j in variables_sorted_by_geo_id[props['GEOID']]:
    #print(j)
    #print(variables_sorted_by_geo_id[props['GEOID']][j])
    record[j] = variables_sorted_by_geo_id[props['GEOID']][j]

  records.append(record)

gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
output_file_name = f"{sys.argv[2]} {sys.argv[1]}.geoparquet"
gdf.to_parquet(output_file_name.replace(' ', '_'))
