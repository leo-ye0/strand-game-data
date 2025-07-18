#!/usr/bin/env python3
"""
Steam Stats Agent CLI

This script provides a command-line interface for the Steam Stats Agent.
"""

import os
import sys
import csv
import argparse
import time
import logging
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from colorama import init, Fore, Style
from tabulate import tabulate
from tqdm import tqdm

from src.agent import SteamStatsAgent

# Initialize colorama
init(autoreset=True)

# ASCII art banner
BANNER = r"""
 ____  _                         ____  _        _         _                      _   
/ ___|| |_ ___  __ _ _ __ ___   / ___|| |_ __ _| |_ ___  / \   __ _  ___ _ __  | |_ 
\___ \| __/ _ \/ _` | '_ ` _ \  \___ \| __/ _` | __/ __| / _ \ / _` |/ _ \ '_ \ | __|
 ___) | ||  __/ (_| | | | | | |  ___) | || (_| | |_\__ \/ ___ \ (_| |  __/ | | || |_ 
|____/ \__\___|\__,_|_| |_| |_| |____/ \__\__,_|\__|___/_/   \_\__, |\___|_| |_| \__|
                                                               |___/                  
"""

def print_header(text: str) -> None:
    """Print a formatted section header."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{text}")
    print(f"{Fore.CYAN}{'═' * len(text)}{Style.RESET_ALL}")

def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Fore.RED}{Style.BRIGHT}Error: {text}{Style.RESET_ALL}")

def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Fore.YELLOW}{Style.BRIGHT}⚠️  {text}{Style.RESET_ALL}")

def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Fore.GREEN}{Style.BRIGHT}{text}{Style.RESET_ALL}")

def print_agent_message(text: str) -> None:
    """Print an agent message."""
    # If the text already contains "Agent >", just print it as is
    if "Agent >" in text:
        print(text)
    else:
        print(f"{Fore.BLUE}Agent > {Style.RESET_ALL}{text}")

def print_user_prompt() -> None:
    """Print the user prompt."""
    print(f"{Fore.GREEN}You > {Style.RESET_ALL}", end="")

def format_hours(hours: float) -> str:
    """Format hours with commas for thousands."""
    return f"{hours:,.1f}"

def export_to_csv(data: Dict, filename: str = "steam_library.csv") -> None:
    """
    Export game data to a CSV file.
    
    Args:
        data: Report data from the agent
        filename: Output CSV filename
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Game', 'Hours Played', 'Last Played']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for game in data["top_games"] + data["unplayed_games"]:
                writer.writerow({
                    'Game': game['name'],
                    'Hours Played': game['playtime_hours'],
                    'Last Played': game['last_played']
                })
        
        print_success(f"Game library exported to {filename}")
    except Exception as e:
        print_error(f"Failed to export CSV: {e}")

def interactive_chat_loop(agent: SteamStatsAgent) -> None:
    """
    Run an interactive chat loop with the agent.
    
    Args:
        agent: The initialized Steam Stats Agent
    """
    print_success("✅ Analysis complete! I'm ready. Ask me anything about your game library.")
    
    while True:
        # Add a newline before the prompt
        print()
        print_user_prompt()
        user_input = input()
        
        if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
            print("Thanks for chatting! Goodbye!")
            break
        
        try:
            # Let the agent handle the output directly
            agent.chat(user_input)
        except Exception as e:
            print_error(f"An error occurred: {e}")

def main() -> None:
    """Main entry point for the CLI."""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Steam Stats Agent - Analyze your Steam game library")
    parser.add_argument("--id", help="Steam ID or vanity URL")
    parser.add_argument("--export", action="store_true", help="Export game list to CSV")
    parser.add_argument("--report", action="store_true", help="Generate a one-time report instead of interactive chat")
    parser.add_argument("--check-models", action="store_true", help="Check available Bedrock models")
    parser.add_argument("--model-id", help="Specify a Bedrock model ID to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        logging.getLogger("strands").setLevel(logging.DEBUG)
        logging.getLogger("botocore").setLevel(logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)
    
    # Print banner
    print(f"{Fore.CYAN}{BANNER}{Style.RESET_ALL}")
    print_header("🎮 STEAM STATS AGENT")
    
    # Check for Steam API key
    steam_api_key = os.getenv("STEAM_API_KEY")
    if not steam_api_key:
        print_error("Steam API key not found!")
        print("Please get your API key from https://steamcommunity.com/dev/apikey")
        print("Then add it to your .env file as STEAM_API_KEY=your_key_here")
        return
    
    # Get Steam ID or vanity URL
    steam_id = args.id
    if not steam_id:
        steam_id = input(f"{Fore.CYAN}Enter your Steam ID or vanity URL: {Style.RESET_ALL}")
    
    if not steam_id:
        print_error("No Steam ID provided. Exiting.")
        return
    
    # Initialize the agent
    try:
        agent = SteamStatsAgent()
        
        # Check available models if requested
        if args.check_models:
            print_header("CHECKING AVAILABLE BEDROCK MODELS")
            available_models = agent.check_available_models()
            
            if available_models:
                print_success(f"Found {len(available_models)} available models:")
                for model in available_models:
                    print(f"- {model}")
                return
            else:
                print_error("No available models found or error accessing Bedrock.")
                print("Please check your AWS credentials and Bedrock access.")
                return
    except Exception as e:
        print_error(f"Failed to initialize agent: {e}")
        return
    
    # Load the user's game data
    print(f"\n🔍 Analyzing your Steam library for: {Fore.GREEN}{steam_id}{Style.RESET_ALL}")
    
    with tqdm(total=2, desc="Loading data", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        try:
            # Step 1: Load the user's game data
            pbar.set_description("Fetching game library")
            result = agent.load_user_data(steam_id)
            
            if not result.get("success", False):
                error_msg = result.get("error", "Failed to load game data")
                print_error(error_msg)
                
                # Provide more helpful guidance based on the error
                if "Invalid SteamID" in error_msg or "private profile" in error_msg:
                    print("\nPossible solutions:")
                    print("1. Make sure your Steam profile is set to public")
                    print("   - Open Steam > Profile > Edit Profile > Privacy Settings")
                    print("   - Set 'My profile' and 'Game details' to 'Public'")
                    print("2. Double-check your Steam ID or vanity URL")
                    print("3. Try using a Steam ID finder website like https://steamid.io/")
                
                return
            
            pbar.update(1)
            
            # Step 2: Initialize the agent
            pbar.set_description("Initializing agent")
            if args.model_id:
                # If a specific model ID is provided, use it directly
                print(f"Using specified model: {args.model_id}")
                agent.initialize_agent_with_model_id(args.model_id)
            else:
                # Otherwise use the automatic model selection
                agent.initialize_agent_with_available_model()
            pbar.update(1)
            
            # Print success message with game count
            game_count = result.get("game_count", 0)
            player_name = result.get("player_name", "Unknown Player")
            print(f"\n🎮 Successfully loaded {Fore.GREEN}{game_count}{Style.RESET_ALL} games for {Fore.GREEN}{player_name}{Style.RESET_ALL}")
            
            # Either generate a one-time report or start the interactive chat
            if args.report:
                # Generate a report similar to the original functionality
                print_header("GENERATING REPORT")
                # This is a simplified version of the original report
                summary = agent.get_library_summary()
                most_played = agent.get_most_played_games(10)
                
                print(f"Total Games: {summary['total_games']}")
                print(f"Total Playtime: {format_hours(summary['total_playtime'])} hours")
                print(f"Most Played Game: {summary['most_played_game']['name']} ({format_hours(summary['most_played_game']['playtime_hours'])} hours)")
                
                print_header("TOP GAMES BY PLAYTIME")
                table_data = []
                for game in most_played["games"]:
                    table_data.append([
                        game["name"],
                        format_hours(game["playtime_hours"]),
                        game["last_played"]
                    ])
                
                print(tabulate(
                    table_data,
                    headers=["Game", "Hours Played", "Last Played"],
                    tablefmt="grid"
                ))
                
                # Export to CSV if requested
                if args.export:
                    # Create a simplified version of the original report structure
                    report_data = {
                        "top_games": most_played["games"],
                        "unplayed_games": agent.list_unplayed_games()["games"]
                    }
                    export_to_csv(report_data)
            else:
                # Start the interactive chat loop
                interactive_chat_loop(agent)
                
        except requests.exceptions.RequestException as e:
            print_error(f"Network error: {e}")
        except Exception as e:
            print_error(f"An error occurred: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
