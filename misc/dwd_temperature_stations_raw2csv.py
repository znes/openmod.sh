# -*- coding: utf-8 -*-
"""
This snippet reads the txt file from data and writes it to a csv file in the
data directory

Source for the textfile is the ftp dwd server:
ftp://ftp-cdc.dwd.de/pub/CDC/observations_germany/climate/hourly/air_temperature/historical/TU_Stundenwerte_Beschreibung_Stationen.txt


"""

import pandas as pd

# open file and read lines as list of lists
with open('../data/dwd_temperature_stations_raw.txt',
          encoding="ISO-8859-1") as f:
    content = f.readlines()

# split elements in list accordingly to the 'columns'
x = [l.split() for l in content]

# create emtpy dataframe
df = pd.DataFrame(columns=['station_id', 'lon', 'lat', 'name'],
                  index=range(len(x)))

# loop over index and fill data frame with specific station data
for i in df.index[2:-1]:
    df.iloc[i]['station_id'] = x[i][0]
    df.iloc[i]['lat'] = x[i][4]
    df.iloc[i]['lon'] = x[i][5]
    df.iloc[i]['name'] = x[i][6]

# drop first two and last columns that is stuff we don't wnat
df.dropna(inplace=True, how='any')

# write to csv file ...
df.to_csv('../data/temperature_stations.csv',
          index=False)


