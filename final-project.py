import requests
import random
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

def get_user_location():
    # Trying to get user location from their API
    ip_api_url = 'http://ip-api.com/json/'
    response = requests.get(ip_api_url)
    if response.status_code == 200:
        data = response.json()
        lat = data['lat']
        lon = data['lon']
        print(f"{lat}, {lon}")
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
            print(f"{lat}, {lon}")
            return f"{lat}, {lon}"
        else:
            # If we can't get the location from the user or the API, return a default location (London, UK) aka the fashion capital!
            print("51.5074, 0.1278")
            return "51.5074, 0.1278"
        
def get_season():
    valid_seasons = ['fall', 'autumn', 'winter', 'spring', 'summer']
    while True:
        season = input("What season is it: ").lower()
        if season in valid_seasons:
            return season
        else:
            print(f"Invalid season '{season}', please enter one of {', '.join(valid_seasons)}")


def scrape_fashion_data():
    url = 'https://www.vogue.com/fashion/trends'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

def parse_fashion_data(fashion_soup):
    seasons = ['fall', 'autumn', 'winter', 'summer', 'spring']
    season_clothing_dict = {}
    article_links = fashion_soup.find_all('a', class_='SummaryItemHedLink-ciaMYZ')

    for article in fashion_soup.find_all('a', {'class': 'SummaryItemHedLink-ciaMYZ'}):
        title = article.find('h3').text.lower()
        if 'fall' not in title and 'autumn' not in title and 'spring' not in title and 'winter' not in title and 'summer' not in title:
            continue

        url = 'https://www.vogue.com' + article['href']
        article_response = requests.get(url)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        season = None  

        # Find the season mentioned in the article title
        for s in ['fall', 'autumn', 'winter', 'summer', 'spring']:
            if s in title:
                season = s.capitalize()
                break

        # If a season was found, add the clothing items to the corresponding list in the dictionary
        if season is not None:
            clothing_items = {}
            for item in article_soup.find_all('p'):
                item_text = item.text.lower()
                for clothing_type in ['dress', 'jacket', 'coat', 'shirt', 'pants', 'jeans', 'skirt', 'blouse', 'sweater', 'boots']:
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
            season_clothing_dict[season] = clothing_items
    return season_clothing_dict


soup1 = scrape_fashion_data()
print(parse_fashion_data(soup1))


def get_product_recommendations(product_dict):
    # Define the ASOS API endpoint and parameters
    asos_api_endpoint = 'https://api.asos.com/product/search/v2/categories'
    category_ids = '4209,4232,4233,4234,4235,4237,4238,4239,4240,4241,4242,4243,4245,4247'
    url = f'{asos_api_endpoint}/{category_ids}'
    headers = {'Content-Type': 'application/json'}
    payload = {'country': 'US', 'currency': 'USD', 'lang': 'en-US', 'store': 'US'}

    # Query the ASOS API with the product categories
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        product_ids = []
        # Extract the product ids from the API response
        for category in data['categories']:
            for product in category['products']:
                product_ids.append(product['id'])
        # Randomly select 10 product ids from the list of product ids
        random_product_ids = random.sample(product_ids, k=min(10, len(product_ids)))
        # Get the ASOS product details for the selected product ids
        product_details = []
        for product_id in random_product_ids:
            product_url = f'https://api.asos.com/product/catalogue/v3/products/{product_id}'
            product_response = requests.get(product_url)
            if product_response.status_code == 200:
                product_data = product_response.json()
                product_details.append({
                    'name': product_data['name'],
                    'price': product_data['price']['current']['value'],
                    'image_url': product_data['media']['images'][0]['url']
                })
        return product_details
    else:
        print("Failed to retrieve product recommendations from ASOS API")

def make_outfit_recommendation(weather_dict, fashion_dict, product_dict):
    temperature = weather_dict.get('temperature')
    humidity = weather_dict.get('humidity')
    wind_speed = weather_dict.get('wind_speed')
    precipitation = weather_dict.get('precipitation')

    if temperature is None or humidity is None or wind_speed is None:
        return "Incomplete weather information"

    # Determine the appropriate season based on the temperature
    season = get_season()

    # Choose the appropriate clothing items based on the weather and season
    if precipitation is not None and precipitation > 0:
        top = fashion_dict.get(season).get('Top').get('Sweater')
        bottom = fashion_dict.get(season).get('Bottom').get('Pants')
        shoes = fashion_dict.get(season).get('Shoe').get('Boots')
    elif wind_speed > 5:
        top = fashion_dict.get(season).get('Top').get('Sweater')
        bottom = fashion_dict.get(season).get('Bottom').get('Pants')
        shoes = fashion_dict.get(season).get('Shoe').get('Boots')
    elif temperature > 20:
        top = fashion_dict.get(season).get('Top').get('T-shirt')
        bottom = fashion_dict.get(season).get('Bottom').get('Shorts')
        shoes = fashion_dict.get(season).get('Shoe').get('Sandals')
    else:
        top = fashion_dict.get(season).get('Top').get('Sweater')
        bottom = fashion_dict.get(season).get('Bottom').get('Jeans')
        shoes = fashion_dict.get(season).get('Shoe').get('Sneakers')

    # Choose the appropriate products based on the clothing items
    top_product = None
    bottom_product = None
    shoes_product = None
    #NOT DONE


    # Create the recommendation message
    message = f"Based on the weather forecast, we recommend you wear:\n- {top_product} as the top\n- {bottom_product} as the bottom\n- {shoes_product} as the shoes"
    return message

