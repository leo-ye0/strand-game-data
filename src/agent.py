"""
Steam Stats Agent Module

This module defines the Strands agent for analyzing Steam game data.
"""

import os
import logging
import re
from typing import Dict, List, Optional, Union, Any

from dotenv import load_dotenv
from strands import Agent, tool
from strands.models import BedrockModel

from .steam_api_handler import SteamAPIHandler
from .game_data_analyzer import GameDataAnalyzer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s"
)
logger = logging.getLogger("steam-stats-agent")

class SteamStatsAgent:
    """
    Agent for analyzing Steam game library data.
    """
    
    def __init__(self):
        """Initialize the Steam Stats Agent."""
        self.steam_api = SteamAPIHandler()
        self.library_data = None
        self.analysis_data = None
        self.game_analyzer = None
        self.agent = None
    
    def initialize_agent(self) -> Agent:
        """
        Create and configure the Strands agent.
        
        Returns:
            Agent: Configured Strands agent
        """
        # Use the new method that checks for available models
        return self.initialize_agent_with_available_model()
    
    def check_available_models(self) -> List[str]:
        """
        Check which Bedrock models are available in the user's AWS account.
        
        Returns:
            List[str]: List of available model IDs
        """
        try:
            import boto3
            
            bedrock = boto3.client('bedrock', region_name='us-east-1')
            response = bedrock.list_foundation_models()
            
            available_models = []
            for model in response.get('modelSummaries', []):
                if model.get('modelLifecycle', {}).get('status') == 'ACTIVE':
                    available_models.append(model.get('modelId'))
            
            return available_models
        except Exception as e:
            logger.error(f"Error checking available models: {str(e)}", exc_info=True)
            return []
    
    def initialize_agent_with_model_id(self, model_id: str) -> Agent:
        """
        Initialize the agent with a specific model ID.
        
        Args:
            model_id: The Bedrock model ID to use
            
        Returns:
            Agent: Configured Strands agent
        """
        if self.agent is not None:
            return self.agent
            
        # Configure the model with the specified ID
        model = BedrockModel(
            model_id=model_id,
            region_name="us-east-1"
        )
        
        # Create the agent with our custom tools
        self.agent = Agent(
            model=model,
            tools=[
                self.get_total_game_count,
                self.get_total_playtime,
                self.get_most_played_games,
                self.get_least_played_games,
                self.list_unplayed_games,
                self.find_game_stats,
                self.get_recently_played_games,
                self.get_neglected_games,
                self.get_library_summary,
                self.get_game_info,
                self.summarize_player_reviews
            ],
            system_prompt="""
            You are the Steam Stats Agent, an AI assistant specialized in analyzing Steam game libraries.
            Your purpose is to help users understand their gaming habits by providing insights about their
            Steam game collection, playtime statistics, and gaming patterns.
            
            When interacting with users:
            - Be friendly and enthusiastic about gaming
            - Provide clear, concise analysis of their game library
            - Highlight interesting patterns in their gaming habits
            - Format data in an easy-to-read manner
            - Use gaming terminology appropriately
            - Be conversational and engaging
            
            You have access to tools that can analyze the user's Steam game library data.
            The data has already been loaded, so you can answer questions immediately.
            
            When users ask about their games, use the appropriate tool to get the information.
            For example:
            - "How many games do I have?" -> use get_total_game_count
            - "What are my most played games?" -> use get_most_played_games
            - "How many hours have I played Elden Ring?" -> use find_game_stats with "Elden Ring"
            
            If the user types "exit", "quit", or "bye", thank them and end the conversation.
            """
        )
        
        return self.agent
            
    def initialize_agent_with_available_model(self) -> Agent:
        """
        Initialize the agent with the first available model from a list of preferred models.
        
        Returns:
            Agent: Configured Strands agent
        """
        if self.agent is not None:
            return self.agent
            
        # List of models to try, in order of preference
        preferred_models = [
            "amazon.nova-pro-v1:0",  # Use Nova Pro as the primary model
            "amazon.nova-pro-v1:0:24k",
            "amazon.nova-pro-v1:0:300k"
        ]
        
        # Get available models
        available_models = self.check_available_models()
        
        # Find the first preferred model that's available
        model_id = None
        for preferred in preferred_models:
            if preferred in available_models:
                model_id = preferred
                break
        
        # If no preferred model is available, use the first available model
        if not model_id and available_models:
            model_id = available_models[0]
        
        # If no models are available, use a default model and hope for the best
        if not model_id:
            model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
            
        return self.initialize_agent_with_model_id(model_id)

    def load_user_data(self, steam_id_or_vanity: str) -> Dict:
        """
        Load a user's Steam game library data.
        
        Args:
            steam_id_or_vanity: Either a 64-bit SteamID or a vanity URL name
            
        Returns:
            Dict: Status of the data loading operation
        """
        try:
            # Validate and normalize the input
            steam_id, is_vanity = self.steam_api.validate_steam_id(steam_id_or_vanity)
            
            # Get the user's owned games
            game_data = self.steam_api.get_owned_games(steam_id)
            
            # Get player profile information
            player_info = self.steam_api.get_player_summaries(steam_id)
            
            # Store the library data
            self.library_data = {
                "steam_id": steam_id,
                "player_info": player_info,
                "game_data": game_data
            }
            
            # Initialize the game analyzer
            self.game_analyzer = GameDataAnalyzer(game_data)
            
            # Analyze the data
            self.analysis_data = {
                "steam_id": steam_id,
                "player_info": player_info,
                "summary": self.game_analyzer.get_library_summary(),
                "most_played": self.game_analyzer.get_most_played_games(10),
                "unplayed": self.game_analyzer.get_unplayed_games(),
                "recently_played": self.game_analyzer.get_recently_played_games(30),
                "neglected": self.game_analyzer.get_neglected_games(365)
            }
            
            return {
                "success": True,
                "player_name": player_info.get("personaname", "Unknown Player"),
                "game_count": game_data.get("game_count", 0)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def chat(self, user_input: str) -> None:
        """
        Process a user's chat message.
        
        Args:
            user_input: The user's message
        """
        if not self.agent:
            print("Error: Agent not initialized. Please load your game data first.")
            return
        
        if not self.analysis_data:
            print("Error: No game data loaded. Please load your game data first.")
            return
        
        # Check for exit commands
        if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
            print("Thanks for chatting! Goodbye!")
            return
        
        try:
            # Just process the message with the agent and let it handle the output
            self.agent(user_input)
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            print(f"I encountered an error: {str(e)}")
    
    @tool
    def get_total_game_count(self) -> Dict:
        """
        Get the total number of games in the user's library.
        
        Returns:
            Dict: Total game count information
        """
        if not self.analysis_data:
            return {"error": "No game data loaded"}
        
        summary = self.analysis_data["summary"]
        return {
            "total_games": summary["total_games"],
            "played_games": summary["played_count"],
            "unplayed_games": summary["unplayed_count"]
        }
    
    @tool
    def get_total_playtime(self) -> Dict:
        """
        Get the total playtime across all games.
        
        Returns:
            Dict: Total playtime information
        """
        if not self.analysis_data:
            return {"error": "No game data loaded"}
        
        summary = self.analysis_data["summary"]
        return {
            "total_hours": summary["total_playtime"],
            "average_hours_per_game": summary["average_playtime"]
        }
    
    @tool
    def get_most_played_games(self, top_n: int = 5) -> Dict:
        """
        Get the most played games.
        
        Args:
            top_n: Number of games to return (default: 5)
            
        Returns:
            Dict: Most played games information
        """
        if not self.game_analyzer:
            return {"error": "No game data loaded"}
        
        # Ensure top_n is a reasonable number
        try:
            top_n = int(top_n)
            if top_n <= 0:
                top_n = 5
        except (ValueError, TypeError):
            top_n = 5
        
        most_played = self.game_analyzer.get_most_played_games(top_n)
        return {
            "games": most_played,
            "count": len(most_played)
        }
    
    @tool
    def get_least_played_games(self, top_n: int = 5) -> Dict:
        """
        Get the least played games that have more than 0 playtime.
        
        Args:
            top_n: Number of games to return (default: 5)
            
        Returns:
            Dict: Least played games information
        """
        if not self.game_analyzer or not self.library_data:
            return {"error": "No game data loaded"}
        
        # Ensure top_n is a reasonable number
        try:
            top_n = int(top_n)
            if top_n <= 0:
                top_n = 5
        except (ValueError, TypeError):
            top_n = 5
        
        # Get games with more than 0 playtime
        played_games = [
            game for game in self.library_data["game_data"]["games"]
            if game.get("playtime_forever", 0) > 0
        ]
        
        # Sort by playtime (ascending)
        sorted_games = sorted(
            played_games,
            key=lambda x: x.get("playtime_forever", 0)
        )
        
        # Format the results
        least_played = []
        for game in sorted_games[:top_n]:
            least_played.append({
                "name": game.get("name", "Unknown Game"),
                "appid": game.get("appid", 0),
                "playtime_hours": self.game_analyzer._minutes_to_hours(game.get("playtime_forever", 0)),
                "last_played": self.game_analyzer._format_timestamp(game.get("rtime_last_played", 0))
            })
        
        return {
            "games": least_played,
            "count": len(least_played)
        }
    
    @tool
    def list_unplayed_games(self, limit: int = 10) -> Dict:
        """
        Get games with less than 1 hour of playtime.
        
        Args:
            limit: Maximum number of games to return (default: 10)
            
        Returns:
            Dict: Unplayed games information
        """
        if not self.analysis_data:
            return {"error": "No game data loaded"}
        
        # Ensure limit is a reasonable number
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 10
        except (ValueError, TypeError):
            limit = 10
        
        unplayed = self.analysis_data["unplayed"]
        return {
            "games": unplayed[:limit],
            "total_count": len(unplayed),
            "showing": min(limit, len(unplayed))
        }
    
    @tool
    def find_game_stats(self, game_name: str) -> Dict:
        """
        Find statistics for a specific game by name.
        
        Args:
            game_name: Name of the game to search for
            
        Returns:
            Dict: Game statistics
        """
        if not self.game_analyzer or not self.library_data:
            return {"error": "No game data loaded"}
        
        if not game_name:
            return {"error": "No game name provided"}
        
        # Try to find an exact match first
        for game in self.library_data["game_data"]["games"]:
            if game.get("name", "").lower() == game_name.lower():
                return {
                    "name": game.get("name", "Unknown Game"),
                    "appid": game.get("appid", 0),
                    "playtime_hours": self.game_analyzer._minutes_to_hours(game.get("playtime_forever", 0)),
                    "last_played": self.game_analyzer._format_timestamp(game.get("rtime_last_played", 0)),
                    "found": True
                }
        
        # If no exact match, try a partial match
        matches = []
        for game in self.library_data["game_data"]["games"]:
            if game_name.lower() in game.get("name", "").lower():
                matches.append({
                    "name": game.get("name", "Unknown Game"),
                    "appid": game.get("appid", 0),
                    "playtime_hours": self.game_analyzer._minutes_to_hours(game.get("playtime_forever", 0)),
                    "last_played": self.game_analyzer._format_timestamp(game.get("rtime_last_played", 0))
                })
        
        if matches:
            return {
                "matches": matches,
                "count": len(matches),
                "found": True
            }
        
        return {"found": False, "error": f"Game '{game_name}' not found in your library"}
    
    @tool
    def get_recently_played_games(self, days: int = 30, limit: int = 5) -> Dict:
        """
        Get games played within the specified number of days.
        
        Args:
            days: Number of days to look back (default: 30)
            limit: Maximum number of games to return (default: 5)
            
        Returns:
            Dict: Recently played games information
        """
        if not self.game_analyzer:
            return {"error": "No game data loaded"}
        
        # Ensure parameters are reasonable numbers
        try:
            days = int(days)
            if days <= 0:
                days = 30
        except (ValueError, TypeError):
            days = 30
            
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 5
        except (ValueError, TypeError):
            limit = 5
        
        recent_games = self.game_analyzer.get_recently_played_games(days)
        return {
            "games": recent_games[:limit],
            "total_count": len(recent_games),
            "showing": min(limit, len(recent_games)),
            "days": days
        }
    
    @tool
    def get_neglected_games(self, days: int = 365, limit: int = 5) -> Dict:
        """
        Get games that haven't been played in a long time but have significant playtime.
        
        Args:
            days: Number of days to consider as "neglected" (default: 365)
            limit: Maximum number of games to return (default: 5)
            
        Returns:
            Dict: Neglected games information
        """
        if not self.game_analyzer:
            return {"error": "No game data loaded"}
        
        # Ensure parameters are reasonable numbers
        try:
            days = int(days)
            if days <= 0:
                days = 365
        except (ValueError, TypeError):
            days = 365
            
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 5
        except (ValueError, TypeError):
            limit = 5
        
        neglected_games = self.game_analyzer.get_neglected_games(days)
        return {
            "games": neglected_games[:limit],
            "total_count": len(neglected_games),
            "showing": min(limit, len(neglected_games)),
            "days": days
        }
    
    @tool
    def get_library_summary(self) -> Dict:
        """
        Get a summary of the user's game library.
        
        Returns:
            Dict: Library summary information
        """
        if not self.analysis_data:
            return {"error": "No game data loaded"}
        
        return self.analysis_data["summary"]
    
    @tool
    def get_game_info(self, game_name: str) -> Dict:
        """
        Get detailed information about a specific game, whether owned or not.
        
        Args:
            game_name: Name of the game to look up
            
        Returns:
            Dict: Detailed game information
        """
        # First try to find the game in the user's library
        owned_game = None
        if self.library_data:
            for game in self.library_data["game_data"]["games"]:
                if game.get("name", "").lower() == game_name.lower():
                    owned_game = game
                    break
        
        try:
            if owned_game:
                # Get detailed info for owned game
                details = self.steam_api.get_game_details(owned_game["appid"])
                # Add user's personal stats
                details["owned"] = True
                details["playtime_hours"] = self.game_analyzer._minutes_to_hours(owned_game.get("playtime_forever", 0))
                details["last_played"] = self.game_analyzer._format_timestamp(owned_game.get("rtime_last_played", 0))
            else:
                # Search for the game on Steam
                search_result = self.steam_api.search_game(game_name)
                if not search_result:
                    return {"error": f"Could not find game '{game_name}' on Steam"}
                
                # Get details for the first matching game
                details = self.steam_api.get_game_details(search_result["appid"])
                details["owned"] = False
            
            return {
                "found": True,
                "details": details
            }
        except Exception as e:
            logger.error(f"Error getting game details: {str(e)}")
            if owned_game:
                return {
                    "found": True,
                    "error": "Could not fetch detailed game information",
                    "basic_info": {
                        "name": owned_game.get("name", "Unknown Game"),
                        "appid": owned_game.get("appid", 0),
                        "owned": True,
                        "playtime_hours": self.game_analyzer._minutes_to_hours(owned_game.get("playtime_forever", 0)),
                        "last_played": self.game_analyzer._format_timestamp(owned_game.get("rtime_last_played", 0))
                    }
                }
            return {"error": f"Could not find or fetch information for game '{game_name}'"}
    
    @tool
    def summarize_player_reviews(self, game_name: str, num_reviews: int = 5) -> Dict:
        """
        Get and summarize recent player reviews for any game on Steam.
        
        Args:
            game_name: Name of the game to get reviews for
            num_reviews: Number of recent reviews to analyze (default: 5)
            
        Returns:
            Dict: Review summary and analysis
        """
        # First try to find the game in the user's library
        game_data = None
        if self.library_data:
            for game in self.library_data["game_data"]["games"]:
                if game.get("name", "").lower() == game_name.lower():
                    game_data = game
                    break
        
        try:
            if not game_data:
                # Search for the game on Steam
                search_result = self.steam_api.search_game(game_name)
                if not search_result:
                    return {"error": f"Could not find game '{game_name}' on Steam"}
                game_data = search_result
            
            # Get recent reviews
            reviews = self.steam_api.get_game_reviews(game_data["appid"], num_reviews)
            
            # Count positive and negative reviews
            positive_count = sum(1 for r in reviews if r["voted_up"])
            
            # Extract review texts
            review_texts = [r["text"] for r in reviews]
            
            return {
                "found": True,
                "game_name": game_data["name"],
                "owned": "appid" in game_data,  # True if from library, False if from search
                "review_count": len(reviews),
                "positive_count": positive_count,
                "negative_count": len(reviews) - positive_count,
                "reviews": review_texts
            }
        except Exception as e:
            logger.error(f"Error getting game reviews: {str(e)}")
            return {
                "found": True,
                "error": "Could not fetch review information",
                "game_name": game_data["name"] if game_data else game_name
            }
