#Hannah's functions - SI 206, WN 2023
import unittest
import sqlite3
import json
import requests
import re
import os
import matplotlib.pyplot as plt
from datetime import date

#duplicate function--remove from one file
def get_user_location():
    #attempt to get user location using API
    ip_api_url = 'http://ip-api.com/json/'
    response = requests.get(ip_api_url)
    if response.status_code == 200:
        data = response.json()
        lat = data['lat']
        lon = data['lon']
        return f"{lat}, {lon}"
    else:
        #attempt to get user location from input
        #NEED API KEY
        city = input("Enter your city: ")
        country = input("Enter your country: ")
        geocoding_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={city},{country}&key="
        response = requests.get(geocoding_url)
        if response.status_code == 200:
            data = response.json()
            lat = data['results'][0]['geometry']['location']['lat']
            lon = data['results'][0]['geometry']['location']['lng']
            return f"{lat}, {lon}"
        else:
            #return default location (London, UK)
            return "51.5074, 0.1278"

def retrieve_weather_data(user_location):
    #Note: lat and lon should be limited to 2 decimal places
    #api call limit: 3000 calls per minute
    lat = re.findall('-*\d+.\d{2}', user_location)[0]
    lon = re.findall(', (-*\d+.\d{2})', user_location)[0]
    url = f'https://pro.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid=f849d7d219fc9e261182e654aad9ce6b'
    
    resp = requests.get(url)
    if resp.status_code == 200:
        print("Successfully retrieved current weather data")
        return resp.text
    else:
        print("Error retrieving current weather data")

def retrieve_historical_weather_data(user_location):
    #make database
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+"weather_db.db")
    cur = conn.cursor()

    #make table for weather data and general descriptions
    cur.execute("CREATE TABLE IF NOT EXISTS weather (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE, general_id INTEGER, temp DOUBLE, humidity DOUBLE, wind DOUBLE)")
    cur.execute("CREATE TABLE IF NOT EXISTS general (id INTEGER PRIMARY KEY NOT NULL UNIQUE, description TEXT UNIQUE)")
    conn.commit()

    #setup previous var to subtract from last date gathered so no duplicate dates
    cur.execute("SELECT MAX(id) FROM weather")
    conn.commit()
    try: 
        previous = cur.fetchone()
        if previous[0] == None:
            previous = 0
        else: 
            previous = previous[0]
    except:
        previous = 0

    #make 25 calls and store data in weather_db
    #prep api call args with user location and current date (RESOURCE: https://www.geeksforgeeks.org/get-current-date-using-python/)
    lat = re.findall('-*\d+.\d{2}', user_location)[0]
    lon = re.findall(', (-*\d+.\d{2})', user_location)[0]
    today = str(date.today())

    for i in range(25):
        month = int(re.findall('-(\d+)-', today)[0])
        day = int(re.findall('-(\d+)', today)[0])
        #api call limit: 50,000 calls per day
        #subtract i and last date gathered to get past 25 days
        day -= (i + previous)
        while day < 1:
            month -= 1
            #cycle day
            if month in [1, 3, 5, 7, 8, 10, 12]:
                day += 31
            elif month == 2:
                day += 28
            else:
                day += 30
            
            #cycle month
            if month <= 0:
                month += 12

        url_day = str(day)
        url_month = str(month)

        #make call
        print("month : " + url_month + " | day: " + url_day)
        url = f"https://history.openweathermap.org/data/2.5/aggregated/day?lat={lat}&lon={lon}&month={url_month}&day={url_day}&appid=f849d7d219fc9e261182e654aad9ce6b"
        resp = requests.get(url)

        if resp.status_code == 200:
            print("parsing data . . .")

            #retrieve temperature, humidity, wind speed, precipitation from JSON
            weather_py = json.loads(resp.text)
            general = weather_py["result"]["precipitation"]["mean"]
            #   translate precipitation (int in mm) into text 
            if (general == 0):
                general = "no rain"
            elif (general < 0.2):
                general = "light rain"
            elif (general < 1):
                general = "moderate rain"
            else:
                general = "heavy rain"

            temp = weather_py["result"]["temp"]["mean"]
            #convert from Kelvin to Fahrenheit
            temp = (temp * (9/5.0)) - 459.67
            humidity = weather_py["result"]["humidity"]["mean"]
            wind = weather_py["result"]["wind"]["mean"]

            #get id for general description
            #setup previous var to subtract from last date gathered so no duplicate dates
            cur.execute("SELECT MAX(id) FROM general")
            conn.commit()
            try: 
                id = cur.fetchone()
                if id[0] == None:
                    id = 0
                else: 
                    id = id[0] + 1
            except:
                id = 0

            cur.execute("INSERT OR IGNORE INTO general (id, description) VALUES (?,?)", (id, general))
            cur.execute("SELECT id FROM general WHERE description = (?)", (general,))
            conn.commit()
            general_id = cur.fetchone()[0]

            #add to database
            cur.execute("INSERT OR IGNORE INTO weather (general_id, temp, humidity, wind) VALUES (?,?,?,?)", (general_id, temp, humidity, wind))
            conn.commit()

        else:
            print("Error retrieving historical weather data")

def generate_visualizations():
    #make lists of weather data to plot from first 25 datapoints
    #make connection to db
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+"weather_db.db")
    cur = conn.cursor()

    #LINE GRAPH
    #make list of last 25 days
    days = []
    today = str(date.today())

    for i in range(25):
        month = int(re.findall('-(\d+)-', today)[0])
        day = int(re.findall('-(\d+)', today)[0])
        day -= i
        while day < 1:
            month -= 1
            #cycle day
            if month in [1, 3, 5, 7, 8, 10, 12]:
                day += 31
            elif month == 2:
                day += 28
            else:
                day += 30
            
            #cycle month
            if month <= 0:
                month += 12

        days.append(str(month) + '/' + str(day))

    #get temps
    cur.execute()
    conn.commit()

    temps = []
    humidity = []
    wind = []
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    #add line plot data
    ax1.plot(days, temps, "g-", label = "Temperature (F)")
    #MOVE TO SEPARATE GRAPH??
    ax1.plot(days, humidity, "b-", label = "Humidity (%)")
    ax1.plot(days, wind, "r-", label = "Wind (meter/sec)")
    ax1.legend()

    #add line plot labels
    ax1.set_xlabel("Trend over Days")
    #ax1.set_ylabel("Level")
    ax1.set_title("Average Daily Levels of Temperature, Humidity, and Wind Over the Past 25 Days")
    ax1.grid()

    #BAR GRAPH (histogram?)
    level = []
    #use count to total days of different levels of precipitation
    total = []

    #add bar graph data
    ax2.barh(total, level)

    #add bar graph labels
    ax2.set_xlabel("Number of Days")
    ax2.set_ylabel("Level of Precipitation")
    ax2.set_title("Levels of Precipitation Over the Past 25 Days")

    #save the figure
    fig.savefig("historical_weather.png")

def parse_weather_data(weather_json):
    #retrieve temperature, humidity, wind speed, precipitation from JSON
    weather_dict = {}
    weather_py = json.loads(weather_json)
    #rain/precipitation would be specified in general
    weather_dict["general"] = weather_py["weather"][0]["description"]
    weather_dict["temp"] = weather_py["main"]["temp"]
    weather_dict["humidity"] = weather_py["main"]["humidity"]
    weather_dict["wind"] = weather_py["wind"]["speed"]

    return weather_dict

def main():
    #get data for current weather
    loc = get_user_location()
    weather_json = retrieve_weather_data(loc)
    #use current weather for outfit recommendation
    weather_dict = parse_weather_data(weather_json)
    print(weather_dict)

    #get historical weather data for database
    #old_weather = retrieve_historical_weather_data(loc)

    #make visualizations from historical weather database
    #generate_visualizations()

    #do calculations (specify what)
    #NEED TO CALCULATE SOMETHING (COUNT, AVG, ETC.)
    #NEED TO DO A JOIN
    #WRITE CALCULATIONS TO FILE AS TEXT

if __name__ == "__main__":
    main()
#    unittest.main(verbosity=2)