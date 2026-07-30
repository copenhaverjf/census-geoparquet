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
#        Run "run_python help" for the list of help commands, which print the valid
#        states, counties, places, zip code tabulation areas and vintages.
#
#        The place map data appears to return an empty feature collection, besides this
#        places should be supported.
#
#        The scaffolding is in place for adding decennial census survey suport later.
#
#        A set of mandatory detailed tables is merged into whatever is listed in the
#        tables file. Those tables back the recoded columns, so the tables file
#        controls extras only and cannot accidentally drop something a recode needs.
#
#        Variables the Census does not publish at the block group level get kicked up
#        to the tract, then copied back down onto every block group inside that tract.
#        No tract geometry is stored. A block group geo id is twelve characters and its
#        first eleven are the tract it sits in, so the copy down needs no crosswalk.
#        The copied down raw columns carry a tract_ prefix because every block group in
#        a tract receives the same value, which is coarser than it looks.

import json
import os
import sys

import geopandas as gpd
import requests
from shapely.geometry import shape



## Help ##

# The vintages the TIGERweb layer match statements further down know about.
# Keep this in sync with those match statements if a new vintage is added.
supported_vintages = ["2012", "2013", "2014", "2015", "2016", "2017", "2018",
                      "2019", "2021", "2022", "2023", "2024"]

# Any recent vintage resolves names to codes for the help listings. The lists
# barely change between vintages, so this does not have to match the vintage
# being pulled.
help_lookup_vintage = "2023"

def print_in_columns(items, column_width, columns):
  # The place and zip code lists run to hundreds of entries, so they are printed
  # across the terminal instead of one per line.
  line = ""
  count = 0
  for i in range(0, len(items)):
    line = line + items[i].ljust(column_width)
    count = count + 1
    if count == columns:
      print(line.rstrip())
      line = ""
      count = 0
  if line != "":
    print(line.rstrip())

def help_state_code(state_name):
  # Turns a state name into its two digit code, or returns "" if it is not valid.
  query = f"https://api.census.gov/data/{help_lookup_vintage}/acs/acs5?get=NAME&for=state:*&key={os.environ['CENSUS_DATA_API_KEY']}"
  states = json.loads(requests.get(query).text)
  for i in range(1, len(states)):
    # states[i] structure: [State Name, State Code]
    if state_name == states[i][0]:
      return states[i][1]
  return ""

def print_help_commands():
  print(f"usage: {sys.argv[0]} location_type location state vintage survey")
  print()
  print("  location_type   \"County\", \"Place\", or \"Zip Code\"")
  print("  location        the county name, the place name, or the five digit zip code")
  print("  state           the full state name, for example \"Pennsylvania\"")
  print("  vintage         a four digit year, for example \"2024\"")
  print("  survey          \"ACS 5-Year\" or \"Decennial Census\"")
  print()
  print("help commands:")
  print(f"  {sys.argv[0]} help                     this message")
  print(f"  {sys.argv[0]} help state               every state name the API accepts")
  print(f"  {sys.argv[0]} help county <state>      every county in a state")
  print(f"  {sys.argv[0]} help place <state>       every census designated place in a state")
  print(f"  {sys.argv[0]} help zip <state>         every zip code tabulation area in a state")
  print(f"  {sys.argv[0]} help vintage             the vintages this script has map layers for")
  print()
  print("examples:")
  print(f"  {sys.argv[0]} County \"Montgomery County\" \"Pennsylvania\" 2024 \"ACS 5-Year\"")
  print("    writes Montgomery_County_Pennsylvania_2024_ACS_5_Year.geoparquet")
  print("    one row per block group, polygon geometry")
  print()
  print(f"  {sys.argv[0]} Place \"North Wales borough\" \"Pennsylvania\" 2024 \"ACS 5-Year\"")
  print("    writes North_Wales_borough_Pennsylvania_2024_ACS_5_Year.geoparquet")
  print("    one row for the place, polygon geometry")
  print()
  print(f"  {sys.argv[0]} \"Zip Code\" 19454 \"Pennsylvania\" 2024 \"ACS 5-Year\"")
  print("    writes 19454_Pennsylvania_2024_ACS_5_Year.geoparquet")
  print("    one row for the zip code tabulation area, polygon geometry")
  print()
  print("the output file name is the location, state, vintage and survey joined by")
  print("underscores, with spaces and hyphens replaced by underscores")

if len(sys.argv) >= 2 and sys.argv[1].lower() == "help":
  if len(sys.argv) == 2:
    print_help_commands()
    sys.exit()

  match sys.argv[2].lower():
    case "state":
      states_query = f"https://api.census.gov/data/{help_lookup_vintage}/acs/acs5?get=NAME&for=state:*&key={os.environ['CENSUS_DATA_API_KEY']}"
      valid_states = json.loads(requests.get(states_query).text)
      state_names = []
      for i in range(1, len(valid_states)):
        # valid_states[i] structure: [State Name, State Code]
        state_names.append(valid_states[i][0])
      state_names.sort()
      print(f"{len(state_names)} states, pass the name exactly as printed:")
      print()
      print_in_columns(state_names, 26, 3)
      sys.exit()

    case "vintage":
      print("vintages with TIGERweb map layers in this script:")
      print()
      print_in_columns(supported_vintages, 8, 8)
      print()
      print("2020 is missing. The ACS 2016-2020 5-Year estimates were published, but")
      print("the block group and tract layer numbers for tigerWMS_ACS2020 are not in")
      print("the match statements below, so add them before pulling that vintage.")
      print()
      print("LODES runs about a year behind the ACS, so an ACS 2024 file pairs with a")
      print("LODES 2023 file.")
      sys.exit()

    case "county" | "place" | "zip":
      if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} help {sys.argv[2].lower()} <state>")
        print(f"for example: {sys.argv[0]} help {sys.argv[2].lower()} \"Pennsylvania\"")
        sys.exit()

      help_state = sys.argv[3]
      code = help_state_code(help_state)
      if code == "":
        print(f"\"{help_state}\" is not a valid state name.")
        print(f"run \"{sys.argv[0]} help state\" for the list.")
        sys.exit()

      match sys.argv[2].lower():
        case "county":
          query = f"https://api.census.gov/data/{help_lookup_vintage}/acs/acs5?get=NAME&for=county:*&in=state:{code}&key={os.environ['CENSUS_DATA_API_KEY']}"
          rows = json.loads(requests.get(query).text)
          names = []
          for i in range(1, len(rows)):
            # rows[i] structure: [County Name, State Code, County Code]
            # the API returns "Montgomery County, Pennsylvania", the script wants
            # the part before the comma
            names.append(rows[i][0].split(",")[0])
          names.sort()
          print(f"{len(names)} counties in {help_state}:")
          print()
          print_in_columns(names, 30, 3)
          print()
          print(f"example: {sys.argv[0]} County \"{names[0]}\" \"{help_state}\" 2024 \"ACS 5-Year\"")

        case "place":
          query = f"https://api.census.gov/data/{help_lookup_vintage}/acs/acs5?get=NAME&for=place:*&in=state:{code}&key={os.environ['CENSUS_DATA_API_KEY']}"
          rows = json.loads(requests.get(query).text)
          names = []
          for i in range(1, len(rows)):
            # rows[i] structure: [Place Name, State Code, Place Code]
            names.append(rows[i][0].split(",")[0])
          names.sort()
          print(f"{len(names)} places in {help_state}:")
          print()
          print_in_columns(names, 34, 3)
          print()
          print(f"example: {sys.argv[0]} Place \"{names[0]}\" \"{help_state}\" 2024 \"ACS 5-Year\"")

        case "zip":
          query = f"https://api.census.gov/data/{help_lookup_vintage}/acs/acs5?get=NAME&ucgid=pseudo(0400000US{code}$8600000)&key={os.environ['CENSUS_DATA_API_KEY']}"
          rows = json.loads(requests.get(query).text)
          names = []
          for i in range(1, len(rows)):
            # rows[i] structure: ["ZCTA5 00000", ucgid]
            # the script wants just the five digits
            names.append(rows[i][0].replace("ZCTA5 ", ""))
          names.sort()
          print(f"{len(names)} zip code tabulation areas in {help_state}:")
          print()
          print_in_columns(names, 8, 8)
          print()
          print("a zip code with no residents may have no tabulation area for a vintage")
          print(f"example: {sys.argv[0]} \"Zip Code\" {names[0]} \"{help_state}\" 2024 \"ACS 5-Year\"")
      sys.exit()

    case _:
      print(f"\"{sys.argv[2]}\" is not a help command.")
      print()
      print_help_commands()
      sys.exit()



## Mandatory Detailed Tables And Recode Definitions ##

# These tables back the recoded columns below. They are merged into whatever the
# tables file lists, so the file controls extras only. B08301 and B15003 are not
# published at the block group level; the kick up logic further down detects that
# on its own, pulls them at the tract, and the record building copies them back
# down onto every block group in the tract.
mandatory_detailed_tables = ["B01001", "B01003", "B02001", "B03003", "B08301",
                             "B11001", "B15003", "B19001", "B19013", "B19025",
                             "B19301", "B20001"]

# The Census Data API returns everything as strings and uses large negative jam
# values (-666666666, -555555555, -222222222 and friends) to mean things like
# "estimate not available" or "median falls outside the published range".
# Summing those as counts produces silent nonsense.

def to_number(value):
  # Returns an int for a usable value, or None for blanks and jam values.
  if value is None:
    return None
  text = str(value).strip()
  if text == "" or text.upper() in ("NONE", "NULL", "N/A", "(X)", "-"):
    return None
  try:
    number = int(float(text))
  except ValueError:
    return None
  if number < 0: # every jam value the ACS publishes is negative
    return None
  return number

def lookup_variable(variable_dictionary, tract_variable_dictionary, variable_name):
  # Block group value first. If the variable was kicked up to the tract because
  # the Census does not publish it at block group, fall back to the tract value.
  # The tract_ prefixed raw columns on the same row show which variables that
  # happened to.
  if variable_name in variable_dictionary:
    return variable_dictionary[variable_name]
  if tract_variable_dictionary != None and variable_name in tract_variable_dictionary:
    return tract_variable_dictionary[variable_name]
  return None

def sum_variables(variable_dictionary, tract_variable_dictionary, variable_names):
  # Adds up a list of variables. Returns None if any one of them is unusable,
  # because a partial sum of a distribution is worse than no number at all.
  running_total = 0
  for variable_name in variable_names:
    number = to_number(lookup_variable(variable_dictionary,
                                       tract_variable_dictionary, variable_name))
    if number == None:
      return None
    running_total = running_total + number
  return running_total

def sex_by_age_variables(band_numbers):
  # B01001 lists male bands 003 to 025 and repeats the identical female bands at
  # +24, so 003 (male under 5) pairs with 027 (female under 5).
  variable_names = []
  for band_number in band_numbers:
    variable_names.append(f"B01001_{band_number:03d}E")
    variable_names.append(f"B01001_{band_number + 24:03d}E")
  return variable_names

def sex_by_earnings_variables(band_numbers):
  # B20001 lists male bands 003 to 022 and repeats the identical female bands at
  # +21, so 003 (male $1 to $2,499) pairs with 024 (female $1 to $2,499).
  variable_names = []
  for band_number in band_numbers:
    variable_names.append(f"B20001_{band_number:03d}E")
    variable_names.append(f"B20001_{band_number + 21:03d}E")
  return variable_names

# recodes structure: {new column name: [source variable 1,..., source variable n]}
# Every one of these is a count, so they can be summed across geographies when a
# trade area covers more than one. The medians below cannot be.
# The acs_ prefix describes the resident population, to sit opposite the
# columns the LODES script writes for the worker population.
recodes = {

  # Age. LODES buckets workers as 14-29, 30-54 and 55-99, so these are collapsed
  # to match. Under 15 has no worker counterpart and is resident only.
  "acs_age_under_15": sex_by_age_variables([3, 4, 5]),
  "acs_age_15_to_29": sex_by_age_variables([6, 7, 8, 9, 10, 11]),
  "acs_age_30_to_54": sex_by_age_variables([12, 13, 14, 15, 16]),
  "acs_age_55_plus": sex_by_age_variables([17, 18, 19, 20, 21, 22, 23, 24, 25]),

  # Sex.
  "acs_sex_male": ["B01001_002E"],
  "acs_sex_female": ["B01001_026E"],

  # Individual annual earnings. LODES publishes monthly bands of $1,250 or less,
  # $1,251 to $3,333, and above $3,333. Annualized those are $15,000 and $40,000,
  # and the B20001 brackets break on exactly those two numbers.
  "acs_earnings_15k_or_less": sex_by_earnings_variables([3, 4, 5, 6, 7, 8]),
  "acs_earnings_15k_to_40k": sex_by_earnings_variables([9, 10, 11, 12, 13, 14, 15]),
  "acs_earnings_over_40k": sex_by_earnings_variables([16, 17, 18, 19, 20, 21, 22]),

  # Race. B02001 is used rather than B03002 because LODES keeps race and
  # ethnicity as two separate counts instead of crossing them. LODES has no
  # "some other race" code, so that one is resident only.
  "acs_race_white": ["B02001_002E"],
  "acs_race_black": ["B02001_003E"],
  "acs_race_american_indian_alaska_native": ["B02001_004E"],
  "acs_race_asian": ["B02001_005E"],
  "acs_race_native_hawaiian_pacific_islander": ["B02001_006E"],
  "acs_race_some_other_race": ["B02001_007E"],
  "acs_race_two_or_more": ["B02001_008E"],

  # Ethnicity, kept separate from race to match how LODES publishes it.
  "acs_ethnicity_not_hispanic": ["B03003_002E"],
  "acs_ethnicity_hispanic": ["B03003_003E"],

  # Household income. There is deliberately no LODES counterpart. A worker does
  # not have a household at their desk, so household income must never be
  # charted opposite the worker earnings buckets above.
  "acs_household_income_under_25k": ["B19001_002E", "B19001_003E",
                                       "B19001_004E", "B19001_005E"],
  "acs_household_income_25k_to_50k": ["B19001_006E", "B19001_007E",
                                        "B19001_008E", "B19001_009E",
                                        "B19001_010E"],
  "acs_household_income_50k_to_100k": ["B19001_011E", "B19001_012E",
                                         "B19001_013E"],
  "acs_household_income_100k_to_200k": ["B19001_014E", "B19001_015E",
                                          "B19001_016E"],
  "acs_household_income_200k_plus": ["B19001_017E"],

  # Commute and education. At the county level these come from B08301 and
  # B15003, which are not published at block group, so they arrive through the
  # tract copy down and every block group in a tract shares a value. At the place
  # and zip code levels they are published directly.
  "acs_commute_total": ["B08301_001E"],
  "acs_commute_drove_alone": ["B08301_003E"],
  "acs_commute_carpooled": ["B08301_004E"],
  "acs_commute_public_transportation": ["B08301_010E"],
  "acs_commute_walked": ["B08301_019E"],
  "acs_commute_worked_from_home": ["B08301_021E"],
  "acs_education_less_than_high_school": ["B15003_002E", "B15003_003E",
                                            "B15003_004E", "B15003_005E",
                                            "B15003_006E", "B15003_007E",
                                            "B15003_008E", "B15003_009E",
                                            "B15003_010E", "B15003_011E",
                                            "B15003_012E", "B15003_013E",
                                            "B15003_014E", "B15003_015E",
                                            "B15003_016E"],
  "acs_education_high_school": ["B15003_017E", "B15003_018E"],
  "acs_education_some_college": ["B15003_019E", "B15003_020E", "B15003_021E"],
  "acs_education_bachelors_or_higher": ["B15003_022E", "B15003_023E",
                                          "B15003_024E", "B15003_025E"],

  # Headline counts.
  "acs_population": ["B01003_001E"],
  "acs_households": ["B11001_001E"],
  "acs_aggregate_household_income": ["B19025_001E"],
}

# passthrough_recodes structure: {new column name: source variable}
# Copied straight across with jam values cleaned out. These are medians and
# ratios, which means they CANNOT be added together across geographies.
# Aggregate household income above is the one to sum for a trade area.
passthrough_recodes = {
  "acs_median_household_income": "B19013_001E",
  "acs_median_household_income_margin_of_error": "B19013_001M",
  "acs_per_capita_income": "B19301_001E",
  "acs_population_margin_of_error": "B01003_001M",
  "acs_households_margin_of_error": "B11001_001M",
}

def apply_recodes(record, variable_dictionary, tract_variable_dictionary):
  # The raw variables are left exactly as they came back from the API. Everything
  # written here is added on top of them.
  for new_column_name in recodes:
    record[new_column_name] = sum_variables(variable_dictionary,
                                            tract_variable_dictionary,
                                            recodes[new_column_name])
  for new_column_name in passthrough_recodes:
    record[new_column_name] = to_number(
        lookup_variable(variable_dictionary, tract_variable_dictionary,
                        passthrough_recodes[new_column_name]))



## User Input Validation ##

if len(sys.argv) != 6:
  print(f"usage: {sys.argv[0]} location_type location state vintage survey")
  print(f"run \"{sys.argv[0]} help\" for the list of help commands")
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
  print(f"run \"{sys.argv[0]} help state\" for the list")
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
      print(f"run \"{sys.argv[0]} help county \\\"{sys.argv[3]}\\\"\" for the list")
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
      print(f"run \"{sys.argv[0]} help place \\\"{sys.argv[3]}\\\"\" for the list")
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
      print(f"run \"{sys.argv[0]} help zip \\\"{sys.argv[3]}\\\"\" for the list")
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

  ## Merge The Mandatory Tables Into The Tables From The File ##

  # The mandatory tables go first so the recodes always have their inputs. The
  # file's tables are appended after, skipping any that are already mandatory,
  # so listing one twice costs nothing. acs_tables[0] is rebuilt in place, which
  # means every loop below reads the merged list without knowing it changed.
  merged_detailed_tables = [acs_tables[0][0]] # keep the "Detailed Tables" label
  for i in range(0, len(mandatory_detailed_tables)):
    merged_detailed_tables.append(mandatory_detailed_tables[i])
  for i in range(1, len(acs_tables[0])):
    if acs_tables[0][i] not in merged_detailed_tables:
      merged_detailed_tables.append(acs_tables[0][i])
  acs_tables[0] = merged_detailed_tables
  #print(acs_tables[0])

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
                  tract_variables.append(bgrp_table[0][k])
                  # was grp_table, which raised a NameError the first time a
                  # variable was kicked up by an annotation flag
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
        tract_response_variables = tract_data[0]
        #print(tract_response_variables)
        for j in range(1, len(tract_data)):
          # tract_data[j] structure: ["Variable 1",...,"Variable n", state, county, tract]
          geo_id = tract_data[j][-3] + tract_data[j][-2] + tract_data[j][-1]
          if geo_id not in tract_keys:
            tract_geo_ids[geo_id] = {}
          for k in range(0, len(tract_response_variables) - 3): # do not need state, county, tract
            tract_geo_ids[geo_id][tract_response_variables[k]] = tract_data[j][k]

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

# No tract map is fetched. The tract level values are copied down onto the block
# groups that sit inside each tract during record building, so no tract geometry
# is stored and there is only one geometry type in the output file.

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
          print(f"run \"{sys.argv[0]} help vintage\" for the list")
          sys.exit()
      bgrp_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{bgrp_layer}/query?where=(COUNTY=%27{county_code}%27%20AND%20STATE=%20%27{state_code}%27)&outFields=*&f=geojson"
      #print(block_group_map_query)
      bgrp_map = json.loads(requests.get(bgrp_map_query).text)
    case "Place": 
      match vintage:
        case "2021" | "2022":
          place_layer = "26"
        case "2012" | "2013" | "2014" | "2015" | "2016" | "2017" | "2018" | "2019":
          place_layer = "28"
        case "2023" | "2024":
          place_layer = "28"
        case _:
          print(f"{sys.argv[5]} place map data does not exist for {vintage}")
          print(f"run \"{sys.argv[0]} help vintage\" for the list")
          sys.exit()
      place_map_query = f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS{vintage}/MapServer/{place_layer}/query?where=(PLACE=%27{place_code}%27%20AND%20STATE=%20%27{state_code}%27)&outFields=*&f=geojson"
      #print(place_map_query)
      #place_map = json.loads(requests.get(place_map_query).text)
      #print(place_map)
    case "Zip Code":
      match vintage:
        case "2021" | "2022":
          zcta_layer = "0"
        case "2012" | "2013" | "2014" | "2015" | "2016" | "2017" | "2018" | "2019" | "2023" | "2024":
          zcta_layer = "2"
        case _:
          print(f"{sys.argv[5]} map data does not exist for {vintage}")
          print(f"run \"{sys.argv[0]} help vintage\" for the list")
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
          # a block group with every variable kicked up to the tract was popped
          # out of bgrp_geo_ids, so it is not safe to index without checking
          if props['GEOID'] in bgrp_keys:
            for j in bgrp_geo_ids[props['GEOID']]:
              record[j] = (bgrp_geo_ids[props['GEOID']][j])

          ## Copy The Tract Level Values Down ##

          # A block group geo id is twelve characters, STATE(2) COUNTY(3)
          # TRACT(6) BLOCK GROUP(1), and a tract geo id is the first eleven of
          # them. Slicing is the whole join, no crosswalk table and no spatial
          # operation. Every block group in a tract receives the same value,
          # which is why these carry a tract_ prefix. The prefix is also what
          # tells you afterwards which variables were not published at the block
          # group level for this vintage.
          tract_geo_id = props['GEOID'][0:11]
          #print(f"tract_geo_id is: {tract_geo_id}")
          if tract_geo_id in tract_keys:
            for j in tract_geo_ids[tract_geo_id]:
              record["tract_" + j] = tract_geo_ids[tract_geo_id][j]

          ## Recoded Columns ##

          if props['GEOID'] in bgrp_keys:
            bgrp_variables = bgrp_geo_ids[props['GEOID']]
          else:
            bgrp_variables = {}
          if tract_geo_id in tract_keys:
            apply_recodes(record, bgrp_variables, tract_geo_ids[tract_geo_id])
          else:
            apply_recodes(record, bgrp_variables, None)

          records.append(record)
      gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
      output_file_name = f"{sys.argv[2]} {sys.argv[3]} {sys.argv[4]} {sys.argv[5]}.geoparquet"
      gdf.to_parquet(output_file_name.replace(' ', '_').replace('-', '_'))
    case "Place":
      for feature in place_map["features"]:
        geom = shape(feature["geometry"]) #parse GeoJSON geometry
        props = feature.get("properties", {}) #whatever is already on the feature
        print(props)
        props['GEOID']
        record = {
          "geometry": geom,
          **props,
        }
        record["source"] = "acs5"
        record["vintage"] = int(vintage)
        record["geo_name"] = sys.argv[2]
        record["geo_level"] = "place"
        print(f"props['GEOID'] is: {props['GEOID']}")
        for j in place_geo_ids[props['GEOID']]:
          record[j] = (place_geo_ids[props['GEOID']][j])
        apply_recodes(record, place_geo_ids[props['GEOID']], None)
        records.append(record)
      gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
      output_file_name = f"{sys.argv[2]} {sys.argv[3]} {sys.argv[4]} {sys.argv[5]}.geoparquet"
      gdf.to_parquet(output_file_name.replace(' ', '_').replace('-', '_'))
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
        if props['GEOID'] in zcta_keys:
          for j in zcta_geo_ids[props['GEOID']]:
            record[j] = (zcta_geo_ids[props['GEOID']][j])

          ## Recoded Columns ##

          # B08301 and B15003 are published at the zip code tabulation area, so
          # there is nothing to copy down and no tract dictionary is passed.
          apply_recodes(record, zcta_geo_ids[props['GEOID']], None)
        records.append(record)
        # this append was one level deeper, inside the variable loop, which wrote
        # one duplicate row per variable
      gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
      output_file_name = f"{sys.argv[2]} {sys.argv[3]} {sys.argv[4]} {sys.argv[5]}.geoparquet"
      gdf.to_parquet(output_file_name.replace(' ', '_').replace('-', '_'))

#elif decennial_census: