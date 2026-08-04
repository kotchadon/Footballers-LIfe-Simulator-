"""Canonical 2026/27 football-world seed data.

The module contains competition and club identity only. No real-player data is
stored. Ratings are deliberately game ratings, not claims about official club
rankings.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable


@dataclass(frozen=True)
class LeagueSeed:
    code: str
    country: str
    country_code: str
    confederation: str
    name: str
    tier: int
    reputation: int
    promotion_slots: int
    relegation_slots: int
    playoff_slots: int
    clubs: tuple[str, ...]
    fully_playable: bool = True


TOP_FIVE_LEAGUES: tuple[LeagueSeed, ...] = (
    LeagueSeed(
        "ENG1", "England", "ENG", "UEFA", "Premier League", 1, 95, 0, 3, 0,
        (
            "Arsenal", "Aston Villa", "AFC Bournemouth", "Brentford", "Brighton & Hove Albion",
            "Chelsea", "Coventry City", "Crystal Palace", "Everton", "Fulham", "Hull City",
            "Ipswich Town", "Leeds United", "Liverpool", "Manchester City", "Manchester United",
            "Newcastle United", "Nottingham Forest", "Sunderland", "Tottenham Hotspur",
        ),
    ),
    LeagueSeed(
        "ENG2", "England", "ENG", "UEFA", "EFL Championship", 2, 78, 3, 3, 6,
        (
            "Birmingham City", "Blackburn Rovers", "Bolton Wanderers", "Bristol City", "Burnley",
            "Cardiff City", "Charlton Athletic", "Derby County", "Lincoln City", "Middlesbrough",
            "Millwall", "Norwich City", "Portsmouth", "Preston North End", "Queens Park Rangers",
            "Sheffield United", "Southampton", "Stoke City", "Swansea City", "Watford",
            "West Bromwich Albion", "West Ham United", "Wolverhampton Wanderers", "Wrexham",
        ),
    ),
    LeagueSeed(
        "ESP1", "Spain", "ESP", "UEFA", "LALIGA EA SPORTS", 1, 93, 0, 3, 0,
        (
            "Athletic Club", "Atlético de Madrid", "CA Osasuna", "RC Celta", "Deportivo Alavés",
            "Elche CF", "FC Barcelona", "Getafe CF", "Levante UD", "Málaga CF", "Racing de Santander",
            "Rayo Vallecano", "RC Deportivo", "RCD Espanyol", "Real Betis", "Real Madrid",
            "Real Sociedad", "Sevilla FC", "Valencia CF", "Villarreal CF",
        ),
    ),
    LeagueSeed(
        "ESP2", "Spain", "ESP", "UEFA", "LALIGA HYPERMOTION", 2, 75, 3, 4, 4,
        (
            "AD Ceuta FC", "Albacete Balompié", "Burgos CF", "Cádiz CF", "CD Castellón", "CD Eldense",
            "CD Leganés", "CD Tenerife", "CE Sabadell", "Celta Fortuna", "Córdoba CF", "FC Andorra",
            "Girona FC", "Granada CF", "Real Sociedad B", "RCD Mallorca", "Real Oviedo",
            "Real Sporting de Gijón", "Real Valladolid", "SD Eibar", "UD Almería", "UD Las Palmas",
        ),
    ),
    LeagueSeed(
        "ITA1", "Italy", "ITA", "UEFA", "Serie A", 1, 91, 0, 3, 0,
        (
            "AC Milan", "Atalanta", "Bologna", "Cagliari", "Como", "Fiorentina", "Frosinone", "Genoa",
            "Inter", "Juventus", "Lazio", "Lecce", "Monza", "Napoli", "Parma", "Roma", "Sassuolo",
            "Torino", "Udinese", "Venezia",
        ),
    ),
    LeagueSeed(
        "ITA2", "Italy", "ITA", "UEFA", "Serie B", 2, 73, 3, 3, 6,
        (
            "Arezzo", "Ascoli", "Avellino", "Benevento", "Carrarese", "Catanzaro", "Cesena", "Cremonese",
            "Empoli", "Hellas Verona", "Juve Stabia", "Mantova", "Modena", "Padova", "Palermo", "Pisa",
            "Sampdoria", "Südtirol", "Vicenza", "Virtus Entella",
        ),
    ),
    LeagueSeed(
        "GER1", "Germany", "GER", "UEFA", "Bundesliga", 1, 90, 0, 2, 1,
        (
            "FC Bayern München", "Borussia Dortmund", "RB Leipzig", "VfB Stuttgart", "TSG Hoffenheim",
            "Bayer 04 Leverkusen", "SC Freiburg", "Eintracht Frankfurt", "FC Augsburg", "1. FSV Mainz 05",
            "1. FC Union Berlin", "Borussia Mönchengladbach", "Hamburger SV", "1. FC Köln", "Werder Bremen",
            "FC Schalke 04", "SV Elversberg", "SC Paderborn 07",
        ),
    ),
    LeagueSeed(
        "GER2", "Germany", "GER", "UEFA", "2. Bundesliga", 2, 72, 2, 2, 1,
        (
            "Arminia Bielefeld", "VfL Bochum", "Eintracht Braunschweig", "Energie Cottbus", "SV Darmstadt 98",
            "Dynamo Dresden", "Greuther Fürth", "Hannover 96", "1. FC Heidenheim", "Hertha BSC",
            "1. FC Kaiserslautern", "Karlsruher SC", "Holstein Kiel", "1. FC Magdeburg", "1. FC Nürnberg",
            "VfL Osnabrück", "FC St. Pauli", "VfL Wolfsburg",
        ),
    ),
    LeagueSeed(
        "FRA1", "France", "FRA", "UEFA", "Ligue 1", 1, 86, 0, 2, 1,
        (
            "Angers SCO", "AJ Auxerre", "Stade Brestois 29", "Le Havre AC", "Le Mans FC", "RC Lens",
            "FC Lorient", "LOSC Lille", "Olympique Lyonnais", "Olympique de Marseille", "AS Monaco",
            "OGC Nice", "Paris FC", "Paris Saint-Germain", "Stade Rennais", "RC Strasbourg Alsace",
            "Toulouse FC", "ESTAC Troyes",
        ),
    ),
    LeagueSeed(
        "FRA2", "France", "FRA", "UEFA", "Ligue 2", 2, 69, 2, 3, 3,
        (
            "FC Annecy", "US Boulogne", "Clermont Foot", "Dijon FCO", "USL Dunkerque", "Grenoble Foot 38",
            "EA Guingamp", "Stade Lavallois", "FC Metz", "Montpellier HSC", "AS Nancy Lorraine", "FC Nantes",
            "Pau FC", "Red Star FC", "Stade de Reims", "Rodez AF", "AS Saint-Étienne", "FC Sochaux",
        ),
    ),
)


EXPANSION_LEAGUES: tuple[LeagueSeed, ...] = (
    LeagueSeed("POR1", "Portugal", "POR", "UEFA", "Primeira Liga", 1, 78, 0, 2, 1,
        ("Benfica", "FC Porto", "Sporting CP", "Braga", "Vitória de Guimarães", "Boavista", "Famalicão", "Gil Vicente", "Rio Ave", "Moreirense", "Casa Pia", "Estoril", "Arouca", "Santa Clara", "Nacional", "AVS", "Alverca", "Tondela"), False),
    LeagueSeed("NED1", "Netherlands", "NED", "UEFA", "Eredivisie", 1, 77, 0, 2, 1,
        ("Ajax", "PSV", "Feyenoord", "AZ Alkmaar", "FC Twente", "FC Utrecht", "SC Heerenveen", "Sparta Rotterdam", "NEC Nijmegen", "Go Ahead Eagles", "PEC Zwolle", "Fortuna Sittard", "Heracles Almelo", "NAC Breda", "FC Groningen", "Willem II", "Excelsior", "FC Volendam"), False),
    LeagueSeed("SCO1", "Scotland", "SCO", "UEFA", "Scottish Premiership", 1, 67, 0, 1, 1,
        ("Celtic", "Rangers", "Aberdeen", "Hearts", "Hibernian", "Dundee United", "Motherwell", "Kilmarnock", "St Mirren", "Dundee", "Falkirk", "Livingston"), False),
    LeagueSeed("IRL1", "Ireland", "IRL", "UEFA", "League of Ireland Premier Division", 1, 48, 0, 1, 1,
        ("Shamrock Rovers", "Shelbourne", "Bohemians", "St Patrick's Athletic", "Derry City", "Sligo Rovers", "Drogheda United", "Galway United", "Waterford", "Cork City"), False),
    LeagueSeed("USA1", "United States", "USA", "CONCACAF", "Major League Soccer", 1, 71, 0, 0, 0,
        ("Atlanta United", "Austin FC", "Charlotte FC", "Chicago Fire", "FC Cincinnati", "Colorado Rapids", "Columbus Crew", "D.C. United", "FC Dallas", "Houston Dynamo", "Inter Miami", "LA Galaxy", "Los Angeles FC", "Minnesota United", "CF Montréal", "Nashville SC", "New England Revolution", "New York City FC", "New York Red Bulls", "Orlando City", "Philadelphia Union", "Portland Timbers", "Real Salt Lake", "San Diego FC", "San Jose Earthquakes", "Seattle Sounders", "Sporting Kansas City", "St. Louis City", "Toronto FC", "Vancouver Whitecaps"), False),
    LeagueSeed("BRA1", "Brazil", "BRA", "CONMEBOL", "Campeonato Brasileiro Série A", 1, 82, 0, 4, 0,
        ("Flamengo", "Palmeiras", "Corinthians", "São Paulo", "Santos", "Fluminense", "Vasco da Gama", "Botafogo", "Grêmio", "Internacional", "Cruzeiro", "Atlético Mineiro", "Bahia", "Fortaleza", "Athletico Paranaense", "Red Bull Bragantino", "Ceará", "Sport Recife", "Vitória", "Mirassol"), False),
    LeagueSeed("ARG1", "Argentina", "ARG", "CONMEBOL", "Liga Profesional Argentina", 1, 79, 0, 2, 0,
        ("River Plate", "Boca Juniors", "Racing Club", "Independiente", "San Lorenzo", "Vélez Sarsfield", "Estudiantes", "Rosario Central", "Newell's Old Boys", "Talleres", "Belgrano", "Lanús", "Banfield", "Argentinos Juniors", "Defensa y Justicia", "Huracán", "Godoy Cruz", "Unión", "Colón", "Gimnasia La Plata"), False),
    LeagueSeed("KSA1", "Saudi Arabia", "KSA", "AFC", "Saudi Pro League", 1, 76, 0, 3, 0,
        ("Al Hilal", "Al Nassr", "Al Ittihad", "Al Ahli", "Al Ettifaq", "Al Shabab", "Al Taawoun", "Al Fateh", "Al Fayha", "Al Khaleej", "Al Riyadh", "Damac", "Al Raed", "Al Okhdood", "Al Wehda", "Al Qadsiah", "Neom SC", "Al Hazem"), False),
    LeagueSeed("JPN1", "Japan", "JPN", "AFC", "J1 League", 1, 70, 0, 3, 0,
        ("Kashima Antlers", "Urawa Red Diamonds", "Yokohama F. Marinos", "Kawasaki Frontale", "Vissel Kobe", "Sanfrecce Hiroshima", "FC Tokyo", "Cerezo Osaka", "Gamba Osaka", "Nagoya Grampus", "Kashiwa Reysol", "Avispa Fukuoka", "Albirex Niigata", "Shonan Bellmare", "Tokyo Verdy", "Machida Zelvia", "Kyoto Sanga", "Júbilo Iwata", "Sagan Tosu", "Hokkaido Consadole Sapporo"), False),
    LeagueSeed("AUS1", "Australia", "AUS", "AFC", "A-League Men", 1, 57, 0, 0, 0,
        ("Adelaide United", "Auckland FC", "Brisbane Roar", "Central Coast Mariners", "Macarthur FC", "Melbourne City", "Melbourne Victory", "Newcastle Jets", "Perth Glory", "Sydney FC", "Wellington Phoenix", "Western Sydney Wanderers", "Western United"), False),
    LeagueSeed("IND1", "India", "IND", "AFC", "Indian Super League", 1, 45, 0, 1, 0,
        ("Mohun Bagan Super Giant", "East Bengal", "Mumbai City", "FC Goa", "Bengaluru FC", "Kerala Blasters", "Chennaiyin FC", "Odisha FC", "Jamshedpur FC", "NorthEast United", "Hyderabad FC", "Punjab FC", "Mohammedan SC"), False),
)

ALL_LEAGUES: tuple[LeagueSeed, ...] = TOP_FIVE_LEAGUES + EXPANSION_LEAGUES


COMPETITIONS = (
    # Domestic cups
    ("FACUP", "FA Cup", "England", "domestic_cup", "UEFA", 86),
    ("EFLCUP", "EFL Cup", "England", "domestic_cup", "UEFA", 75),
    ("COPAREY", "Copa del Rey", "Spain", "domestic_cup", "UEFA", 84),
    ("COPITA", "Coppa Italia", "Italy", "domestic_cup", "UEFA", 82),
    ("DFBPOK", "DFB-Pokal", "Germany", "domestic_cup", "UEFA", 82),
    ("COUPEFR", "Coupe de France", "France", "domestic_cup", "UEFA", 79),
    ("TACA", "Taça de Portugal", "Portugal", "domestic_cup", "UEFA", 68),
    ("KNVBCUP", "KNVB Cup", "Netherlands", "domestic_cup", "UEFA", 66),
    ("SCOTCUP", "Scottish Cup", "Scotland", "domestic_cup", "UEFA", 58),
    ("FAICUP", "FAI Cup", "Ireland", "domestic_cup", "UEFA", 43),
    ("USOC", "U.S. Open Cup", "United States", "domestic_cup", "CONCACAF", 55),
    ("COPABR", "Copa do Brasil", "Brazil", "domestic_cup", "CONMEBOL", 76),
    ("COPARG", "Copa Argentina", "Argentina", "domestic_cup", "CONMEBOL", 72),
    ("KINGS", "King's Cup", "Saudi Arabia", "domestic_cup", "AFC", 61),
    ("EMPEROR", "Emperor's Cup", "Japan", "domestic_cup", "AFC", 58),
    ("AUSCUP", "Australia Cup", "Australia", "domestic_cup", "AFC", 47),
    ("SUPERIND", "Super Cup India", "India", "domestic_cup", "AFC", 39),
    # Domestic super cups
    ("COMSHIELD", "FA Community Shield", "England", "super_cup", "UEFA", 72),
    ("SUPERCOPA", "Supercopa de España", "Spain", "super_cup", "UEFA", 78),
    ("SUPERITA", "Supercoppa Italiana", "Italy", "super_cup", "UEFA", 76),
    ("DFLSUP", "DFL-Supercup", "Germany", "super_cup", "UEFA", 75),
    ("TROPHEE", "Trophée des Champions", "France", "super_cup", "UEFA", 71),
    # Club continental competitions
    ("UCL", "UEFA Champions League", None, "continental_club", "UEFA", 100),
    ("UEL", "UEFA Europa League", None, "continental_club", "UEFA", 91),
    ("UECL", "UEFA Conference League", None, "continental_club", "UEFA", 78),
    ("USC", "UEFA Super Cup", None, "super_cup", "UEFA", 88),
    ("LIB", "Copa Libertadores", None, "continental_club", "CONMEBOL", 91),
    ("SUD", "Copa Sudamericana", None, "continental_club", "CONMEBOL", 77),
    ("CCC", "CONCACAF Champions Cup", None, "continental_club", "CONCACAF", 73),
    ("ACL", "AFC Champions League Elite", None, "continental_club", "AFC", 78),
    ("CWC", "FIFA Club World Cup", None, "world_club", "FIFA", 96),
    # National-team competitions
    ("WC", "FIFA World Cup", None, "international", "FIFA", 100),
    ("EURO", "UEFA European Championship", None, "international", "UEFA", 96),
    ("COPA", "Copa América", None, "international", "CONMEBOL", 94),
    ("ASIAN", "AFC Asian Cup", None, "international", "AFC", 83),
    ("AFCON", "Africa Cup of Nations", None, "international", "CAF", 86),
    ("GOLDCUP", "CONCACAF Gold Cup", None, "international", "CONCACAF", 79),
    ("UNL", "UEFA Nations League", None, "international", "UEFA", 79),
)


ELITE_RATINGS = {
    "Real Madrid": (92, 100), "FC Barcelona": (90, 98), "Manchester City": (91, 98),
    "Liverpool": (90, 97), "Arsenal": (89, 95), "FC Bayern München": (91, 98),
    "Paris Saint-Germain": (91, 98), "Inter": (89, 94), "Juventus": (86, 92),
    "AC Milan": (86, 92), "Atlético de Madrid": (87, 93), "Borussia Dortmund": (86, 91),
    "Chelsea": (85, 92), "Manchester United": (83, 94), "Napoli": (86, 90),
    "Bayer 04 Leverkusen": (87, 89), "Tottenham Hotspur": (83, 88), "Newcastle United": (84, 87),
    "Roma": (84, 87), "Olympique de Marseille": (82, 85), "Benfica": (84, 87),
    "FC Porto": (83, 87), "Sporting CP": (84, 86), "Ajax": (81, 86), "PSV": (83, 85),
    "Feyenoord": (82, 84), "Flamengo": (84, 88), "Palmeiras": (84, 87),
    "River Plate": (83, 87), "Boca Juniors": (82, 88), "Al Hilal": (82, 84),
    "Al Nassr": (81, 84), "Inter Miami": (79, 82), "Celtic": (78, 82), "Rangers": (77, 81),
}


def _short_code(name: str, league_code: str, index: int) -> str:
    cleaned = "".join(ch for ch in name.upper() if ch.isalnum())
    stem = (cleaned[:3] if len(cleaned) >= 3 else cleaned.ljust(3, "X"))
    return f"{league_code}{stem}{index:02d}"[:12]


def iter_club_rows() -> Iterable[dict]:
    """Yield normalized club rows with deterministic game ratings."""
    for league in ALL_LEAGUES:
        total = len(league.clubs)
        for index, name in enumerate(league.clubs):
            if name in ELITE_RATINGS:
                strength, reputation = ELITE_RATINGS[name]
            else:
                # Official club lists are normally alphabetical, so list position must
                # never be treated as sporting quality. A stable name-derived jitter
                # creates variety around the league baseline without changing between
                # machines or Python runs. Important clubs use explicit overrides above.
                digest = hashlib.blake2b(f"{league.code}:{name}".encode("utf-8"), digest_size=2).digest()
                variation = int.from_bytes(digest, "big") % 9 - 4
                tier_penalty = (league.tier - 1) * 9
                strength = round(league.reputation * 0.58 + 27 + variation - tier_penalty)
                reputation = round(league.reputation * 0.82 + variation - tier_penalty * 0.4)
                strength = max(43, min(88, strength))
                reputation = max(35, min(92, reputation))
            youth = max(40, min(95, round(strength * 0.7 + reputation * 0.25)))
            reserve = max(40, min(90, round(strength - 6 + youth * 0.08)))
            yield {
                "name": name,
                "short_name": _short_code(name, league.code, index),
                "league_code": league.code,
                "country_code": league.country_code,
                "strength": strength,
                "reputation": reputation,
                "youth_rating": youth,
                "reserve_rating": reserve,
            }


NATIONALITY_TO_COUNTRY_CODE = {
    "english": "ENG", "england": "ENG", "british": "ENG",
    "spanish": "ESP", "spain": "ESP",
    "italian": "ITA", "italy": "ITA",
    "german": "GER", "germany": "GER",
    "french": "FRA", "france": "FRA",
    "portuguese": "POR", "portugal": "POR",
    "dutch": "NED", "netherlands": "NED",
    "scottish": "SCO", "scotland": "SCO",
    "irish": "IRL", "ireland": "IRL",
    "american": "USA", "usa": "USA", "united states": "USA", "canadian": "USA", "canada": "USA",
    "brazilian": "BRA", "brazil": "BRA",
    "argentine": "ARG", "argentinian": "ARG", "argentina": "ARG",
    "saudi": "KSA", "saudi arabia": "KSA",
    "japanese": "JPN", "japan": "JPN",
    "australian": "AUS", "australia": "AUS",
    "indian": "IND", "india": "IND",
}
