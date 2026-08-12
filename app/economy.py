from __future__ import annotations

import json
import math
import random
from typing import Any


INVESTMENT_INSTRUMENTS = (
    ("GIDX", "Global Index Fund", "fund", 100.0, 0.018, 0.055),
    ("TECH", "Technology Growth Fund", "fund", 80.0, 0.030, 0.130),
    ("SPRT", "Sports & Media Fund", "fund", 65.0, 0.023, 0.100),
    ("BOND", "Government Bond Fund", "fund", 50.0, 0.008, 0.018),
)

PROPERTY_CATALOG = (
    ("CITY_FLAT", "City apartment", 110_000, 0, 55, 42),
    ("RENTAL_TOWNHOUSE", "Rental townhouse", 240_000, 540, 120, 56),
    ("LUXURY_HOME", "Luxury residence", 720_000, 0, 510, 74),
    ("COMMERCIAL", "Small commercial property", 980_000, 2_150, 760, 82),
    ("PENTHOUSE", "City penthouse", 1_250_000, 0, 890, 86),
    ("COASTAL_VILLA", "Coastal villa", 1_600_000, 0, 1_150, 90),
    ("STUDIO_LOFT", "Studio loft", 165_000, 350, 80, 48),
    ("SUBURBAN_HOME", "Suburban home", 420_000, 0, 240, 64),
)

ENDORSEMENT_BRANDS = (
    ("Striker Athletics", "Boots and training wear"),
    ("Peak Hydration", "Sports drink campaign"),
    ("Victory Mobile", "Technology and social campaign"),
    ("Northstar Motors", "Automotive ambassador"),
    ("Apex Bank", "Financial-services campaign"),
)

OFFSEASON_ACTIONS = {
    "rest": {
        "label": "Full recovery block",
        "description": "Medical work, sleep and controlled return to training.",
        "fitness": 16,
        "morale": 3,
        "reputation": 0,
        "stress": -12,
        "cost": 0,
    },
    "holiday": {
        "label": "Private holiday",
        "description": "A complete break that restores morale but costs money.",
        "fitness": 8,
        "morale": 12,
        "reputation": 0,
        "stress": -18,
        "cost": 2_500,
    },
    "personal_training": {
        "label": "Personal training camp",
        "description": "A high-quality individual block that creates development XP.",
        "fitness": -3,
        "morale": 2,
        "reputation": 0,
        "stress": 4,
        "cost": 1_200,
        "xp": 22,
    },
    "commercial": {
        "label": "Commercial appearance",
        "description": "Media and sponsor work that earns money and public exposure.",
        "fitness": 1,
        "morale": 1,
        "reputation": 3,
        "stress": 7,
        "income": 3_500,
    },
    "charity": {
        "label": "Charity programme",
        "description": "Community work that improves public reputation and balance.",
        "fitness": 2,
        "morale": 7,
        "reputation": 4,
        "stress": -4,
        "cost": 1_000,
    },
    "agent_meeting": {
        "label": "Agent strategy meeting",
        "description": "Review contracts, club interest and commercial positioning.",
        "fitness": 3,
        "morale": 2,
        "reputation": 1,
        "stress": -2,
        "cost": 400,
    },
}


def seed_economy_catalog(db) -> None:
    for code, name, instrument_type, price, drift, volatility in INVESTMENT_INSTRUMENTS:
        db.execute(
            """
            INSERT INTO investment_instruments(code, name, instrument_type, initial_price, annual_drift, volatility)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name, instrument_type=excluded.instrument_type,
                initial_price=excluded.initial_price, annual_drift=excluded.annual_drift,
                volatility=excluded.volatility
            """,
            (code, name, instrument_type, price, drift, volatility),
        )
    for code, name, price, rent, maintenance, min_rep in PROPERTY_CATALOG:
        db.execute(
            """
            INSERT INTO property_catalog(code, name, purchase_price, weekly_rent, weekly_maintenance, minimum_reputation)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name, purchase_price=excluded.purchase_price,
                weekly_rent=excluded.weekly_rent,
                weekly_maintenance=excluded.weekly_maintenance,
                minimum_reputation=excluded.minimum_reputation
            """,
            (code, name, price, rent, maintenance, min_rep),
        )


def _log(
    db,
    career,
    calendar_week: int,
    category: str,
    amount: int,
    description: str,
    *,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO finance_transactions(
            career_id, season_number, week, calendar_week, category, amount,
            description, reference_type, reference_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            career["id"], career["season_number"], career["current_week"], calendar_week,
            category, int(round(amount)), description, reference_type, reference_id,
        ),
    )


def ensure_financial_profile(db, career_id: int) -> None:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return
    db.execute(
        """
        INSERT OR IGNORE INTO career_financial_profiles(
            career_id, agent_fee_rate, tax_rate, weekly_living_cost, risk_profile
        ) VALUES (?, 0.05, 0.18, ?, 'balanced')
        """,
        (career_id, max(120, round(80 + career["reputation"] * 4))),
    )
    active_contract = db.execute(
        "SELECT 1 FROM player_contracts WHERE career_id=? AND status='active'",
        (career_id,),
    ).fetchone()
    if active_contract is None:
        db.execute(
            """
            INSERT INTO player_contracts(
                career_id, club_id, start_season, end_season, weekly_wage,
                appearance_bonus, goal_bonus, assist_bonus, signing_bonus,
                squad_role, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 'active')
            """,
            (
                career_id, career["club_id"], career["season_number"], career["season_number"] + 2,
                career["wage"], max(50, career["wage"] // 8), max(100, career["wage"] // 4),
                max(75, career["wage"] // 5), career["squad_level"],
            ),
        )
    for instrument in db.execute("SELECT * FROM investment_instruments").fetchall():
        db.execute(
            """
            INSERT OR IGNORE INTO investment_prices(instrument_id, season_number, calendar_week, price)
            VALUES (?, ?, 1, ?)
            """,
            (instrument["id"], career["season_number"], instrument["initial_price"]),
        )


def _price_for_week(db, instrument, season_number: int, calendar_week: int, rng: random.Random) -> float:
    existing = db.execute(
        """
        SELECT price FROM investment_prices
        WHERE instrument_id=? AND season_number=? AND calendar_week=?
        """,
        (instrument["id"], season_number, calendar_week),
    ).fetchone()
    if existing:
        return float(existing["price"])
    previous = db.execute(
        """
        SELECT price FROM investment_prices
        WHERE instrument_id=? AND (season_number<? OR (season_number=? AND calendar_week<?))
        ORDER BY season_number DESC, calendar_week DESC LIMIT 1
        """,
        (instrument["id"], season_number, season_number, calendar_week),
    ).fetchone()
    previous_price = float(previous["price"]) if previous else float(instrument["initial_price"])
    weekly_drift = float(instrument["annual_drift"]) / 52
    weekly_volatility = float(instrument["volatility"]) / math.sqrt(52)
    shock = rng.gauss(weekly_drift, weekly_volatility)
    price = round(max(1.0, previous_price * (1 + shock)), 2)
    db.execute(
        """
        INSERT OR IGNORE INTO investment_prices(instrument_id, season_number, calendar_week, price)
        VALUES (?, ?, ?, ?)
        """,
        (instrument["id"], season_number, calendar_week, price),
    )
    return price


def update_market_prices(db, career, calendar_week: int, rng: random.Random) -> None:
    for instrument in db.execute("SELECT * FROM investment_instruments ORDER BY id").fetchall():
        _price_for_week(db, instrument, career["season_number"], calendar_week, rng)


def _active_endorsement_income(db, career_id: int, calendar_week: int) -> int:
    rows = db.execute(
        """
        SELECT * FROM endorsements
        WHERE career_id=? AND status='active' AND start_week<=? AND end_week>=?
        """,
        (career_id, calendar_week, calendar_week),
    ).fetchall()
    return sum(int(row["weekly_payment"]) for row in rows)


def _property_cashflow(db, career_id: int) -> tuple[int, int]:
    row = db.execute(
        """
        SELECT COALESCE(SUM(pc.weekly_rent),0) AS rent,
               COALESCE(SUM(pc.weekly_maintenance),0) AS maintenance
        FROM owned_properties op JOIN property_catalog pc ON pc.id=op.property_id
        WHERE op.career_id=? AND op.status='owned'
        """,
        (career_id,),
    ).fetchone()
    return int(row["rent"]), int(row["maintenance"])


def maybe_generate_endorsement_offers(db, career, calendar_week: int, rng: random.Random) -> int:
    if career["reputation"] < 12:
        return 0
    active_or_pending = db.execute(
        "SELECT COUNT(*) AS n FROM endorsements WHERE career_id=? AND status IN ('active','pending')",
        (career["id"],),
    ).fetchone()["n"]
    capacity = 1 + career["reputation"] // 35
    if active_or_pending >= capacity or rng.random() > min(0.55, 0.10 + career["reputation"] / 180):
        return 0
    brand, category = rng.choice(ENDORSEMENT_BRANDS)
    weekly = max(150, round((career["reputation"] * 38 + career["overall"] * 12) / 50) * 50)
    signing = weekly * rng.randint(2, 6)
    duration = rng.randint(10, 26)
    db.execute(
        """
        INSERT INTO endorsements(
            career_id, brand_name, category, weekly_payment, signing_payment,
            start_week, end_week, reputation_requirement, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            career["id"], brand, category, weekly, signing, calendar_week,
            min(52, calendar_week + duration), max(10, career["reputation"] - 5),
        ),
    )
    return 1


def process_weekly_finances(db, career, calendar_week: int, rng: random.Random) -> dict[str, int]:
    existing = db.execute(
        """
        SELECT 1 FROM career_week_finance
        WHERE career_id=? AND season_number=? AND calendar_week=?
        """,
        (career["id"], career["season_number"], calendar_week),
    ).fetchone()
    if existing:
        return {"net": 0, "already_processed": 1}

    ensure_financial_profile(db, career["id"])
    profile = db.execute("SELECT * FROM career_financial_profiles WHERE career_id=?", (career["id"],)).fetchone()
    contract = db.execute(
        "SELECT * FROM player_contracts WHERE career_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (career["id"],),
    ).fetchone()
    gross = int(contract["weekly_wage"] if contract else career["wage"])
    agent_fee = round(gross * float(profile["agent_fee_rate"]))
    tax = round(gross * float(profile["tax_rate"]))
    living = int(profile["weekly_living_cost"])
    endorsement = _active_endorsement_income(db, career["id"], calendar_week)
    rent, maintenance = _property_cashflow(db, career["id"])
    net = gross - agent_fee - tax - living + endorsement + rent - maintenance

    _log(db, career, calendar_week, "Salary", gross, f"Gross weekly salary from {career['club_name']}")
    if agent_fee:
        _log(db, career, calendar_week, "Agent fee", -agent_fee, f"Agent commission at {float(profile['agent_fee_rate']) * 100:.0f}%")
    if tax:
        _log(db, career, calendar_week, "Tax reserve", -tax, f"Career tax reserve at {float(profile['tax_rate']) * 100:.0f}%")
    if living:
        _log(db, career, calendar_week, "Living costs", -living, "Housing, travel, food and routine personal costs")
    if endorsement:
        _log(db, career, calendar_week, "Endorsements", endorsement, "Active sponsorship contracts")
    if rent:
        _log(db, career, calendar_week, "Property income", rent, "Rental income from owned property")
    if maintenance:
        _log(db, career, calendar_week, "Property costs", -maintenance, "Property maintenance and management")

    db.execute("UPDATE careers SET money=money+? WHERE id=?", (net, career["id"]))
    db.execute(
        """
        INSERT INTO career_week_finance(
            career_id, season_number, calendar_week, gross_income, total_expenses,
            net_cashflow, processed
        ) VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            career["id"], career["season_number"], calendar_week,
            gross + endorsement + rent, agent_fee + tax + living + maintenance, net,
        ),
    )
    update_market_prices(db, career, calendar_week, rng)
    maybe_generate_endorsement_offers(db, career, calendar_week, rng)
    return {
        "gross": gross,
        "agent_fee": agent_fee,
        "tax": tax,
        "living": living,
        "endorsement": endorsement,
        "rent": rent,
        "maintenance": maintenance,
        "net": net,
    }


def accept_endorsement(db, career_id: int, endorsement_id: int) -> tuple[bool, str]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    offer = db.execute(
        "SELECT * FROM endorsements WHERE id=? AND career_id=? AND status='pending'",
        (endorsement_id, career_id),
    ).fetchone()
    if career is None or offer is None:
        return False, "Endorsement offer is no longer available."
    if career["reputation"] < offer["reputation_requirement"]:
        return False, "Your current reputation no longer satisfies this campaign."
    db.execute("UPDATE endorsements SET status='active' WHERE id=?", (endorsement_id,))
    db.execute("UPDATE careers SET money=money+?, reputation=MIN(100,reputation+1) WHERE id=?", (offer["signing_payment"], career_id))
    _log(db, career, career["calendar_week"], "Endorsement signing", offer["signing_payment"], f"Signed with {offer['brand_name']}", reference_type="endorsement", reference_id=endorsement_id)
    return True, f"Signed {offer['brand_name']}: ${offer['signing_payment']:,} now and ${offer['weekly_payment']:,} per week."


def decline_endorsement(db, career_id: int, endorsement_id: int) -> bool:
    cursor = db.execute(
        "UPDATE endorsements SET status='declined' WHERE id=? AND career_id=? AND status='pending'",
        (endorsement_id, career_id),
    )
    return cursor.rowcount > 0


def _latest_prices(db, season_number: int, calendar_week: int) -> list[Any]:
    return db.execute(
        """
        SELECT ii.*,
               COALESCE((SELECT ip.price FROM investment_prices ip
                         WHERE ip.instrument_id=ii.id
                           AND (ip.season_number<? OR (ip.season_number=? AND ip.calendar_week<=?))
                         ORDER BY ip.season_number DESC, ip.calendar_week DESC LIMIT 1), ii.initial_price) AS price
        FROM investment_instruments ii ORDER BY ii.id
        """,
        (season_number, season_number, calendar_week),
    ).fetchall()


def buy_investment(db, career_id: int, instrument_id: int, amount: int) -> tuple[bool, str]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return False, "Career not found."
    amount = int(amount)
    if amount < 100:
        return False, "Minimum investment is $100."
    if amount > career["money"]:
        return False, "Not enough available cash."
    instrument = next((row for row in _latest_prices(db, career["season_number"], career["calendar_week"]) if row["id"] == instrument_id), None)
    if instrument is None:
        return False, "Investment instrument not found."
    price = float(instrument["price"])
    units = amount / price
    existing = db.execute(
        "SELECT * FROM investment_positions WHERE career_id=? AND instrument_id=?",
        (career_id, instrument_id),
    ).fetchone()
    if existing:
        total_cost = float(existing["units"]) * float(existing["average_cost"]) + amount
        total_units = float(existing["units"]) + units
        db.execute(
            "UPDATE investment_positions SET units=?, average_cost=? WHERE id=?",
            (total_units, total_cost / total_units, existing["id"]),
        )
    else:
        db.execute(
            "INSERT INTO investment_positions(career_id,instrument_id,units,average_cost) VALUES (?,?,?,?)",
            (career_id, instrument_id, units, price),
        )
    db.execute("UPDATE careers SET money=money-? WHERE id=?", (amount, career_id))
    _log(db, career, career["calendar_week"], "Investment purchase", -amount, f"Bought {instrument['name']} at ${price:.2f}", reference_type="investment", reference_id=instrument_id)
    return True, f"Invested ${amount:,} in {instrument['name']}."


def sell_investment(db, career_id: int, instrument_id: int, percent: int) -> tuple[bool, str]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    position = db.execute(
        "SELECT * FROM investment_positions WHERE career_id=? AND instrument_id=?",
        (career_id, instrument_id),
    ).fetchone()
    if career is None or position is None or float(position["units"]) <= 0:
        return False, "No position is available to sell."
    percent = max(1, min(100, int(percent)))
    instrument = next((row for row in _latest_prices(db, career["season_number"], career["calendar_week"]) if row["id"] == instrument_id), None)
    units_sold = float(position["units"]) * percent / 100
    proceeds = round(units_sold * float(instrument["price"]))
    remaining = float(position["units"]) - units_sold
    db.execute("UPDATE investment_positions SET units=? WHERE id=?", (remaining, position["id"]))
    db.execute("UPDATE careers SET money=money+? WHERE id=?", (proceeds, career_id))
    _log(db, career, career["calendar_week"], "Investment sale", proceeds, f"Sold {percent}% of {instrument['name']} at ${float(instrument['price']):.2f}", reference_type="investment", reference_id=instrument_id)
    return True, f"Sold {percent}% of {instrument['name']} for ${proceeds:,}."


def buy_property(db, career_id: int, property_id: int) -> tuple[bool, str]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    item = db.execute("SELECT * FROM property_catalog WHERE id=?", (property_id,)).fetchone()
    if career is None or item is None:
        return False, "Property not found."
    if career["reputation"] < item["minimum_reputation"]:
        return False, f"This property requires reputation {item['minimum_reputation']}."
    if career["money"] < item["purchase_price"]:
        return False, "Not enough available cash."
    db.execute(
        """
        INSERT INTO owned_properties(career_id,property_id,purchase_price,purchase_season,purchase_week,status)
        VALUES (?,?,?,?,?,'owned')
        """,
        (career_id, property_id, item["purchase_price"], career["season_number"], career["calendar_week"]),
    )
    db.execute("UPDATE careers SET money=money-? WHERE id=?", (item["purchase_price"], career_id))
    _log(db, career, career["calendar_week"], "Property purchase", -item["purchase_price"], f"Purchased {item['name']}", reference_type="property", reference_id=property_id)
    return True, f"Purchased {item['name']} for ${item['purchase_price']:,}."


def place_virtual_wager(db, career_id: int, stake: int, risk: str, rng: random.Random) -> tuple[bool, str]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return False, "Career not found."
    if db.execute(
        """
        SELECT 1 FROM virtual_wagers WHERE career_id=? AND season_number=? AND calendar_week=?
        """,
        (career_id, career["season_number"], career["calendar_week"]),
    ).fetchone():
        return False, "Only one virtual wager is allowed per career week."
    stake = int(stake)
    cap = max(100, min(10_000, career["money"] // 5))
    if stake < 50 or stake > cap:
        return False, f"Stake must be between $50 and ${cap:,}."
    if stake > career["money"]:
        return False, "Not enough available cash."
    profiles = {
        "safe": (0.58, 1.62),
        "balanced": (0.38, 2.35),
        "longshot": (0.16, 5.40),
    }
    probability, multiplier = profiles.get(risk, profiles["balanced"])
    won = rng.random() < probability
    payout = round(stake * multiplier) if won else 0
    net = payout - stake
    db.execute(
        """
        INSERT INTO virtual_wagers(
            career_id,season_number,calendar_week,stake,risk_level,odds_multiplier,won,payout
        ) VALUES (?,?,?,?,?,?,?,?)
        """,
        (career_id, career["season_number"], career["calendar_week"], stake, risk, multiplier, int(won), payout),
    )
    db.execute("UPDATE careers SET money=money+? WHERE id=?", (net, career_id))
    _log(db, career, career["calendar_week"], "Virtual wager", net, f"{risk.title()} in-game wager: {'won' if won else 'lost'}", reference_type="wager")
    return True, f"Virtual wager {'won' if won else 'lost'}: net {'+' if net >= 0 else '-'}${abs(net):,}."


def take_offseason_action(db, career_id: int, action: str) -> tuple[bool, str]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    definition = OFFSEASON_ACTIONS.get(action)
    if career is None or definition is None:
        return False, "Unknown player programme."
    if career["season_phase"] not in {"offseason", "preseason"} and career["calendar_week"] not in {1, 2, 3, 51, 52}:
        return False, "This programme is available only during designated off-season weeks."
    if db.execute(
        """
        SELECT 1 FROM career_week_actions
        WHERE career_id=? AND season_number=? AND calendar_week=?
        """,
        (career_id, career["season_number"], career["calendar_week"]),
    ).fetchone():
        return False, "You have already chosen this week's player programme."
    cost = int(definition.get("cost", 0))
    income = int(definition.get("income", 0))
    if cost > career["money"]:
        return False, "Not enough available cash for that programme."
    db.execute(
        """
        INSERT INTO career_week_actions(
            career_id,season_number,calendar_week,action_type,title,effects_json
        ) VALUES (?,?,?,?,?,?)
        """,
        (
            career_id, career["season_number"], career["calendar_week"], action,
            definition["label"], json.dumps(definition, sort_keys=True),
        ),
    )
    db.execute(
        """
        UPDATE careers SET
            fitness=MIN(100,MAX(25,fitness+?)),
            morale=MIN(100,MAX(15,morale+?)),
            reputation=MIN(100,MAX(0,reputation+?)),
            stress=MIN(100,MAX(0,stress+?)),
            xp=MIN(99,xp+?),
            money=money+?
        WHERE id=?
        """,
        (
            definition.get("fitness", 0), definition.get("morale", 0), definition.get("reputation", 0),
            definition.get("stress", 0), definition.get("xp", 0), income - cost, career_id,
        ),
    )
    if cost:
        _log(db, career, career["calendar_week"], "Player programme", -cost, definition["label"])
    if income:
        _log(db, career, career["calendar_week"], "Commercial income", income, definition["label"])
    return True, f"{definition['label']} selected. {definition['description']}"


def get_financial_dashboard(db, career_id: int) -> dict[str, Any]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return {}
    profile = db.execute("SELECT * FROM career_financial_profiles WHERE career_id=?", (career_id,)).fetchone()
    contract = db.execute(
        """
        SELECT pc.*, c.name AS club_name FROM player_contracts pc
        JOIN clubs c ON c.id=pc.club_id
        WHERE pc.career_id=? AND pc.status='active' ORDER BY pc.id DESC LIMIT 1
        """,
        (career_id,),
    ).fetchone()
    endorsements = db.execute(
        "SELECT * FROM endorsements WHERE career_id=? ORDER BY status='pending' DESC, id DESC",
        (career_id,),
    ).fetchall()
    prices = _latest_prices(db, career["season_number"], career["calendar_week"])
    positions = db.execute(
        """
        SELECT p.*, ii.name, ii.code,
               COALESCE((SELECT ip.price FROM investment_prices ip
                         WHERE ip.instrument_id=ii.id
                         ORDER BY ip.season_number DESC, ip.calendar_week DESC LIMIT 1), ii.initial_price) AS current_price
        FROM investment_positions p JOIN investment_instruments ii ON ii.id=p.instrument_id
        WHERE p.career_id=? AND p.units>0 ORDER BY ii.name
        """,
        (career_id,),
    ).fetchall()
    position_value = sum(float(row["units"]) * float(row["current_price"]) for row in positions)
    properties = db.execute(
        """
        SELECT op.*, pc.code, pc.name, pc.weekly_rent, pc.weekly_maintenance,
               pc.purchase_price AS catalogue_price
        FROM owned_properties op JOIN property_catalog pc ON pc.id=op.property_id
        WHERE op.career_id=? AND op.status='owned' ORDER BY op.id
        """,
        (career_id,),
    ).fetchall()
    property_value = sum(int(row["catalogue_price"]) for row in properties)
    property_catalog = db.execute("SELECT * FROM property_catalog ORDER BY purchase_price").fetchall()
    location_row = db.execute(
        """
        SELECT co.code AS country_code, co.name AS country_name
        FROM clubs c LEFT JOIN countries co ON co.id=c.country_id
        WHERE c.id=?
        """,
        (career["club_id"],),
    ).fetchone()
    transactions = db.execute(
        """
        SELECT * FROM finance_transactions WHERE career_id=?
        ORDER BY id DESC LIMIT 80
        """,
        (career_id,),
    ).fetchall()
    totals = db.execute(
        """
        SELECT
          COALESCE(SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),0) AS income,
          COALESCE(-SUM(CASE WHEN amount<0 THEN amount ELSE 0 END),0) AS expenses,
          COALESCE(SUM(amount),0) AS net
        FROM finance_transactions WHERE career_id=?
        """,
        (career_id,),
    ).fetchone()
    categories = db.execute(
        """
        SELECT category, SUM(amount) AS total, COUNT(*) AS transactions
        FROM finance_transactions WHERE career_id=?
        GROUP BY category ORDER BY ABS(SUM(amount)) DESC
        """,
        (career_id,),
    ).fetchall()
    country_code = (location_row["country_code"] if location_row and location_row["country_code"] else "INT")
    country_name = (location_row["country_name"] if location_row and location_row["country_name"] else "International")
    city_by_country = {
        "ENG": "London", "ESP": "Madrid", "ITA": "Milan", "GER": "Berlin", "FRA": "Paris",
        "POR": "Lisbon", "NED": "Amsterdam", "SCO": "Edinburgh", "IRL": "Dublin", "USA": "New York",
        "BRA": "São Paulo", "ARG": "Buenos Aires", "SAU": "Riyadh", "JPN": "Tokyo", "AUS": "Sydney",
        "IND": "Mumbai",
    }
    city = city_by_country.get(country_code, country_name)
    property_meta = {
        "CITY_FLAT": ("city-apartment.svg", "Primary residence", "A modern city base. No rental income; only weekly running costs."),
        "RENTAL_TOWNHOUSE": ("rental-townhouse.svg", "Income property", "A residential rental producing weekly income after maintenance."),
        "LUXURY_HOME": ("luxury-residence.svg", "Primary residence", "High-prestige home with significant running costs and no rental income."),
        "COMMERCIAL": ("commercial-office.svg", "Income property", "Commercial tenancy with strong rent and higher maintenance exposure."),
        "PENTHOUSE": ("penthouse.svg", "Primary residence", "Premium city living with no weekly rent income."),
        "COASTAL_VILLA": ("coastal-villa.svg", "Primary residence", "Private lifestyle property with high upkeep and no rental income."),
        "STUDIO_LOFT": ("studio-loft.svg", "Income property", "Entry-level rental asset with modest weekly income."),
        "SUBURBAN_HOME": ("suburban-home.svg", "Primary residence", "A larger personal home outside the city centre."),
    }
    location_suffix = {
        "CITY_FLAT": f"{city} Central", "RENTAL_TOWNHOUSE": f"{city} North", "LUXURY_HOME": f"{city} Hills",
        "COMMERCIAL": f"{city} Business District", "PENTHOUSE": f"{city} Skyline", "COASTAL_VILLA": f"{country_name} Coast",
        "STUDIO_LOFT": f"{city} Arts Quarter", "SUBURBAN_HOME": f"Greater {city}",
    }
    # Rotating local listings: the catalogue exists permanently, but only five properties are marketed each week.
    market_rng = random.Random(f"property:{career_id}:{career['season_number']}:{career['calendar_week']}:{country_code}")
    shuffled_catalog = list(property_catalog)
    market_rng.shuffle(shuffled_catalog)
    available_ids = {int(row["id"]) for row in shuffled_catalog[:5]}
    owned_ids = {int(row["property_id"]) for row in properties}
    decorated_catalog = []
    for row in property_catalog:
        item = dict(row)
        image, use_type, summary = property_meta.get(row["code"], ("city-apartment.svg", "Property", "Local property listing."))
        item.update({
            "image": image,
            "use_type": use_type,
            "summary": summary,
            "location": location_suffix.get(row["code"], city),
            "is_owned": int(row["id"]) in owned_ids,
            "is_available": int(row["id"]) in available_ids,
            "expires_in": 1 + market_rng.randint(1, 4),
            "net_weekly": int(row["weekly_rent"]) - int(row["weekly_maintenance"]),
        })
        decorated_catalog.append(item)
    decorated_properties = []
    for row in properties:
        item = dict(row)
        image, use_type, summary = property_meta.get(row["code"], ("city-apartment.svg", "Property", "Owned property."))
        item.update({"image": image, "use_type": use_type, "summary": summary, "location": location_suffix.get(row["code"], city), "net_weekly": int(row["weekly_rent"]) - int(row["weekly_maintenance"])})
        decorated_properties.append(item)
    price_history = {}
    for instrument in prices:
        rows = db.execute(
            """
            SELECT season_number, calendar_week, price FROM investment_prices
            WHERE instrument_id=? ORDER BY season_number DESC, calendar_week DESC LIMIT 16
            """,
            (instrument["id"],),
        ).fetchall()
        values = [round(float(row["price"]), 2) for row in reversed(rows)]
        if len(values) == 1:
            values = [values[0]] * 4
        price_history[int(instrument["id"])] = values
    instrument_meta = {
        "GIDX": {"icon": "index", "risk": "Moderate", "description": "Broad market exposure with steadier long-term movement."},
        "TECH": {"icon": "chip", "risk": "High", "description": "Higher volatility and stronger growth potential."},
        "SPRT": {"icon": "stadium", "risk": "Medium-high", "description": "Sport, media and entertainment sector exposure."},
        "BOND": {"icon": "shield", "risk": "Low", "description": "Defensive fund with lower volatility."},
    }
    decorated_instruments = []
    for row in prices:
        item = dict(row)
        item.update(instrument_meta.get(row["code"], {"icon": "chart", "risk": "Variable", "description": "Virtual market instrument."}))
        item["history"] = price_history.get(int(row["id"]), [float(row["price"])])
        first, last = item["history"][0], item["history"][-1]
        item["change_pct"] = round(((last-first)/first)*100, 2) if first else 0.0
        decorated_instruments.append(item)
    return {
        "career": career,
        "profile": profile,
        "contract": contract,
        "endorsements": endorsements,
        "instruments": decorated_instruments,
        "positions": positions,
        "properties": decorated_properties,
        "property_catalog": decorated_catalog,
        "property_location": {"country": country_name, "country_code": country_code, "city": city},
        "transactions": transactions,
        "totals": totals,
        "categories": categories,
        "investment_value": round(position_value),
        "property_value": property_value,
        "net_worth": round(career["money"] + position_value + property_value),
        "offseason_actions": OFFSEASON_ACTIONS,
    }
