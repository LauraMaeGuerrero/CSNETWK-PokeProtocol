"""Pokemon data management and battle calculations"""
import csv
import os
import random
from typing import Dict, Any, Optional
from utils import safe_float, safe_int

# Configuration
CSV_PATH = os.path.join(os.path.dirname(__file__), "pokemon.csv")

# Minimal test moveset
MOVES = {
    "Tackle": {"name": "Tackle", "type": "Normal", "power": 40, "damage_category": "physical"},
    "Quick Attack": {"name": "Quick Attack", "type": "Normal", "power": 40, "damage_category": "physical"},
    "Scratch": {"name": "Scratch", "type": "Normal", "power": 40, "damage_category": "physical"},
    "Ember": {"name": "Ember", "type": "Fire", "power": 40, "damage_category": "special"},
    "Water Gun": {"name": "Water Gun", "type": "Water", "power": 40, "damage_category": "special"},
    "Thunderbolt": {"name": "Thunderbolt", "type": "Electric", "power": 90, "damage_category": "special"},
    "Vine Whip": {"name": "Vine Whip", "type": "Grass", "power": 45, "damage_category": "physical"},
}


class PokemonManager:
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            csv_path = CSV_PATH
        self.csv_path = csv_path
        self.pokemon_db = self.load_pokemon(csv_path)
        self.moves_by_pokemon = self.generate_movesets(self.pokemon_db, MOVES)

    def load_pokemon(self, csv_file: str) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV not found: {csv_file}")
        out = {}
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # normalize keys (some CSVs may contain leading/trailing spaces)
                row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                # numeric stats
                for s in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']:
                    row[s] = safe_int(row.get(s))
                # floats
                for s in ['weight_kg', 'height_m', 'base_total', 'base_egg_steps', 
                         'base_happiness', 'experience_growth', 'capture_rate']:
                    row[s] = safe_float(row.get(s))
                # types
                row['types'] = (row.get('type1') or None, row.get('type2') or None)
                # build type effectiveness mapping from against_* columns
                te = {}
                for k, v in row.items():
                    if k.startswith('against_'):
                        move_type = k.replace('against_', '').capitalize()
                        te[move_type] = safe_float(v)
                row['type_effectiveness'] = te
                out[row['name']] = row
        return out

    def generate_movesets(self, pokemon_db: Dict[str, Dict[str, Any]], 
                         moves_defs: Dict[str, Dict[str, Any]], 
                         per_pokemon_max: int = 4) -> Dict[str, list]:
        """Generate a simple per-pokemon moveset mapping."""
        common_moves = [m for m in moves_defs.keys() if m in ("Tackle", "Quick Attack", "Scratch")]
        moves_by_pokemon = {}
        for name, row in pokemon_db.items():
            types = [t for t in (row.get('type1'), row.get('type2')) if t]
            preferred = [m for m, md in moves_defs.items() 
                        if md.get('type') and md['type'].lower() in [t.lower() for t in types]]
            preferred.sort(key=lambda mn: moves_defs[mn].get('power', 0), reverse=True)
            picks = []
            for m in preferred:
                if m not in picks:
                    picks.append(m)
                if len(picks) >= per_pokemon_max:
                    break
            for m in common_moves:
                if len(picks) >= per_pokemon_max:
                    break
                if m not in picks:
                    picks.append(m)
            if len(picks) < per_pokemon_max:
                others = sorted(moves_defs.keys(), 
                              key=lambda mn: moves_defs[mn].get('power', 0), reverse=True)
                for m in others:
                    if m not in picks:
                        picks.append(m)
                    if len(picks) >= per_pokemon_max:
                        break
            moves_by_pokemon[name] = picks
        return moves_by_pokemon

    def get_type_multiplier(self, move_type: str, defender_row: Dict[str, Any]) -> float:
        if not move_type:
            return 1.0
        move_type = move_type.capitalize()
        multiplier = 1.0
        for dt in defender_row['types']:
            if not dt:
                continue
            val = defender_row['type_effectiveness'].get(move_type)
            if val is None:
                val = 1.0
            multiplier *= val
        return multiplier

    def calculate_damage(self, attacker_row: Dict[str, Any], 
                        defender_row: Dict[str, Any], 
                        move: Dict[str, Any]) -> int:
        category = move.get('damage_category', 'physical')
        if category == 'physical':
            atk = attacker_row['attack']
            defn = defender_row['defense']
        else:
            atk = attacker_row['sp_attack']
            defn = defender_row['sp_defense']
        power = move.get('power', 50)
        type_mult = self.get_type_multiplier(move.get('type', ''), defender_row)
        raw = ((atk / max(defn, 1.0)) * power) * type_mult
        return max(1, int(round(raw)))

    def get_pokemon_list(self, limit: int = 20) -> list:
        return list(self.pokemon_db.keys())[:limit]

    def get_pokemon(self, name: str) -> Optional[Dict[str, Any]]:
        return self.pokemon_db.get(name)

    def get_moves_for_pokemon(self, pokemon_name: str) -> list:
        return self.moves_by_pokemon.get(pokemon_name, list(MOVES.keys()))