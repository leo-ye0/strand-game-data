"""
Steam API Handler

This module handles all interactions with the Steam Web API.
"""

import os
import time
from typing import Dict, List, Tuple, Optional, Union
import logging

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SteamAPIHandler:
    """Handler for Steam Web API interactions."""
    
    def __init__(self):
        """Initialize the Steam API handler."""
        self.api_key = os.getenv("STEAM_API_KEY")
        if not self.api_key:
            raise ValueError("Steam API key not found in environment variables")
        
        self.base_url = "https://api.steampowered.com"
        self.store_url = "https://store.steampowered.com/api"
        
        # Add rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds
    
    def _rate_limit(self) -> None:
        """Implement basic rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def validate_steam_id(self, steam_id_or_vanity: str) -> Tuple[str, bool]:
        """
        Validate and convert a Steam ID or vanity URL to a 64-bit Steam ID.
        
        Args:
            steam_id_or_vanity: Either a 64-bit SteamID or vanity URL name
            
        Returns:
            Tuple[str, bool]: (steam_id, is_vanity)
            
        Raises:
            ValueError: If the Steam ID is invalid or profile is private
        """
        # Check if it's a 64-bit Steam ID
        if steam_id_or_vanity.isdigit() and len(steam_id_or_vanity) == 17:
            return steam_id_or_vanity, False
        
        # Try resolving as vanity URL
        self._rate_limit()
        response = requests.get(
            f"{self.base_url}/ISteamUser/ResolveVanityURL/v1/",
            params={
                "key": self.api_key,
                "vanityurl": steam_id_or_vanity
            }
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to validate Steam ID: {response.status_code}")
        
        data = response.json()
        if data["response"]["success"] == 1:
            return data["response"]["steamid"], True
        
        raise ValueError("Invalid Steam ID or vanity URL")
    
    def get_owned_games(self, steam_id: str) -> Dict:
        """
        Get a user's owned games.
        
        Args:
            steam_id: 64-bit Steam ID
            
        Returns:
            Dict: Game library data
            
        Raises:
            ValueError: If the request fails or profile is private
        """
        self._rate_limit()
        response = requests.get(
            f"{self.base_url}/IPlayerService/GetOwnedGames/v1/",
            params={
                "key": self.api_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1
            }
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get owned games: {response.status_code}")
        
        data = response.json()
        if "response" not in data or "games" not in data["response"]:
            raise ValueError("Failed to get game data. Profile might be private.")
        
        return {
            "game_count": data["response"].get("game_count", 0),
            "games": data["response"]["games"]
        }
    
    def get_player_summaries(self, steam_id: str) -> Dict:
        """
        Get a player's profile information.
        
        Args:
            steam_id: 64-bit Steam ID
            
        Returns:
            Dict: Player profile data
            
        Raises:
            ValueError: If the request fails
        """
        self._rate_limit()
        response = requests.get(
            f"{self.base_url}/ISteamUser/GetPlayerSummaries/v2/",
            params={
                "key": self.api_key,
                "steamids": steam_id
            }
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get player summary: {response.status_code}")
        
        data = response.json()
        if not data["response"]["players"]:
            raise ValueError("Player not found or profile is private")
        
        return data["response"]["players"][0]
    
    def get_game_details(self, appid: int) -> Dict:
        """
        Get detailed information about a game from the Steam Store API.
        
        Args:
            appid: Steam App ID
            
        Returns:
            Dict: Game details including description, developers, release date, etc.
            
        Raises:
            ValueError: If the request fails or game data is not available
        """
        self._rate_limit()
        response = requests.get(
            f"{self.store_url}/appdetails",
            params={
                "appids": appid,
                "cc": "us",  # Country code for pricing
                "l": "english"  # Language
            }
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get game details: {response.status_code}")
        
        data = response.json()
        if str(appid) not in data or not data[str(appid)]["success"]:
            raise ValueError("Game details not available")
        
        game_data = data[str(appid)]["data"]
        return {
            "name": game_data.get("name", "Unknown"),
            "short_description": game_data.get("short_description", "No description available"),
            "developers": game_data.get("developers", []),
            "publishers": game_data.get("publishers", []),
            "release_date": game_data.get("release_date", {}).get("date", "Unknown"),
            "genres": [genre["description"] for genre in game_data.get("genres", [])],
            "metacritic": game_data.get("metacritic", {}).get("score"),
            "header_image": game_data.get("header_image"),
            "categories": [cat["description"] for cat in game_data.get("categories", [])]
        }
    
    def get_game_reviews(self, appid: int, num_reviews: int = 5) -> List[Dict]:
        """
        Get recent reviews for a game from the Steam Store API.
        
        Args:
            appid: Steam App ID
            num_reviews: Number of reviews to fetch (default: 5)
            
        Returns:
            List[Dict]: List of recent reviews with text and other metadata
            
        Raises:
            ValueError: If the request fails or reviews are not available
        """
        self._rate_limit()
        
        # Set up proper headers to mimic a web browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Referer': f'https://store.steampowered.com/app/{appid}'
        }
        
        response = requests.get(
            f"https://store.steampowered.com/appreviews/{appid}",
            params={
                'json': 1,
                'filter': 'recent',
                'language': 'english',
                'day_range': 30,  # Get reviews from last 30 days
                'num_per_page': num_reviews,
                'purchase_type': 'all',
                'cursor': '*',
                'review_type': 'all'
            },
            headers=headers
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get game reviews: {response.status_code}")
        
        data = response.json()
        if not data.get("success", 0):
            raise ValueError("Reviews not available")
        
        reviews = []
        for review in data.get("reviews", []):
            reviews.append({
                "text": review.get("review", ""),
                "voted_up": review.get("voted_up", False),
                "playtime_at_review": review.get("author", {}).get("playtime_at_review", 0),
                "timestamp_created": review.get("timestamp_created", 0),
                "playtime_forever": review.get("author", {}).get("playtime_forever", 0)
            })
        
        return reviews[:num_reviews]
    def search_game(self, game_name: str) -> Optional[Dict]:
        """
        Search for a game on the Steam store.
        
        Args:
            game_name: Name of the game to search for
            
        Returns:
            Optional[Dict]: Game information if found, None otherwise
            
        Raises:
            ValueError: If the request fails
        """
        self._rate_limit()
        response = requests.get(
            "https://store.steampowered.com/api/storesearch",
            params={
                "term": game_name,
                "l": "english",
                "cc": "us"
            }
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to search for game: {response.status_code}")
        
        data = response.json()
        if not data.get("total", 0) or not data.get("items"):
            return None
        
        # Return the first matching game
        game = data["items"][0]
        return {
            "appid": game["id"],
            "name": game["name"],
            "type": game.get("type", "game")
        }
