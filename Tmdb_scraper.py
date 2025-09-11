import requests
import random
from bs4 import BeautifulSoup
import json
import re
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import time

# Disable SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1"
]

def get_random_ua():
    return random.choice(user_agents)

headers = {
    'User-Agent': get_random_ua(),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,ar-EG;q=0.8,ar;q=0.7',
    'Referer': 'https://www.themoviedb.org',
    'Connection': 'keep-alive',
}

def extract_title_from_card(card):
    """Extract the main title from a movie card, handling different HTML structures"""
    # Method 1: Try to find h2 tag directly
    h2_tag = card.find('h2')
    if h2_tag:
        # Remove any span elements with class 'title' (alternative titles)
        for span in h2_tag.find_all('span', class_='title'):
            span.decompose()
        title = h2_tag.get_text(strip=True)
        if title:
            return title
    
    # Method 2: Try to find the title in the a tag with class 'result'
    a_tag = card.find('a', class_='result')
    if a_tag:
        # Remove any span elements with class 'title'
        for span in a_tag.find_all('span', class_='title'):
            span.decompose()
        title = a_tag.get_text(strip=True)
        if title:
            return title
    
    # Method 3: Try to extract from img alt text
    img_tag = card.find('img', class_='poster')
    if img_tag and img_tag.has_attr('alt'):
        return img_tag['alt']
    
    # Method 4: Try to extract from URL
    a_tag = card.find('a', class_='result')
    if a_tag and a_tag.has_attr('href'):
        url_parts = a_tag['href'].split('/')
        if len(url_parts) > 2:
            # Extract title from URL like "/movie/1035259-the-naked-gun"
            title_part = url_parts[-1]
            # Remove ID part if present
            if '-' in title_part:
                title_part = title_part.split('-', 1)[1]
            # Replace hyphens with spaces and capitalize
            return title_part.replace('-', ' ').title()
    
    return "Unknown Title"

def extract_alternative_title(card):
    """Extract alternative title if present"""
    alt_title_span = card.find('span', class_='title')
    if alt_title_span:
        return alt_title_span.get_text(strip=True)
    return None

def extract_poster_url(card):
    """Extract poster URL and try to get higher resolution"""
    img_tag = card.find('img', class_='poster')
    if img_tag and img_tag.has_attr('src'):
        poster_url = img_tag['src']
        # Try to get a larger version of the poster
        if 'w94_and_h141_bestv2' in poster_url:
            return poster_url.replace('w94_and_h141_bestv2', 'w220_and_h330_face')
        elif 'w130_and_h195_bestv2' in poster_url:
            return poster_url.replace('w130_and_h195_bestv2', 'w220_and_h330_face')
        return poster_url
    return None

def extract_tmdb_id(card):
    """Extract TMDB ID from the card"""
    a_tag = card.find('a', class_='result')
    if a_tag and a_tag.has_attr('href'):
        href = a_tag['href']
        # Extract ID from URL like "/movie/1035259-the-naked-gun"
        match = re.search(r'/movie/(\d+)', href)
        if match:
            return match.group(1)
    return None

def scrape_tmdb_movies(movie_title):
    """Scrape TMDB for movies matching the search title"""
    # Prepare the search query
    title = movie_title.replace(' ', '+').lower()
    url = f"https://www.themoviedb.org/search?query={title}"
    
    # Make the request
    response = requests.get(url, headers=headers, verify=False, timeout=10)
    response.raise_for_status()
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all movie cards
    movie_cards = soup.find_all('div', class_='card')
    
    movies_data = []
    
    for card in movie_cards:
        # Extract movie data
        movie = {}
        
        # Extract title
        movie['title'] = extract_title_from_card(card)
        
        # Extract alternative title
        alt_title = extract_alternative_title(card)
        if alt_title:
            movie['alternative_title'] = alt_title
        
        # Extract URL
        a_tag = card.find('a', class_='result')
        if a_tag and a_tag.has_attr('href'):
            movie['url'] = "https://www.themoviedb.org" + a_tag['href']
        
        # Extract release date
        release_date = card.find('span', class_='release_date')
        if release_date:
            movie['release_date'] = release_date.get_text(strip=True)
        
        # Extract overview
        overview = card.find('div', class_='overview')
        if overview and overview.find('p'):
            movie['overview'] = overview.find('p').get_text(strip=True)
        
        # Extract poster URL
        poster_url = extract_poster_url(card)
        if poster_url:
            movie['poster_url'] = poster_url
        
        # Extract media type and adult content
        if a_tag and a_tag.has_attr('data-media-type'):
            movie['media_type'] = a_tag['data-media-type']
        
        if a_tag and a_tag.has_attr('data-media-adult'):
            movie['adult_content'] = a_tag['data-media-adult'] == 'true'
        
        # Extract TMDB ID
        tmdb_id = extract_tmdb_id(card)
        if tmdb_id:
            movie['tmdb_id'] = tmdb_id
        
        movies_data.append(movie)
    
    return movies_data

def scrape_movie_logos(movie_url):
    """Scrape logo images from the movie's logos page"""
    logos_url = movie_url + "/images/logos"
    
    try:
        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Make the request
        response = requests.get(logos_url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the section with logos
        logos_section = soup.find('section', class_='panel user_images')
        if not logos_section:
            return []
        
        # Find all logo images
        logo_images = []
        logo_elements = logos_section.select('img[src*="w500"]')
        
        for logo_element in logo_elements:
            if logo_element.has_attr('src'):
                logo_url = logo_element['src']
                logo_images.append(logo_url)
        
        return logo_images
        
    except Exception as e:
        print(f"Error scraping logos: {e}")
        return []

def scrape_movie_backdrops(movie_url):
    """Scrape backdrop images from the movie's backdrops page"""
    backdrops_url = movie_url + "/images/backdrops"
    
    try:
        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Make the request
        response = requests.get(backdrops_url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the section with backdrops
        backdrops_section = soup.find('section', class_='panel user_images')
        if not backdrops_section:
            return []
        
        # Find all backdrop images with w500_and_h282_face size
        backdrop_images = []
        backdrop_elements = backdrops_section.select('img[src*="w500_and_h282_face"]')
        
        for backdrop_element in backdrop_elements:
            if backdrop_element.has_attr('src'):
                backdrop_url = backdrop_element['src']
                backdrop_images.append(backdrop_url)
        
        return backdrop_images
        
    except Exception as e:
        print(f"Error scraping backdrops: {e}")
        return []

def scrape_movie_posters(movie_url):
    """Scrape additional poster images from the movie's posters page"""
    posters_url = movie_url + "/images/posters"
    
    try:
        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Make the request
        response = requests.get(posters_url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the section with posters
        posters_section = soup.find('section', class_='panel user_images')
        if not posters_section:
            return []
        
        # Find all poster images with w220_and_h330_face size
        poster_images = []
        poster_elements = posters_section.select('img[src*="w220_and_h330_face"]')
        
        for poster_element in poster_elements:
            if poster_element.has_attr('src'):
                poster_url = poster_element['src']
                poster_images.append(poster_url)
        
        return poster_images
        
    except Exception as e:
        print(f"Error scraping posters: {e}")
        return []

def scrape_movie_trailers(movie_url):
    """Scrape trailer videos from the movie's videos page"""
    trailers_url = movie_url + "/videos?active_nav_item=Trailers"
    
    try:
        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Make the request
        response = requests.get(trailers_url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the section with trailers
        trailers_section = soup.find('section', class_='panel video')
        if not trailers_section:
            return []
        
        # Find all trailer elements
        trailers = []
        trailer_elements = trailers_section.find_all('div', class_='video card default')
        
        for trailer_element in trailer_elements:
            trailer = {}
            
            # Extract YouTube video ID
            play_button = trailer_element.find('a', class_='play_trailer')
            if play_button and play_button.has_attr('data-id'):
                trailer['youtube_id'] = play_button['data-id']
                trailer['youtube_url'] = f"https://www.youtube.com/watch?v={play_button['data-id']}"
            
            # Extract trailer title
            title_element = trailer_element.find('h2')
            if title_element:
                trailer['title'] = title_element.get_text(strip=True)
            
            # Extract trailer duration and date
            sub_element = trailer_element.find('h3', class_='sub')
            if sub_element:
                trailer['details'] = sub_element.get_text(strip=True)
            
            # Extract site (usually YouTube)
            if play_button and play_button.has_attr('data-site'):
                trailer['site'] = play_button['data-site']
            
            # Extract channel/publisher info
            channel_element = trailer_element.find('h4')
            if channel_element:
                trailer['channel'] = channel_element.get_text(strip=True)
            
            if trailer:
                trailers.append(trailer)
        
        return trailers
        
    except Exception as e:
        print(f"Error scraping trailers: {e}")
        return []

def scrape_movie_cast(movie_url):
    """Scrape cast information from the movie's cast page"""
    cast_url = movie_url + "/cast"
    
    try:
        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Make the request
        response = requests.get(cast_url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the section with cast
        cast_section = soup.find('section', class_='panel pad')
        if not cast_section:
            print("No cast section found")
            return []
        
        # Find all cast members
        cast = []
        cast_elements = cast_section.find_all('li', attrs={'data-order': True})
        
        for i, cast_element in enumerate(cast_elements[:6]):  # Limit to first 6 cast members
            actor = {}
            
            # Extract actor name - look for the <a> tag inside the <p> tag
            info_div = cast_element.find('div', class_='info')
            if info_div:
                p_tag = info_div.find('p')
                if p_tag:
                    a_tag = p_tag.find('a')
                    if a_tag:
                        actor['name'] = a_tag.get_text(strip=True)
            
            # Extract character name
            character_element = cast_element.find('p', class_='character')
            if character_element:
                actor['character'] = character_element.get_text(strip=True)
            
            # Extract profile image URL (w66_and_h66_face size)
            profile_img = cast_element.find('img', class_='profile')
            if profile_img and profile_img.has_attr('src'):
                profile_url = profile_img['src']
                actor['profile_url'] = profile_url
            
            # Only add if we have at least a name
            if actor.get('name'):
                cast.append(actor)
            else:
                print(f"No name found for cast member {i}")
        
        return cast
        
    except Exception as e:
        print(f"Error scraping cast: {e}")
        return []

def scrape_movie_details(movie_url):
    """Scrape detailed information from a specific movie page"""
    try:
        # Make the request
        response = requests.get(movie_url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract detailed information
        details = {}
        
        # Title
        title_element = soup.find('h2', class_='title')
        if title_element:
            details['title'] = title_element.get_text(strip=True)
        
        # Tagline
        tagline_element = soup.find('h3', class_='tagline')
        if tagline_element:
            details['tagline'] = tagline_element.get_text(strip=True)
        
        # Overview
        overview_element = soup.find('div', class_='overview')
        if overview_element:
            details['overview'] = overview_element.find('p').get_text(strip=True) if overview_element.find('p') else overview_element.get_text(strip=True)
        
        # Release date
        release_date_element = soup.find('span', class_='release')
        if release_date_element:
            details['release_date'] = release_date_element.get_text(strip=True)
        
        # Runtime
        runtime_element = soup.find('span', class_='runtime')
        if runtime_element:
            details['runtime'] = runtime_element.get_text(strip=True)
        
        # Genres
        genres = []
        genres_elements = soup.find('span', class_='genres')
        if genres_elements:
            for genre in genres_elements.find_all('a'):
                genres.append(genre.get_text(strip=True))
            details['genres'] = genres
        
        # Rating
        rating_element = soup.find('div', class_='user_score_chart')
        if rating_element and rating_element.has_attr('data-percent'):
            details['rating'] = rating_element['data-percent']
        
        # Poster image (w220_and_h330_face version)
        poster_element = soup.find('img', class_='poster')
        if poster_element and poster_element.has_attr('src'):
            poster_url = poster_element['src']
            details['poster_url'] = poster_url
        
        # Scrape logos
        logos = scrape_movie_logos(movie_url)
        if logos:
            details['logo_urls'] = logos
        
        # Scrape backdrops
        backdrops = scrape_movie_backdrops(movie_url)
        if backdrops:
            details['backdrop_urls'] = backdrops
        
        # Scrape additional posters
        posters = scrape_movie_posters(movie_url)
        if posters:
            details['additional_poster_urls'] = posters
        
        # Scrape trailers
        trailers = scrape_movie_trailers(movie_url)
        if trailers:
            details['trailers'] = trailers
        
        # Scrape cast (first 6 members)
        cast = scrape_movie_cast(movie_url)
        if cast:
            details['cast'] = cast
        
        # Director
        director_elements = soup.select('ol.people li.profile')
        for director_element in director_elements:
            job_element = director_element.find('p', class_='job')
            if job_element and 'director' in job_element.get_text(strip=True).lower():
                name_element = director_element.find('p', class_='name')
                if name_element:
                    details['director'] = name_element.find('a').get_text(strip=True) if name_element.find('a') else name_element.get_text(strip=True)
                break
        
        return details
        
    except Exception as e:
        print(f"Error scraping movie details: {e}")
        return None

def main():
    title = input("Please enter movie name: ")
    
    try:
        movies = scrape_tmdb_movies(title)
        
        if not movies:
            print("No movies found!")
            return
        
        print(f"\nFound {len(movies)} movies:\n")
        
        for i, movie in enumerate(movies, 1):
            print(f"{i}. {movie.get('title', 'N/A')} ({movie.get('release_date', 'N/A')})")
        
        # Ask user to select a movie for detailed scraping
        selection = input("\nEnter the number of the movie you want to scrape details for (or 'all' for all movies): ")
        
        if selection.lower() == 'all':
            # Scrape details for all movies
            detailed_movies = []
            for i, movie in enumerate(movies, 1):
                print(f"Scraping details for movie {i}/{len(movies)}: {movie.get('title', 'N/A')}")
                if 'url' in movie:
                    details = scrape_movie_details(movie['url'])
                    if details:
                        # Merge basic and detailed info
                        merged_info = {**movie, **details}
                        detailed_movies.append(merged_info)
            
            # Save all detailed results
            filename = f"tmdb_{title.replace(' ', '_')}_detailed_results.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(detailed_movies, f, indent=2, ensure_ascii=False)
            print(f"All detailed results saved to {filename}")
            
        else:
            try:
                selection_idx = int(selection) - 1
                if 0 <= selection_idx < len(movies):
                    selected_movie = movies[selection_idx]
                    print(f"\nScraping details for: {selected_movie.get('title', 'N/A')}")
                    
                    if 'url' in selected_movie:
                        details = scrape_movie_details(selected_movie['url'])
                        if details:
                            # Merge basic and detailed info
                            merged_info = {**selected_movie, **details}
                            
                            # Display the detailed information
                            print("\nDetailed Movie Information:")
                            print("=" * 50)
                            for key, value in merged_info.items():
                                if key == 'cast':
                                    print("Cast:")
                                    for i, actor in enumerate(value, 1):
                                        print(f"  {i}. {actor.get('name', 'N/A')} as {actor.get('character', 'N/A')}")
                                        if 'profile_url' in actor:
                                            print(f"     Profile: {actor['profile_url']}")
                                elif key == 'logo_urls':
                                    print("Logos:")
                                    for i, logo_url in enumerate(value, 1):
                                        print(f"  {i}. {logo_url}")
                                elif key == 'backdrop_urls':
                                    print("Backdrops:")
                                    for i, backdrop_url in enumerate(value, 1):
                                        print(f"  {i}. {backdrop_url}")
                                elif key == 'additional_poster_urls':
                                    print("Additional Posters:")
                                    for i, poster_url in enumerate(value, 1):
                                        print(f"  {i}. {poster_url}")
                                elif key == 'trailers':
                                    print("Trailers:")
                                    for i, trailer in enumerate(value, 1):
                                        print(f"  {i}. {trailer.get('title', 'N/A')}")
                                        print(f"     YouTube ID: {trailer.get('youtube_id', 'N/A')}")
                                        print(f"     YouTube URL: {trailer.get('youtube_url', 'N/A')}")
                                        print(f"     Details: {trailer.get('details', 'N/A')}")
                                        print(f"     Site: {trailer.get('site', 'N/A')}")
                                        if 'channel' in trailer:
                                            print(f"     Channel: {trailer['channel']}")
                                elif isinstance(value, list):
                                    print(f"{key.replace('_', ' ').title()}: {', '.join(value)}")
                                else:
                                    print(f"{key.replace('_', ' ').title()}: {value}")
                            
                            # Ask if user wants to save the detailed information
                            save = input("\nDo you want to save the detailed results to a JSON file? (y/n): ")
                            if save.lower() == 'y':
                                filename = f"tmdb_{selected_movie.get('title', 'unknown').replace(' ', '_')}_details.json"
                                with open(filename, 'w', encoding='utf-8') as f:
                                    json.dump(merged_info, f, indent=2, ensure_ascii=False)
                                print(f"Detailed results saved to {filename}")
                        else:
                            print("Failed to scrape detailed information.")
                    else:
                        print("No URL found for the selected movie.")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number or 'all'.")
            
    except requests.RequestException as e:
        print(f"Error making request: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
