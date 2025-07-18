"""
Game Data Analyzer Module

This module processes and analyzes game data from the Steam API.
"""

import datetime
from typing import Dict, List, Tuple, Any

class GameDataAnalyzer:
    """
    Analyzes game data from the Steam API.
    """
    
    def __init__(self, game_data: Dict):
        """
        Initialize the analyzer with game data.
        
        Args:
            game_data: Raw game data from the Steam API
        """
        self.game_data = game_data
        self.games = game_data.get("games", [])
        self.game_count = game_data.get("game_count", 0)
    
    def _minutes_to_hours(self, minutes: int) -> float:
        """Convert minutes to hours with one decimal place."""
        return round(minutes / 60, 1)
    
    def _format_timestamp(self, timestamp: int) -> str:
        """Convert Unix timestamp to human-readable date."""
        if timestamp == 0:
            return "Never"
        
        date = datetime.datetime.fromtimestamp(timestamp)
        return date.strftime("%b %d, %Y")
    
    def get_total_playtime(self) -> float:
        """
        Calculate total playtime across all games.
        
        Returns:
            float: Total playtime in hours
        """
        total_minutes = sum(game.get("playtime_forever", 0) for game in self.games)
        return self._minutes_to_hours(total_minutes)
    
    def get_most_played_games(self, limit: int = 10) -> List[Dict]:
        """
        Get the most played games.
        
        Args:
            limit: Number of games to return
            
        Returns:
            List[Dict]: List of games with playtime information
        """
        sorted_games = sorted(
            self.games, 
            key=lambda x: x.get("playtime_forever", 0), 
            reverse=True
        )
        
        top_games = []
        for game in sorted_games[:limit]:
            top_games.append({
                "name": game.get("name", "Unknown Game"),
                "appid": game.get("appid", 0),
                "playtime_hours": self._minutes_to_hours(game.get("playtime_forever", 0)),
                "last_played": self._format_timestamp(game.get("rtime_last_played", 0))
            })
        
        return top_games
    
    def get_unplayed_games(self) -> List[Dict]:
        """
        Get games with less than 1 hour of playtime.
        
        Returns:
            List[Dict]: List of unplayed games
        """
        unplayed = []
        for game in self.games:
            if game.get("playtime_forever", 0) < 60:  # Less than 60 minutes
                unplayed.append({
                    "name": game.get("name", "Unknown Game"),
                    "appid": game.get("appid", 0),
                    "playtime_hours": self._minutes_to_hours(game.get("playtime_forever", 0)),
                    "last_played": self._format_timestamp(game.get("rtime_last_played", 0))
                })
        
        return unplayed
    
    def get_recently_played_games(self, days: int = 30) -> List[Dict]:
        """
        Get games played within the specified number of days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List[Dict]: List of recently played games
        """
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_timestamp = int(cutoff_time.timestamp())
        
        recent_games = []
        for game in self.games:
            last_played = game.get("rtime_last_played", 0)
            if last_played > cutoff_timestamp:
                recent_games.append({
                    "name": game.get("name", "Unknown Game"),
                    "appid": game.get("appid", 0),
                    "playtime_hours": self._minutes_to_hours(game.get("playtime_forever", 0)),
                    "last_played": self._format_timestamp(last_played)
                })
        
        return sorted(recent_games, key=lambda x: x["last_played"], reverse=True)
    
    def get_neglected_games(self, days: int = 365) -> List[Dict]:
        """
        Get games that haven't been played in a long time but have significant playtime.
        
        Args:
            days: Number of days to consider as "neglected"
            
        Returns:
            List[Dict]: List of neglected games
        """
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_timestamp = int(cutoff_time.timestamp())
        
        neglected_games = []
        for game in self.games:
            last_played = game.get("rtime_last_played", 0)
            playtime = game.get("playtime_forever", 0)
            
            # Only consider games with at least 2 hours of playtime
            if playtime >= 120 and last_played > 0 and last_played < cutoff_timestamp:
                neglected_games.append({
                    "name": game.get("name", "Unknown Game"),
                    "appid": game.get("appid", 0),
                    "playtime_hours": self._minutes_to_hours(playtime),
                    "last_played": self._format_timestamp(last_played),
                    "days_since_played": (datetime.datetime.now() - 
                                         datetime.datetime.fromtimestamp(last_played)).days
                })
        
        return sorted(neglected_games, key=lambda x: x["playtime_hours"], reverse=True)
    
    def get_library_summary(self) -> Dict:
        """
        Get a summary of the user's game library.
        
        Returns:
            Dict: Summary statistics
        """
        if not self.games:
            return {
                "total_games": 0,
                "total_playtime": 0,
                "most_played_game": None,
                "unplayed_count": 0,
                "played_count": 0,
                "average_playtime": 0
            }
        
        most_played = max(self.games, key=lambda x: x.get("playtime_forever", 0))
        unplayed_count = sum(1 for game in self.games if game.get("playtime_forever", 0) < 60)
        played_count = self.game_count - unplayed_count
        
        total_playtime = self.get_total_playtime()
        average_playtime = total_playtime / played_count if played_count > 0 else 0
        
        return {
            "total_games": self.game_count,
            "total_playtime": total_playtime,
            "most_played_game": {
                "name": most_played.get("name", "Unknown Game"),
                "playtime_hours": self._minutes_to_hours(most_played.get("playtime_forever", 0))
            },
            "unplayed_count": unplayed_count,
            "played_count": played_count,
            "average_playtime": round(average_playtime, 1)
        }
