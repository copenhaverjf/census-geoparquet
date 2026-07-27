# File: Census_Data_To_GeoParquet_Script.py
# Author: Logan Marko
# Description: Using the Census Data API and the Census TIGERweb GeoServices Rest API, 
#              this python script takes a county, place, zip code tabulation area, state, 
#              vintage, and survey (ACS 5-Year or Decennial Census) and outputs a 
#              GeoParquet file that contains the results for the variables in the 
#              Census_Data_To_GeoParquet_ACS_5_Tables file or the 
#              Census_Data_To_GeoParquet_Decennial_Tables file  in the chosen geographies.
#
# Notes: The script is called like this: 
#        run_python location_type location state vintage survey
#        location_type can be County, Place, or Zip Code
#
#        The place map data appears to return an empty feature collection, besides this
#        places should be supported.
#
#        The scaffolding is in place for adding decennial census survey suport later.

import json
import os
import sys

import geopandas as gpd
import requests
from shapely.geometry import shape



## User Input Validation ##

if len(sys.argv) != 6:
  print(f"usage: {sys.argv[0]} location_type location state vintage survey")
  sys.exit()

# What and when is being measured.
acs_5_year = False
decennial_census = False
vintage = 0
decennial_vintage = 0

# Where is being measured.
state_code = ""
county_code = ""
place_code = ""
zcta_ucgid = ""


match sys.argv[5]:
  case "ACS 5-Year":
    acs_5_year = True
  case "Decennial Census":
    decennial_census = True
  case _:
    print(f"usage: {sys.argv[0]} location_type location state vintage survey")
    print("survey options: \"ACS 5-Year\" or \"Decennial Census\"")
    sys.exit()

if not sys.argv[4].isdecimal():
  print(f"usage: {sys.argv[0]} location_type location vintage survey")
  print("vintage should be a year, for example, \"2023\"")
  sys.exit()
vintage = sys.argv[4]

if int(vintage) >= 2010 and int(vintage) <= 2019:
  decennial_vintage = "2010"
elif int(vintage) >= 2020 and int(vintage) <= 2029:
  decennial_vintage = "2020"
#print(f"decennial_vintage is: {decennial_vintage}")

if acs_5_year:
  states_reference_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=NAME&for=state:*&key={os.environ['CENSUS_DATA_API_KEY']}"
elif decennial_census:
  states_reference_query = f"https://api.census.gov/data/{decennial_vintage}/dec/dhc?get=NAME&for=state:*&key={os.environ['CENSUS_DATA_API_KEY']}"

valid_states = json.loads(requests.get(states_reference_query).text)
#print(valid_states)
for i in range(1, len(valid_states)):
  # valid_states[i] structure: [State Name, State Code]
  #print(f"valid_states[{i]}) is: {valid_states[i]}")
  if sys.argv[3] == valid_states[i][0]:
    state_code = valid_states[i][1]
    break
#print(f"state_code is: {state_code}")
if state_code == "":
  print(f"usage: {sys.argv[0]} location_type location state vintage survey")
  print("state was not valid")
  sys.exit()

if acs_5_year:
  counties_reference_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=NAME&for=county:*&in=state:{state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
  places_reference_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=NAME&for=place:*&in=state:{state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
  zcta_reference_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=NAME&ucgid=pseudo(0400000US{state_code}$8600000)&key={os.environ['CENSUS_DATA_API_KEY']}"
elif decennial_census:
  counties_reference_query = f"https://api.census.gov/data/{decennial_vintage}/dec/dhc?get=NAME&for=county:*&in=state:{state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
  places_reference_query = f"https://api.census.gov/data/{decennial_vintage}/dec/dhc?get=NAME&for=place:*&in=state:{state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
  zcta_reference_query = f"https://api.census.gov/data/{decennial_vintage}/dec/dhc?get=NAME&ucgid=pseudo(0400000US{state_code}$8600000)&key={os.environ['CENSUS_DATA_API_KEY']}"

match sys.argv[1]:
  case "County":
    valid_counties = json.loads(requests.get(counties_reference_query).text)
    #print(valid_counties)
    for i in range(1, len(valid_counties)):
      # valid_counties[i] structure: [County Name, State Code, County Code]
      #print(f"valid_counties[{i}] is: {valid_counties[i]}")
      if (sys.argv[2] + ", " +  sys.argv[3]) == valid_counties[i][0]:
        county_code = valid_counties[i][2]
        break
    if county_code == "":
      print(f"usage: {sys.argv[0]} location_type location state vintage survey")
      print("county was not valid")
      sys.exit()
    #print(f"county_code is: {county_code}")
  case "Place":
    valid_places = json.loads(requests.get(places_reference_query).text)
    #print(valid_places)
    for i in range(1, len(valid_places)):
      # valid_counties[i] structure: [Place Name, State Code, Place Code]
      #print(f"valid_places[{i}] is: {valid_places[i]}")
      if (sys.argv[2] + ", " +  sys.argv[3]) == valid_places[i][0]:
        place_code = valid_places[i][2]
        break
    if place_code == "":
      print(f"usage: {sys.argv[0]} location_type location state vintage survey")
      print("place was not valid")
      sys.exit()
    #print(f"place is: {place}")
    #print(f"place_code is: {place_code}")
  case "Zip Code":
    valid_zctas = json.loads(requests.get(zcta_reference_query).text)
    #print(valid_zctas)
    for i in range(1, len(valid_zctas)):
      # valid_zctas[i] structure: ['ZCTA Name", 'ucgid']
      #print(f"valid_zctas[{i}] is: valid_zctas[i]")
      if ("ZCTA5 " + sys.argv[2]) == valid_zctas[i][0]:
        zcta_ucgid = valid_zctas[i][1]
        break
    if zcta_ucgid == "":
      print(f"usage: {sys.argv[0]} location_type location state vintage survey")
      print("If you typed a valid zip code, it does not resolve to a zip code tabulation area for the selected vintage and survey")
      sys.exit()
    #print(f"zcta_ucgid is: {zcta_ucgid}")
  case _:
    print(f"usage: {sys.argv[0]} location_type location state vintage survey")
    print("location_type was incorrect: currently \"County\", \"Place\", and \"Zip Code\" are supported")
    sys.exit()



## Collect Data Tables From File For Chosen Survey ##

if acs_5_year:
  try:
    acs_tables = json.loads(open("Census_Data_To_GeoParquet_ACS_5_Year_Tables", "rt").read())
  except:
    print("Census_Data_To_GeoParquet_ACS_5_Year_Tables file does not exist or is incorrectly formatted.")
    sys.exit()
elif decennial_census:
  try:
    dec_tables = json.loads(open("Census_Data_To_GeoParquet_Decennial_Tables", "rt").read())
  except:
    print("Census_Data_To_GeoParquet_Decennial_Tables file does not exist or is incorrectly formatted.")
    sys.exit()


## Collect Census Data from the Census Data API  ##

bgrp_geo_ids = {} # nested dictionary for block group data
# {geo_id_1: {variable 1: value 1,..., variable n: value n},..., geo_id_n {...}}
bgrp_keys = bgrp_geo_ids.keys()
tract_geo_ids = {} # similar to bgrp_geo_ids but for tract level data
tract_keys = tract_geo_ids.keys()
place_geo_ids = {} # similar to bgrp_geo_ids but for place data
place_keys = place_geo_ids.keys()
zcta_geo_ids = {} # similar to bgrp_geo_ids but for zcta data
zcta_keys = zcta_geo_ids.keys()

tract_variables = []
# unsorted, holds all variables kicked up to tract resolution, gets sorted into tract_strings
tract_strings = []
# list of strings for the Census Data API get function containing tract level variable names
# The Census Data API allows a maximum of 50 variables per call.
tract_string = ""
tract_var_count = 0

if acs_5_year:
  match sys.argv[1]:
    case "County":
      ## Detailed Tables ##

      #print(acs_tables)
      for i in range(1, len(acs_tables[0])): # skip over 'Detailed Tables' # for each table
        #acs_tables[0] structure: ['Tables', 'Table 1',...,'Table n']
        #print(f"acs_tables[0][{i}] is: {acs_tables[0][i]}")
        detailed_bgrp_data_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=group({acs_tables[0][i]})&for=block%20group:*&in=state:{state_code}%20county:{county_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
        bgrp_table = json.loads(requests.get(detailed_bgrp_data_query).text)
        #print(bgrp_table)
        #print(bgrp_table[0]) # holds the structure of the table
        for j in range(1, len(bgrp_table)): # for each block group
          # bgrp_table[j] structure: ['Variable 1',..., 'Variable n', 'GEO_ID', 'NAME', "state', 'county', 'tract', 'block group']
          #print(f"bgrp_table[{j}] is: {bgrp_table[j]}")
          #print(f"bgrp_table[{j}][-6][9:] is: {bgrp_table[j][-6][9:]}") # geo id
          if bgrp_table[j][-6][9:] not in bgrp_keys:
            bgrp_geo_ids[bgrp_table[j][-6][9:]] = {}
            # [9:] is for chopping off the beginning of the census data geo ids have that the map data does not have.

          name_flag = False
          k = 0
          while k < (len(bgrp_table[0]) - 6): # everything after the variables, besides NAME, are not neded, the map data already has it
            #print(f"bgrp_table[{j}][{k}] is: {bgrp_table[j][k]}") # estimate/margin of error
            #print(f"bgrp_table[{j}][{k+1}] is: {bgrp_table[j][k+1]}") # the annotation flag for the estimate/margin of error
            match bgrp_table[j][k+1]:
              case "-" | "N" | "(X)" | "**" | "***":
                if bgrp_table[0][k] not in tract_variables:
                  tract_variables.append(grp_table[0][k])
                if bgrp_table[0][k+1] not in tract_variables:
                  tract_variables.append(bgrp_table[0][k+1])
              case None:
                if bgrp_table[j][k] != None:
                  bgrp_geo_ids[bgrp_table[j][-6][9:]][bgrp_table[0][k]] = bgrp_table[j][k]
                  bgrp_geo_ids[bgrp_table[j][-6][9:]][bgrp_table[0][k+1]] = bgrp_table[j][k+1]
                  if not name_flag:
                    bgrp_geo_ids[bgrp_table[j][-6][9:]][bgrp_table[0][-5]] = bgrp_table[j][-5] 
                    # fetch the name, this one is more detailed than the one in the map data
                    name_flag = True
                else:
                  if bgrp_table[0][k] not in tract_variables:
                    tract_variables.append(bgrp_table[0][k])
                  if bgrp_table[0][k+1] not in tract_variables:
                    tract_variables.append(bgrp_table[0][k+1])
              case _:
                bgrp_geo_ids[bgrp_table[j][-6][9:]][bgrp_table[0][k]] = bgrp_table[j][k]
                bgrp_geo_ids[bgrp_table[j][-6][9:]][bgrp_table[0][k+1]] = bgrp_table[j][k+1]
                if not name_flag:
                  bgrp_geo_ids[bgrp_table[j][-6][9:]][bgrp_table[0][-5]] = bgrp_table[j][-5] 
                  # fetch the name, this one is more detailed than the one in the map data
                  name_flag = True
            k = k + 2
          #print()
      empty_bgrp_geo_ids = [] # variables that get kicked up leave empty bgrp_geo_ids dictionaries behind
      for i in bgrp_geo_ids:
        if bgrp_geo_ids[i] == {}:
          empty_bgrp_geo_ids.append(i)
      for i in range(0, len(empty_bgrp_geo_ids)):
          bgrp_geo_ids.pop(empty_bgrp_geo_ids[i])
      #print(bgrp_geo_ids)
      #print()
      #print(tract_variables)
      for i in range(0, len(tract_variables)): # for each census tract level variable
      # max of 50 variables in a tract_string as per Census Data API limits
        if tract_var_count == 48: # 48 instead of 49 to include NAME, NAME is variable 49 (counting from 0)
          tract_string = tract_string + f",NAME"
          tract_strings.append(tract_string)
          tract_string = ""
          tract_var_count = 0
        if tract_var_count == 0:
          tract_string = tract_string + f"{tract_variables[i]}"
        else:
          tract_string = tract_string + f",{tract_variables[i]}"
        tract_var_count = tract_var_count + 1
      if len(tract_variables) != 0: # the next loop won't run if there are no tract_strings
        tract_strings.append(tract_string)
      #print(tract_strings)
      for i in range(0, len(tract_strings)): # for each tract string
        detailed_tract_data_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get={tract_strings[i]}&for=tract:*&in=state:{state_code}%20county:{county_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
        #print(detailed_tract_data_query)
        tract_data = json.loads(requests.get(detailed_tract_data_query).text)
        #print(tract_data)
        tract_variables = tract_data[0]
        #print(tract_variables)
        for j in range(1, len(tract_data)):
          # tract_data[j] structure: ["Variable 1",...,"Variable n", state, county, tract]
          geo_id = tract_data[j][-3] + tract_data[j][-2] + tract_data[j][-1]
          if geo_id not in tract_keys:
            tract_geo_ids[geo_id] = {}
          for k in range(0, len(tract_variables) - 3): # do not need state, county, tract
            tract_geo_ids[geo_id][tract_variables[k]] = tract_data[j][k]

      ## Subject Tables ##

      for i in range(1, len(acs_tables[1])): # skip over 'Subject Tables'
        #print(acs_tables[1][i])
        subject_tract_query = f"https://api.census.gov/data/{vintage}/acs/acs5/subject?get=group({acs_tables[1][i]})&for=tract:*&in=state:{state_code}%20county:{county_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
        tract_data = json.loads(requests.get(subject_tract_query).text)
        for j in range(1, len(tract_data)):
          # tract_data[j] structure: ["GEO_ID", "NAME", "Variable 1",...,"Variable n", "state", "county", "tract"]
          geo_id = tract_data[j][0][9:]
          #  [9:] is for chopping off the beginning of the census data geo ids that the map data does not have.
          #print(geo_id is: {geo_id})
          if geo_id not in tract_keys:
            tract_geo_ids[geo_id] = {}
          for k in range(1, len(tract_data[0]) - 3): # do not need state, county, tract
            tract_geo_ids[geo_id][tract_data[0][k]] = tract_data[j][k]
      #print(tract_geo_ids)
    case "Place":
      ## Detailed Tables ##

      for i in range(1, len(acs_tables[0])):
        detailed_place_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=group({acs_tables[0][i]})&for=place:{place_code}&in=state:{state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
        #print(place_query)
        place_table = json.loads(requests.get(detailed_place_query).text)
        # place_table_data[ ] structure: ["Variable 1",...,"Variable n", "geo_id", "name", "state", "place"]
        # There are only two lists: the variable names and the values for that place.
        #print(place_table)
        #print() # make space between tables when debugging
        #print()
        #print(f"place_table[1][-4][9:] is: {place_table[1][-4][9:]}")
        geo_id = place_table[1][-4][9:]
        # [9:] is for chopping off the beginning that the census data starts geo ids with but the map data doesn't
        place_variables = place_table[0]
        if geo_id not in place_keys:
          place_geo_ids[geo_id] = {}
        for j in range(0, len(place_variables) - 4): # everything after the variables is in the map data
          place_geo_ids[geo_id][place_table[0][j]] = place_table[1][j]
        place_geo_ids[place_table[1][-4][9:]][place_table[0][-3]] = place_table[1][-3]
        # fetch the name, this one is more detailed than the one in the map data

      ## Subject Tables ##

      for i in range(1, len(acs_tables[1])): # skip over 'Subject Tables'
        #print(acs_tables[1][i])
        place_subject_query = f"https://api.census.gov/data/{vintage}/acs/acs5/subject?get=group({acs_tables[1][i]})&for=place:{place_code}&in=state:{state_code}&key={os.environ['CENSUS_DATA_API_KEY']}"
        place_data = json.loads(requests.get(place_subject_query).text)
        for j in range(1, len(place_data)):
          # tract_data[j] structure: ["GEO_ID", "NAME", "Variable 1",...,"Variable n", "state", "place"]
          geo_id = place_data[j][0][9:]
          #  [9:] is for chopping off the beginning of the census data geo ids that the map data does not have.
          #print(geo_id)
          if geo_id not in place_keys:
            place_geo_ids[geo_id] = {}
          for k in range(1, len(place_data[0]) - 2): # do not need state, place
            place_geo_ids[geo_id][place_data[0][k]] = place_data[j][k]
      #print(place_geo_ids)
    case "Zip Code":
      ## Detailed Tables ##

      for i in range(1, len(acs_tables[0])):
        detailed_zcta_query = f"https://api.census.gov/data/{vintage}/acs/acs5?get=group({acs_tables[0][i]})&ucgid={zcta_ucgid}&key={os.environ['CENSUS_DATA_API_KEY']}"
        #print(detailed_zcta_query)
        zcta_table = json.loads(requests.get(detailed_zcta_query).text)
        # zcta_table_data[ ] structure: ["Variable 1",...,"Variable n", "geo_id", "name", "ucgid"]
        # There are only two lists: the variable names and the values for that zcta.
        #print(zcta_table)
        #print() # make space between tables when debugging
        #print()
        #print(f"zcta_table[1][-3][9:] is: {zcta_table[1][-3][9:]}")
        geo_id = zcta_table[1][-3][9:]
        # [9:] is for chopping off the beginning that the census data starts geo ids with but the map data doesn't
        zcta_variables = zcta_table[0]
        if geo_id not in zcta_keys:
          zcta_geo_ids[geo_id] = {}
        for j in range(0, len(zcta_variables) - 3): # everything after the variables is in the map data
          zcta_geo_ids[geo_id][zcta_table[0][j]] = zcta_table[1][j]
        zcta_geo_ids[zcta_table[1][-3][9:]][zcta_table[0][-2]] = zcta_table[1][-2] 
        # fetch the name, this one is more detailed than the one in the map data

      ## Subject Tables ##

      for i in range(1, len(acs_tables[1])): # skip over 'Subject Tables'
        #print(acs_tables[1][{i}] is: {acs_tables[1][i]})
        subject_zcta_query = f"https://api.census.gov/data/{vintage}/acs/acs5/subject?get=group({acs_tables[1][i]})&ucgid={zcta_ucgid}&key={os.environ['CENSUS_DATA_API_KEY']}"
        zcta_data = json.loads(requests.get(subject_zcta_query).text)
        for j in range(1, len(zcta_data)):
          # zcta_data[j] structure: ["GEO_ID", "NAME", "Variable 1",...,"Variable n", "ucgid"]
          geo_id = zcta_data[j][0][9:]
          #  [9:] is for chopping off the beginning of the census data geo ids that the map data does not have.
          #print(f"geo_id is: {geo_id}")
          if geo_id not in zcta_keys:
            zcta_geo_ids[geo_id] = {}
          for k in range(1, len(zcta_data[0]) - 1): # do not need ucgid
            zcta_geo_ids[geo_id][zcta_data[0][k]] = zcta_data[j][k]
      #print(zcta_geo_ids)
#elif decennial_census:

## Colect Map Data From the Census TIGERweb GeoServices Rest API ##

if acs_5_year:
  match sys.argv[1]:
    case "County":
      match vintage:
        case "2021" | "2022":
          bgrp_layer = 8
        case "2012" | "2013" | "2014" | "2015" | "2016" | "2017" | "2018" | "2019" | "2023" | "2024" | "2025" :
          bgrp_layer = 10
        case _:
          print(f"{sys.argv[5]} block group map data does not exist for {vintage}")
          sys.exit()
      bgrp_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{bgrp_layer}/query?where=(COUNTY=%27{county_code}%27%20AND%20STATE=%20%27{state_code}%27)&outFields=*&f=geojson"
      #print(block_group_map_query)
      match vintage:
        case "2021" | "2022":
          tract_layer = "6"
        case "2012" | "2013" | "2014" | "2015" | "2016" | "2017" | "2018" | "2019" | "2023" | "2024" | "2025":
          tract_layer = "8"
        case _:
          print(f"{sys.argv[5]} tract map data does not exist for {vintage}")
          sys.exit()
      tract_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{tract_layer}/query?where=(COUNTY=%27{county_code}%27%20AND%20STATE=%20%27{state_code}%27)&outFields=*&f=geojson"
      #print(tract_map_query)
      bgrp_map = json.loads(requests.get(bgrp_map_query).text)
      tract_map = json.loads(requests.get(tract_map_query).text)
    case "Place": 
      match vintage:
        case "2021" | "2022":
          place_layer = "26"
        case "2012" | "2013" | "2014" | "2015" | "2016" | "2017" | "2018" | "2019":
          place_layer = "28"
        case "2023" | "2024" | "2025":
          place_layer = "30"
        case _:
          print(f"{sys.argv[5]} place map data does not exist for {vintage}")
          sys.exit()
      place_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{place_layer}/query?where=(PLACE=%27{place_code}%27%20AND%20STATE=%20%27{state_code}%27)&outFields=*&f=geojson"
      #print(place_map_query)
      #place_map = json.loads(requests.get(place_map_query).text)
      #print(place_map)
    case "Zip Code":
      match vintage:
        case "2021" | "2022":
          zcta_layer = "0"
        case "2012" | "2013" | "2014" | "2015" | "2016" | "2017" | "2018" | "2019" | "2023" | "2024" | "2025":
          zcta_layer = "2"
        case _:
          print(f"{sys.argv[5]} map data does not exist for {vintage}")
          sys.exit()
      zcta_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{zcta_layer}/query?where=ZCTA5=%27{sys.argv[2]}%27&outFields=*&f=geojson"
      #print(zcta_map_query)
      zcta_map = json.loads(requests.get(zcta_map_query).text)
      #print(zcta_map)
#elif decennial_census:

if acs_5_year:
  records = []
  match sys.argv[1]:
    case "County":
      if len(bgrp_keys) != 0:
        for feature in bgrp_map["features"]:
          geom = shape(feature["geometry"]) #parse GeoJSON geometry
          props = feature.get("properties", {}) #whatever is already on the feature
          #print(props)
          #props['GEOID']
          record = {
            "geometry": geom,
            **props,
          }
          #print(f"props['GEOID'] is: {props['GEOID']}")
          record["source"] = "acs5"
          record["vintage"] = int(vintage)
          record["geo_name"] = sys.argv[2]
          record["geo_level"] = "block_group"
          for j in bgrp_geo_ids[props['GEOID']]:
            record[j] = (bgrp_geo_ids[props['GEOID']][j])
          records.append(record)
      if len(tract_keys) != 0:
        for feature in tract_map["features"]:
          geom = shape(feature["geometry"]) #parse GeoJSON geometry
          props = feature.get("properties", {}) #whatever is already on the feature
          #print(props)
          #props['GEOID']
          record = {
            "geometry": geom,
            **props,
          }
          #print(f"props['GEOID'] is: {props['GEOID']}")
          record["source"] = "acs5"
          record["vintage"] = int(vintage)
          record["geo_name"] = sys.argv[2]
          record["geo_level"] = "tract"
          for j in tract_geo_ids[props['GEOID']]:
            record[j] = (tract_geo_ids[props['GEOID']][j])
          records.append(record)
      gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
      output_file_name = f"{sys.argv[2]} {sys.argv[3]} {sys.argv[4]} {sys.argv[5]}.geoparquet"
      gdf.to_parquet(output_file_name.replace(' ', '_').replace('-', '_'))
    #case "Place":
      #for feature in place_map["features"]:
        #geom = shape(feature["geometry"]) #parse GeoJSON geometry
        #props = feature.get("properties", {}) #whatever is already on the feature
        #print(props)
        #props['GEOID']
        #record = {
          #"geometry": geom,
          #**props,
        #}
        #record["source"] = "acs5"
        #record["vintage"] = int(vintage)
        #record["geo_name"] = sys.argv[2]
        #record["geo_level"] = "place"
        #print(f"props['GEOID'] is: {props['GEOID']}")
        #for j in place_geo_ids[props['GEOID']]:
          #record[j] = (place_geo_ids[props['GEOID']][j])
          #records.append(record)
      #gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
      #output_file_name = f"{sys.argv[2]} {sys.argv[3]} {sys.argv[4]} {sys.argv[5]}.geoparquet"
      #gdf.to_parquet(output_file_name.replace(' ', '_').replace('-', '_'))
    case "Zip Code":
      for feature in zcta_map["features"]:
        geom = shape(feature["geometry"]) #parse GeoJSON geometry
        props = feature.get("properties", {}) #whatever is already on the feature
        #print(props)
        #props['GEOID']
        record = {
          "geometry": geom,
          **props,
        }
        record["source"] = "acs5"
        record["vintage"] = int(vintage)
        record["geo_name"] = sys.argv[2]
        record["geo_level"] = "zcta"
        #print(f"props['GEOID'] is: {props['GEOID']}")
        for j in zcta_geo_ids[props['GEOID']]:
          record[j] = (zcta_geo_ids[props['GEOID']][j])
          records.append(record)
      gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
      output_file_name = f"{sys.argv[2]} {sys.argv[3]} {sys.argv[4]} {sys.argv[5]}.geoparquet"
      gdf.to_parquet(output_file_name.replace(' ', '_').replace('-', '_'))

#elif decennial_census:
