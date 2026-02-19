import os
import json
import datetime

class PlayerTracker:
    def __init__(self, fileName="player_data.json"):
        self.player_data_file = fileName
        self.player_data = self._load()

    def _load(self):
        if os.path.exists(self.player_data_file):
            with open(self.player_data_file, "r") as f:
                return json.load(f)
        return {}

    def save(self):
        with open(self.player_data_file, "w") as f:
            json.dump(self.player_data, f, indent=2)

    def update(self, status):
        """Update player times based on server status."""
        current_time = int(datetime.datetime.now().timestamp())
        current_players = set()

        # Only collect names if server shares player list
        if hasattr(status.players, "sample") and status.players.sample:
            current_players = {p.name for p in status.players.sample}

        # Update or start session for online players
        for name in current_players:
            if name not in self.player_data:
                # New player
                self.player_data[name] = {
                    "total_time": 0,
                    "session_start": current_time,
                    "last_seen": current_time
                }
            else:
                player = self.player_data[name]

                # Start session if not already
                if "session_start" not in player:
                    player["session_start"] = current_time

                # Update total_time if last_seen recent
                last_seen = player.get("last_seen", current_time)
                diff = current_time - last_seen
                if diff < 300:  # Only count short gaps to avoid double counting
                    player["total_time"] += diff

                # Update last_seen
                player["last_seen"] = current_time

        # End session for offline players
        for name, player in self.player_data.items():
            if name not in current_players and "session_start" in player:
                # Mark session as ended by removing session_start
                del player["session_start"]

        self.save()

    def top_players(self, limit=10):
        """Return top N players sorted by total_time."""
        sorted_players = sorted(
            self.player_data.items(),
            key=lambda x: x[1].get("total_time", 0),
            reverse=True
        )
        return sorted_players[:limit]

    def get_player_info(self, name):
        """Return detailed info about a player."""
        player = self.player_data.get(name)
        if not player:
            return None

        info = {
            "total_time": player.get("total_time", 0),
            "last_seen": player.get("last_seen"),
            "current_session": None
        }

        if "session_start" in player:
            # Player is currently online
            info["current_session"] = int(datetime.datetime.now().timestamp()) - player["session_start"]

        return info
