#FINAL COMPLETE FUNCTION LIST

import requests
import random
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import nltk
import unittest
import sqlite3
import json
import re
import os
from datetime import date
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

def get_user_location():
    ip_api_url = 'http://ip-api.com/json/'
    response = requests.get(ip_api_url)
    if response.status_code == 200:
        data = response.json()
        lat = data['lat']
        lon = data['lon']
        return f"{lat}, {lon}"
    else:
        city = input("Enter your city: ")
        country = input("Enter your country: ")
        geocoding_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={city},{country}&key=AIzaSyA4p8sXBp5xyMtohNGNUtQqU3xIxXqaVLA"
        response = requests.get(geocoding_url)
        if response.status_code == 200:
            data = response.json()
            lat = data['results'][0]['geometry']['location']['lat']
            lon = data['results'][0]['geometry']['location']['lng']
            return f"{lat}, {lon}"
        else:
            return "51.5074, 0.1278"

def get_season():
    valid_seasons = ['fall', 'autumn', 'winter', 'spring', 'summer']
    while True:
        season = input("What season is it: ").lower()
        if season in valid_seasons:
            return season[0].upper() + season[1:].lower()
        else:
            print(f"Invalid season '{season}', please enter one of {', '.join(valid_seasons)}")

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
        day = int(re.findall('\d+-\d+-(\d+)', today)[0])
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


def parse_weather_data(weather_json):
    #retrieve temperature, humidity, wind speed, precipitation from JSON
    weather_dict = {}
    weather_py = json.loads(weather_json)
    #rain/precipitation would be specified in general
    weather_dict["general"] = weather_py["weather"][0]["main"]
    temp_kelvin = weather_py["main"]["temp"]
    weather_dict['temp'] = (temp_kelvin * (9/5.0)) - 459.67
    weather_dict["humidity"] = weather_py["main"]["humidity"]
    weather_dict["wind"] = weather_py["wind"]["speed"]

    return weather_dict

def scrape_fashion_data():
    url = 'https://www.vogue.com/fashion/trends'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup


def parse_fashion_data(fashion_soup):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+"weather_db.db")
    cur = conn.cursor()

    #make table for weather data and general descriptions
    cur.execute("CREATE TABLE IF NOT EXISTS vogue (id INTEGER PRIMARY KEY NOT NULL UNIQUE, season_id INTEGER, clothing_id INTEGER, adjective TEXT UNIQUE)")
    cur.execute("CREATE TABLE IF NOT EXISTS seasons (id INTEGER PRIMARY KEY NOT NULL UNIQUE, season TEXT UNIQUE)")
    cur.execute("CREATE TABLE IF NOT EXISTS clothes (id INTEGER PRIMARY KEY NOT NULL UNIQUE, type TEXT UNIQUE)")
    conn.commit()

    season_clothing_dict = {}
    article_links = fashion_soup.find_all('a', class_='SummaryItemHedLink-ciaMYZ')

    try:
        last = cur.execute("SELECT MAX(id) FROM vogue").fetchone()
        if (last[0] == None):
            last = 0
        else:
            last = last[0] + 1
    except:
        last = 0
    
    conn.commit()
    for article in article_links:
        title = article.find('h3').text.lower()
        if 'fall' not in title and 'autumn' not in title and 'spring' not in title and 'winter' not in title and 'summer' not in title:
            continue
        if 'https://www.vogue.com' not in article['href']:
            url = 'https://www.vogue.com' + article['href']
        else:
            url = article['href']
        article_response = requests.get(url)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        season = None  

        # Find the season mentioned in the article title
        for s in ['fall', 'autumn', 'winter', 'summer', 'spring']:
            cur.execute("INSERT OR IGNORE INTO seasons (season) VALUES (?)", (s.capitalize(),))
            conn.commit()

            if s in title:
                season = s.capitalize()
                break

        # If a season was found, add the clothing items to the corresponding list in the dictionary
        if season is not None:
            clothing_items = {}
            for item in article_soup.find_all('p'):
                item_text = item.text.lower()
                for clothing_type in ["blouse","cardigan","coat","dress","hoodie","jacket","jeans","jumpsuit","leggings","pants","pant","polo shirt","shirt","shorts","skirt","sweater","sweater vest","suit","swimwear","tank top","t-shirt","underwear","socks","belt","gloves","hat","jewelry","scarf","shoes","sneakers","boots","sandals","watch"]:
                    if clothing_type in item_text:
                        adjectives = []
                        # Use the NLTK POS tagger to identify adjectives
                        words = nltk.word_tokenize(item_text)
                        tags = nltk.pos_tag(words)
                        for i in range(len(words)-1):
                            if words[i+1] == clothing_type and tags[i][1] == 'JJ':
                                adjectives.append(words[i])
                        if adjectives:
                            if clothing_type not in clothing_items:
                                clothing_items[clothing_type] = []
                            clothing_items[clothing_type].extend(adjectives)
                            id = cur.execute("SELECT MAX(id) FROM vogue").fetchone()[0]
                            if id == None:
                                id = 0
                            else:
                                id += 1
                            season_id = int(cur.execute("SELECT id FROM seasons WHERE season = (?)", (season,)).fetchone()[0])
                            clothing_id = int(cur.execute("SELECT id FROM clothes WHERE type = (?)", (clothing_type,)).fetchone()[0])
                            for adj in adjectives:
                                cur.execute("INSERT OR IGNORE INTO vogue (id, season_id, clothing_id, adjective) VALUES (?,?,?,?)", (id, season_id, clothing_id, adj))
                            conn.commit()
                            
            season_clothing_dict[season] = clothing_items
    return season_clothing_dict

def query_forever21_api(fashion_data_dict):

    headers = {
            "X-RapidAPI-Key": "5a61c7400emshf154c64810bf95cp1d3ccajsn7b2be8277c26",
            "X-RapidAPI-Host": "apidojo-forever21-v1.p.rapidapi.com"
    }

    url = "https://apidojo-forever21-v1.p.rapidapi.com/products/search"
    new_list = []
    new_dict = {}
    for season in fashion_data_dict: 
        # print(season)
        for key,value in fashion_data_dict[season].items(): #access key not value 
            for v in value: 
                q = v +'+'+key #concatenation
                querystring = {"query":q,"rows":"60","start":"0","color_groups":"black"}
                #{"query": q,"rows":"60","start":"0"}
                # print(type(q))
                # print(querystring)
                response = requests.get(url, headers=headers, params=querystring).json() #call
                # print(response)

                new_list.append(response['response']['docs'][0]['url']) 
        new_dict[season] = new_list
    return new_dict

def parse_forever21_data(f21_urls):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+"weather_db.db")
    cur = conn.cursor()

    #make table for weather data and general descriptions
    cur.execute("CREATE TABLE IF NOT EXISTS forever21 (id INTEGER PRIMARY KEY NOT NULL UNIQUE, product TEXT, parent INT, image TEXT, price DOUBLE)")
    cur.execute("CREATE TABLE IF NOT EXISTS category (id INTEGER PRIMARY KEY NOT NULL UNIQUE, parent TEXT)")
    conn.commit()

    final_dict = {}
    count = 0

    for seasons in f21_urls:
        new_list = []
        for url in f21_urls[seasons]:
            id_isolation = url.split("/")
            index_id = id_isolation[4].replace('.html', "")
            new_list.append(index_id)
        # print(new_list)
        empty_dict = {}
        for id in new_list:
            # querystring = {"productId": "2000383198"}
            # print(querystring)
            # response = requests.get(url, headers=headers, params=querystring).text
        
            # print(response)
            url = "https://apidojo-forever21-v1.p.rapidapi.com/products/v2/detail"
            
            querystring = {"productId": id}

            headers = {
            "X-RapidAPI-Key": "5a61c7400emshf154c64810bf95cp1d3ccajsn7b2be8277c26",
            "X-RapidAPI-Host": "apidojo-forever21-v1.p.rapidapi.com"
            }
            response = requests.request("GET", url, headers=headers, params=querystring).json()

            #access keys from response and make a list of dict where each one is a product 

            empty_dict[id] = {}

            empty_dict[id]['DisplayName'] = response['product']['DisplayName']
            empty_dict[id]['PrimaryParentCategory'] = response['product']['PrimaryParentCategory']
            empty_dict[id]['ProductShareLinkUrl'] = response['product']['ProductShareLinkUrl']
            empty_dict[id]['DefaultProductImage'] = response['product']['DefaultProductImage']
            empty_dict[id]['ListPrice'] = response ['product']['ListPrice']

            if count < 7:
                if cur.execute("SELECT id FROM category WHERE parent = (?)", (response['product']['PrimaryParentCategory'], )).fetchone():
                    
                    parent = cur.execute("SELECT id FROM category WHERE parent = (?)", (response['product']['PrimaryParentCategory'], )).fetchone()[0]
                else: 
                    id_s = cur.execute("SELECT max(id) FROM category").fetchone()[0]
                    if id_s == None:
                        id_s = 0
                    else: 
                        id_s += 1 
                    cur.execute("INSERT OR IGNORE INTO category (id, parent) VALUES (?,?)", (id_s, response['product']['PrimaryParentCategory']))
                    parent = id_s
                cur.execute("INSERT OR IGNORE INTO forever21 (id, product, parent, image, price) VALUES (?,?,?,?,?)", (id, response['product']['DisplayName'], parent, response['product']['DefaultProductImage'], response['product']['ListPrice']))
            conn.commit() 
            count += 1 
        
        final_dict[seasons] = empty_dict
    return final_dict

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

    #get temp data
    temps = []
    cur.execute("SELECT temp FROM weather LIMIT 25")
    conn.commit()
    for i in cur.fetchall():
        temps.append(i[0])

    #get humidity data
    humidity = []
    cur.execute("SELECT humidity FROM weather LIMIT 25")
    conn.commit()
    for i in cur.fetchall():
        humidity.append(i[0])

    #get wind data
    wind = []
    cur.execute("SELECT wind FROM weather LIMIT 25")
    conn.commit()
    for i in cur.fetchall():
        wind.append(i[0])
    
    #fig, (ax1, ax2, ax3, ax4) = plt.subplots(2, 2, figsize=(30, 10))
    fig = plt.figure(figsize=(30, 10))
    ax1 = fig.add_subplot(2,2,1)
    ax2 = fig.add_subplot(2,2,2)
    ax3 = fig.add_subplot(2,2,3)
    ax4 = fig.add_subplot(2,2,4)
    
    #reverse data so increasing in date
    days = days[::-1]
    temps = temps[::-1]
    humidity = humidity[::-1]
    wind = wind[::-1]

    #add line plot data
    ax1.plot(days, temps, "g-", label = "Temperature (F)")
    ax3.plot(days, humidity, "b-", label = "Humidity (%)")
    ax4.plot(days, wind, "r-", label = "Wind (meters/sec)")
    #ax1.legend()

    #add line plot labels
    ax1.set_xlabel("Trend over Days")
    ax1.set_title("Average Daily Levels of Temperature (F) Over the Past 25 Days")
    ax1.grid()
    ax3.set_xlabel("Trend over Days")
    ax3.set_title("Average Daily Levels of Humidity (%) Over the Past 25 Days")
    ax3.grid()
    ax4.set_xlabel("Trend over Days")
    ax4.set_title("Average Daily Levels of Wind (meters/sec) Over the Past 25 Days")
    ax4.grid()

    #BAR GRAPH (histogram?)
    #get list of different descriptions (levels of precipitation)
    level = ["no rain", "light rain", "moderate rain", "heavy rain"]

    #use count to total days of different levels of precipitation
    total = []
    for l in level:
        cur.execute("SELECT COUNT(weather.general_id) FROM weather JOIN general ON weather.general_id = general.id WHERE general.description = (?)", (l,))
        total.append(cur.fetchone()[0])
    conn.commit()

    #reassign list with capitalized levels for labeling bar chart
    level = ["No Rain", "Light Rain", "Moderate Rain", "Heavy Rain"]

    #write calculations to a txt file
    path = os.path.dirname(os.path.abspath(__file__))
    file = (path+'/'+"weather_calculations.txt")
    f = open(file, 'w')

    #find average temp
    cur.execute("SELECT AVG(temp) FROM weather LIMIT 25")
    conn.commit()
    avg_temp = cur.fetchone()[0]

    f.write("Over the last 100 days, a total of " + str(max(total)) + " days had " + level[total.index(max(total))] + "\n")
    f.write("The average temperature over the last 25 days was " + str(avg_temp) + " degrees Fahrenheit")

    #add bar graph data
    ax2.bar(level, total)

    #add bar graph labels
    ax2.set_ylabel("Number of Days")
    ax2.set_xlabel("Level of Precipitation")
    ax2.set_title("Levels of Precipitation Over the Past 100 Days")

    #save the figure
    fig.savefig("historical_weather.png")

def get_outfit(weather_dict, season, fashion_dict):
    temperature = weather_dict.get('temp')
    precipitation = weather_dict.get('general')

   
    if precipitation == "Clear":
        if temperature < 32:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 32 and temperature < 60:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 60 and temperature < 80:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")     

    if precipitation == "Thunderstorm" or precipitation == "Rain" or precipitation == "Drizzle": 
        if temperature >= 32 and temperature < 60:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory']
                    if category == 'top':
                        top = product_info
                    elif category == 'bottom':
                        bottom = product_info
                    elif category == 'shoes':
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 60 and temperature < 80:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 80 and temperature < 150:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
    elif precipitation == "Snow":
        if temperature >= 32:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 32 and temperature < 60:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
    if precipitation == "Clouds":
        if temperature >= 32:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 32 and temperature < 60:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 60 and temperature < 80:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 80 and temperature < 150:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
    elif precipitation != "Clouds" or precipitation != "Clear" or precipitation != "Thunderstorm" or precipitation != "Drizzle" or precipitation != "Rain" or precipitation != "Snow":
        if temperature >= 32:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 32 and temperature < 60:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 60 and temperature < 80:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
        elif temperature >= 80 and temperature < 150:
            season_products = fashion_dict.get(season)
            if season_products:
                top = None
                bottom = None
                shoe = None
                for product_id, product_info in season_products.items():
                    category = product_info['PrimaryParentCategory'].split("_")[:-1]
                    print(category)
                    if category == 'tops' or category == "top" or category == ["plus", "size", "top"]:
                        top = product_info
                    elif category == 'bottoms'or category == ["plus", "size", "bottom"]:
                        bottom = product_info
                    elif category == 'shoes'or category == "shoe" or category == "boots":
                        shoe = product_info
                if top and bottom and shoe:
                    print(f"Top: {top['DisplayName']}\nBottom: {bottom['DisplayName']}\nShoe: {shoe['DisplayName']}")
                else:
                    print("Could not find matching top, bottom, and shoe for this season.")
                    found_products = [p for p in [top, bottom, shoe] if p is not None]
                    if found_products:
                        user_choice = input("Do you want to see the products that were found? (y/n) ")
                        if user_choice.lower() == "y":
                            for product in found_products:
                                print(f"{product['PrimaryParentCategory'].capitalize()}: {product['DisplayName']}")
            else:
                print("No products found for this season.")
            
soup = scrape_fashion_data()
dic = parse_fashion_data(soup)
urls = query_forever21_api(dic)

soup = scrape_fashion_data()
loc = get_user_location()
weather_json = retrieve_weather_data(loc)
w_dict = parse_weather_data(weather_json)
print(w_dict)
season = get_season()
f_dict = parse_forever21_data(urls)
# print(f_dict)
get_outfit(w_dict, season, f_dict)