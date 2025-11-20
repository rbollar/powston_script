# Priority Rules Decision
# Powston Dynamic Arbitrage — v6.5 (Refactored & Optimized)
# Author: powston.com.au@bol.la
#
# STRATEGY PHILOSOPHY:
# - ALWAYS charge to 100% by 16:00 if buy price ≤ 10c (cheap energy is valuable)
# - Solar forecast controls EXPORT floor (how much to protect for overnight)
# - Sunny: Can export down to 71% (low overnight reserve)
# - Normal: Can export down to 91% (medium overnight reserve)  
# - Rainy: Can export down to 116% → ~100% (high overnight reserve)
# - After 16:00: Floor steps down as hours until sunrise decrease
# - OVERNIGHT DRAIN: After 20:00, actively sell to reach 10-20% by sunrise
#   - Protects house load until sunrise
#   - Sells more aggressively as sunrise approaches
#   - Priority 65 overrides normal sell thresholds when above target

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION CONSTANTS
# ═══════════════════════════════════════════════════════════════
# 
# CRITICAL: This script runs INDEPENDENTLY on each inverter
# - 2 inverters × 50 kWh = 100 kWh total system capacity
# - Each inverter supplies HALF the total house load
# - House load constants below are PER INVERTER (not total)
#

# Time periods
PEAK_START = 16
PEAK_END = 20

# Price thresholds
MAX_AM_BUY_PRICE = 10.0
BASE_MIN_SELL_PRICE = 10.0
ALWAYS_SELL_PRICE = 100.0
DESIRED_MARGIN = 5.0

# Forecast settings
FUTURE_FORECAST_HOURS = 8
BUY_UNCERTAINTY_DISCOUNT = 0.03
SELL_UNCERTAINTY_DISCOUNT = 0.07

# Site configuration
NUM_INVERTERS = 2
INVERTER_IDS = [43923, 43924]
SITE_EXPORT_KWH_PER_PERIOD = NUM_INVERTERS * 10.0

# Battery configuration
FULL_BATTERY = 100.0
BATTERY_WATT_HOURS = 50000.0  # Per inverter (100 kWh total across 2 inverters)

# House load estimation (kWh/hour) - PER INVERTER
# Total house load is split across 2 inverters
# 4 kWh/hour total house load = 2 kWh/hour per inverter
CONSERVATIVE_HOUSE_LOAD_KWH_PER_HOUR = 2.0  # Conservative per-inverter (4 kWh total)
# _TYPICAL_HOUSE_LOAD_KWH_PER_HOUR = 1.5      # Typical per-inverter (3 kWh total) - reserved for future use
# _MIN_HOUSE_LOAD_KWH_PER_HOUR = 1.0          # Minimum per-inverter (2 kWh total) - reserved for future use

# Solar classification thresholds (GTI W·h/m²)
GTI_SUNNY_THRESHOLD = 6000.0
GTI_NORMAL_THRESHOLD = 3500.0

# SOC floors by solar condition (%)
SUNNY_FLOOR_SOC = 15.0
NORMAL_FLOOR_SOC = 35.0
RAINY_FLOOR_SOC = 60.0

# Export budgets by solar condition (kWh)
SUNNY_EXPORT_BUDGET = 40.0
NORMAL_EXPORT_BUDGET = 25.0
RAINY_EXPORT_BUDGET = 10.0

# Evening premium bounds
EVENING_PREMIUM_LOW = DESIRED_MARGIN
EVENING_PREMIUM_HIGH = 2 * DESIRED_MARGIN

# Morning target SOC (for overnight drain strategy)
TARGET_MORNING_SOC_MIN = 10.0
TARGET_MORNING_SOC_MAX = 20.0

# Grid limitation
feed_in_power_limitation = None


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def clean_number_list(seq, default_val):
    """Extract valid numbers from a list, return default if empty."""

    out = []

    if isinstance(seq, list):
        for v in seq:
            if isinstance(v, (int, float)):
                out.append(float(v))
    return out if out else [default_val]


def get_combined_soc(battery_soc_input, inverters_dict, inverter_ids):
    """Calculate average SOC across multiple inverters, fallback to direct SOC."""

    socs = []
    try:
        if inverters_dict:
            for inv_id in inverter_ids:
                key = f"inverter_params_{inv_id}"
                if key in inverters_dict:
                    soc_val = inverters_dict[key].get("battery_soc")
                    if isinstance(soc_val, (int, float)):
                        socs.append(float(soc_val))
    except (AttributeError, KeyError, TypeError):
        pass
    
    if socs:
        return sum(socs) / len(socs)
    
    return float(battery_soc_input) if isinstance(battery_soc_input, (int, float)) else 0.0


def apply_uncertainty_discount(buy_list, sell_list, hours, buy_disc, sell_disc):
    """
    Apply exponential uncertainty discounting to forecasts.
    Buy prices increase with uncertainty, sell prices decrease.
    """

    discounted_buy = []
    discounted_sell = []
    limit = min(hours, max(len(buy_list), len(sell_list)))
    
    for i in range(limit):
        if i < len(buy_list):
            discounted_buy.append(buy_list[i] * ((1 + buy_disc) ** i))
        if i < len(sell_list):
            discounted_sell.append(sell_list[i] * ((1 - sell_disc) ** i))
    
    # Ensure we always return valid lists
    if not discounted_buy:
        discounted_buy = [9999.0]
    if not discounted_sell:
        discounted_sell = [0.0]
    
    return {"buy": discounted_buy, "sell": discounted_sell}


def classify_time_period(current_hour, sunrise_hour, peak_start, peak_end):
    """Classify current time as Peak, Day, or Night."""

    if peak_start <= current_hour <= peak_end:
        return "Peak"
    elif sunrise_hour <= current_hour < peak_start:
        return "Day"
    else:
        return "Night"


def classify_solar_forecast(gti_tomorrow, sunny_threshold, normal_threshold):
    """Classify tomorrow's solar forecast as sunny, normal, or rainy."""

    if not isinstance(gti_tomorrow, (int, float)):
        return "normal"
    
    if gti_tomorrow >= sunny_threshold:
        return "sunny"
    elif gti_tomorrow >= normal_threshold:
        return "normal"
    else:
        return "rainy"


def compute_evening_premium(buy_fc, sell_fc, current_hour, peak_start, peak_end):
    """
    Calculate evening premium: difference between peak sell prices 
    and daytime buy prices.
    """

    daytime_buys = []
    peak_sells = []
    count = min(len(buy_fc), len(sell_fc))
    
    for i in range(count):
        hour = (current_hour + i) % 24
        buy_price = buy_fc[i]
        sell_price = sell_fc[i]
        
        if not isinstance(buy_price, (int, float)) or not isinstance(sell_price, (int, float)):
            continue
        
        # Collect daytime buys (9am to peak start)
        if 9 <= hour < peak_start:
            daytime_buys.append(buy_price)
        
        # Collect peak sells
        if peak_start <= hour <= peak_end:
            peak_sells.append(sell_price)
    
    if not daytime_buys or not peak_sells:
        return 0.0
    
    return max(peak_sells) - min(daytime_buys)


def compute_floor_and_budget(
    solar_class,
    evening_premium,
    battery_kwh,
    current_soc,
    current_hour,
    sunrise_hour,
    house_load_kwh_per_hour,
    sunny_floor,
    normal_floor,
    rainy_floor,
    sunny_budget,
    normal_budget,
    rainy_budget,
    premium_low,
    premium_high
):
    """
    Compute dynamic SOC floor and export budget based on solar forecast,
    evening premium, and overnight house load requirements.
    """

    # Select base values by solar class (these are safety margins)
    if solar_class == "sunny":
        base_floor_soc = sunny_floor
        base_budget = sunny_budget
    elif solar_class == "rainy":
        base_floor_soc = rainy_floor
        base_budget = rainy_budget
    else:  # normal
        base_floor_soc = normal_floor
        base_budget = normal_budget
    
    # Calculate overnight energy requirements
    # Key insight: ALWAYS charge to 100% by 16:00 if buy price is reasonable.
    # Solar forecast only affects EXPORT floor (how much we protect for overnight).
    
    # Calculate hours from 16:00 until sunrise (for export floor calculation)
    if 16 >= sunrise_hour:
        hours_from_16_to_sunrise = (24 - 16) + sunrise_hour
    else:
        hours_from_16_to_sunrise = sunrise_hour - 16
    
    target_overnight_hours = max(0.0, hours_from_16_to_sunrise)  # 14 hours if sunrise=6
    target_overnight_energy_kwh = target_overnight_hours * house_load_kwh_per_hour
    target_overnight_reserve_soc = (target_overnight_energy_kwh / battery_kwh) * 100.0
    
    # This is what we need to protect for overnight
    target_export_floor_at_16 = base_floor_soc + target_overnight_reserve_soc
    
    # For decisions right now:
    if current_hour < 16:
        # Before 16:00: ALWAYS target 100% for imports (if price reasonable)
        import_floor_soc = 100.0
        
        # But for EXPORTS: protect overnight requirement
        # Can't export below what we need at 16:00 for overnight
        export_floor_soc = target_export_floor_at_16  # 71%/91%/116% based on solar
        
        # For logging: show what we're protecting for overnight
        overnight_hours = target_overnight_hours
        overnight_energy_kwh = target_overnight_energy_kwh
        overnight_reserve_soc = target_overnight_reserve_soc
    else:
        # At/after 16:00: Calculate actual current floor
        # Both decrease together as night progresses
        if current_hour >= sunrise_hour:
            hours_until_sunrise = (24 - current_hour) + sunrise_hour
        else:
            hours_until_sunrise = sunrise_hour - current_hour
        
        overnight_hours = max(0.0, hours_until_sunrise)
        overnight_energy_kwh = overnight_hours * house_load_kwh_per_hour
        overnight_reserve_soc = (overnight_energy_kwh / battery_kwh) * 100.0
        
        # After 16:00: imports aren't allowed during peak anyway
        # Both floors step down together
        import_floor_soc = base_floor_soc + overnight_reserve_soc
        export_floor_soc = base_floor_soc + overnight_reserve_soc
        overnight_hours = max(0.0, hours_until_sunrise)
        overnight_energy_kwh = overnight_hours * house_load_kwh_per_hour
        overnight_reserve_soc = (overnight_energy_kwh / battery_kwh) * 100.0
    
    # Adjust budget based on evening premium
    if evening_premium <= premium_low:
        budget_factor = 0.0
    elif evening_premium <= premium_high:
        budget_factor = 0.5
    else:
        budget_factor = 1.0
    
    export_budget = base_budget * budget_factor
    
    # Limit budget to available energy ABOVE the EXPORT floor
    current_energy_kwh = max(0.0, (current_soc / 100.0) * battery_kwh)
    export_floor_energy_kwh = max(0.0, (export_floor_soc / 100.0) * battery_kwh)
    available_above_floor = max(0.0, current_energy_kwh - export_floor_energy_kwh)
    export_budget = min(export_budget, available_above_floor)
    
    # Clamp floors to valid range (but can exceed 100% as warning flag)
    import_floor_soc = max(0.0, import_floor_soc)
    export_floor_soc = max(0.0, export_floor_soc)
    
    return {
        "import_floor": import_floor_soc,      # Use for import decisions
        "export_floor": export_floor_soc,      # Use for export decisions  
        "budget": export_budget,
        "overnight_reserve_soc": overnight_reserve_soc,
        "overnight_hours": overnight_hours if current_hour >= 16 else target_overnight_hours,
        "overnight_energy_kwh": overnight_energy_kwh if current_hour >= 16 else target_overnight_energy_kwh
    }


def compute_dynamic_sell_threshold(
    discounted_sell_fc,
    discounted_buy_fc,
    available_kwh,
    per_period_kwh,
    base_min_price,
    margin
):
    """
    Calculate dynamic sell threshold based on available energy and forecast.
    Uses a "periods to export" approach: higher availability = lower threshold.
    """

    if available_kwh <= 0:
        return 9999.0  # No energy available, don't sell
    
    # Extract positive sell prices
    positive_sells = [s for s in discounted_sell_fc if isinstance(s, (int, float)) and s > 0]
    
    if not positive_sells:
        return 9999.0
    
    # Sort descending to find threshold by rank
    positive_sells.sort(reverse=True)
    
    # Calculate how many periods needed to export available energy
    per_period_cap = max(0.1, per_period_kwh)
    periods_needed = int(available_kwh / per_period_cap + 0.999)
    periods_needed = max(1, periods_needed)
    
    # Select threshold: if we need many periods, accept lower prices
    if periods_needed >= len(positive_sells):
        threshold_sell = min(positive_sells)
    else:
        threshold_sell = positive_sells[periods_needed - 1]
    
    # Calculate margin threshold from minimum buy price
    valid_buys = [b for b in discounted_buy_fc if isinstance(b, (int, float)) and b > 0]
    min_buy = min(valid_buys) if valid_buys else 0.0
    margin_threshold = min_buy + margin
    
    # Final threshold is the max of: base min, dynamic sell, and margin
    return max(base_min_price, threshold_sell, margin_threshold)


def analyze_overnight_opportunities(
    sell_forecast,
    current_hour,
    sunrise_hour,
    peak_end_hour,
    energy_to_drain_kwh,
    per_period_export_kwh
):
    """
    Analyze overnight forecast to identify best sell periods.
    Returns dict with best period prices and whether current period is a good opportunity.
    """
    
    # Calculate overnight period indices
    overnight_prices = []
    
    for i in range(len(sell_forecast)):
        # Calculate when this period starts (each period is 0.5 hours = 30 min)
        period_start_hour = (current_hour + (i * 0.5)) % 24
        
        # Check if this period is overnight (after peak_end, before sunrise)
        is_overnight = False
        if peak_end_hour >= sunrise_hour:
            # Overnight spans midnight (most common: 20:00 to 06:00)
            # A period is overnight if: after peak_end OR before sunrise
            is_overnight = period_start_hour > peak_end_hour or period_start_hour < sunrise_hour
        else:
            # Overnight doesn't span midnight (rare: e.g., 02:00 to 06:00)
            # A period is overnight if: after peak_end AND before sunrise
            is_overnight = period_start_hour > peak_end_hour and period_start_hour < sunrise_hour
        
        if is_overnight and isinstance(sell_forecast[i], (int, float)):
            overnight_prices.append({
                "index": i,
                "hour": period_start_hour,  # Store actual hour (can be float)
                "price": sell_forecast[i]
            })
    
    if not overnight_prices:
        return {
            "has_opportunities": False,
            "best_prices": [],
            "current_is_good": False,
            "current_rank": None,
            "total_periods": 0
        }
    
    # Sort by price descending to find best opportunities
    overnight_prices.sort(key=lambda x: x["price"], reverse=True)
    
    # Calculate how many periods we need to drain the target energy
    periods_needed = max(1, int(energy_to_drain_kwh / per_period_export_kwh + 0.999))
    
    # Identify the best N periods (where N = periods_needed)
    best_periods = overnight_prices[:min(periods_needed, len(overnight_prices))]
    best_period_indices = [p["index"] for p in best_periods]
    
    # Check if current period (index 0) is in the best periods
    current_is_best = 0 in best_period_indices
    
    # Find current period's rank
    current_rank = None
    for rank, p in enumerate(overnight_prices, 1):
        if p["index"] == 0:
            current_rank = rank
            break
    
    return {
        "has_opportunities": True,
        "best_prices": [p["price"] for p in best_periods],
        "best_periods": best_periods,  # Full period details (index, hour, price)
        "best_period_indices": best_period_indices,
        "current_is_good": current_is_best,
        "current_rank": current_rank,
        "total_periods": len(overnight_prices),
        "periods_needed": periods_needed,
        "worst_acceptable_price": best_periods[-1]["price"] if best_periods else 0
    }


def analyze_daytime_charging_strategy(
    buy_forecast,
    current_hour,
    peak_start_hour,
    solar_surplus_deficit_kwh,
    current_soc,
    battery_kwh
):
    """
    Analyze daytime charging strategy based on solar surplus/deficit.
    
    Args:
        buy_forecast: Discounted buy price forecast (cents/kWh)
        current_hour: Current hour
        peak_start_hour: When peak starts (target 100% by this time)
        solar_surplus_deficit_kwh: Net energy balance to 16:00
            Negative = need grid charging
            Positive = solar will handle it (no grid needed)
        current_soc: Current battery SOC %
        battery_kwh: Battery capacity in kWh
    
    Returns:
        Dict with charging strategy
    """
    
    # Determine if grid charging is needed
    if solar_surplus_deficit_kwh >= 0:
        # Solar surplus or break-even - no grid charging needed
        # Solar will naturally charge the battery
        return {
            "needs_grid_charging": False,
            "grid_energy_needed_kwh": 0.0,
            "grid_periods_needed": 0,
            "best_grid_periods": [],
            "current_is_best": False,
            "current_rank": None,
            "strategy": "solar_only"
        }
    
    # Solar deficit - need grid charging
    grid_energy_needed_kwh = abs(solar_surplus_deficit_kwh)
    
    # Analyze buy forecast to find best periods
    daytime_periods = []
    
    for i in range(len(buy_forecast)):
        # Calculate when this period starts (each period is 0.5 hours = 30 min)
        period_start_hour = current_hour + (i * 0.5)
        
        # Only consider periods that START before peak (16:00)
        # Don't need modulo 24 here since we're just checking if < peak_start_hour
        if period_start_hour >= peak_start_hour:
            # Reached or passed peak start time
            break
        
        buy_price = buy_forecast[i]
        if not isinstance(buy_price, (int, float)):
            buy_price = 9999.0
        
        daytime_periods.append({
            "index": i,
            "hour": period_start_hour,  # Store actual hour (can be float like 6.5 = 06:30)
            "price": buy_price
        })
    
    if not daytime_periods:
        return {
            "needs_grid_charging": True,
            "grid_energy_needed_kwh": grid_energy_needed_kwh,
            "grid_periods_needed": 0,
            "best_grid_periods": [],
            "current_is_best": False,
            "current_rank": None,
            "strategy": "grid_needed_but_no_periods"
        }
    
    # Sort by price ascending (cheapest first)
    daytime_periods.sort(key=lambda x: x["price"])
    
    # Calculate how many periods needed
    max_charge_per_period_kwh = 5.0  # 10kW × 0.5h
    grid_periods_needed = max(1, int(grid_energy_needed_kwh / max_charge_per_period_kwh + 0.999))
    
    # Identify best (cheapest) N periods
    best_periods = daytime_periods[:min(grid_periods_needed, len(daytime_periods))]
    best_period_indices = [p["index"] for p in best_periods]
    
    # Check if current period (index 0) is in best periods
    current_is_best = 0 in best_period_indices
    
    # Find current period's rank
    current_rank = None
    for rank, p in enumerate(daytime_periods, 1):
        if p["index"] == 0:
            current_rank = rank
            break
    
    # Get current period info
    current_period = None
    for p in daytime_periods:
        if p["index"] == 0:
            current_period = p
            break
    
    return {
        "needs_grid_charging": True,
        "grid_energy_needed_kwh": grid_energy_needed_kwh,
        "grid_periods_needed": grid_periods_needed,
        "best_grid_periods": best_periods,
        "all_periods": daytime_periods,
        "current_period": current_period,
        "current_is_best": current_is_best,
        "current_rank": current_rank,
        "total_periods": len(daytime_periods),
        "strategy": "grid_charging_needed",
        "worst_acceptable_price": best_periods[-1]["price"] if best_periods else 9999.0
    }


# ═══════════════════════════════════════════════════════════════
# INPUT EXTRACTION & VALIDATION
# ═══════════════════════════════════════════════════════════════

# Extract solar estimates
solar_estimate_remaining = mqtt_data.get("solar_estimate", {}).get("solar_estimate_remaining", 0.0)
solar_surplus_deficit = mqtt_data.get("solar_estimate", {}).get("solar_surplus_deficit", 0.0)

# Clean and validate values
pv_kwh = float(solar_estimate_remaining) if isinstance(solar_estimate_remaining, (int, float)) else 0.0
pv_kwh = max(0.0, pv_kwh)

surplus_deficit = float(solar_surplus_deficit) if isinstance(solar_surplus_deficit, (int, float)) else 0.0

# Calculate load (this is derived, not directly given)
# Note: solar_surplus_deficit already includes all loads + battery charging to 100%
load_kwh = max(0.0, pv_kwh - surplus_deficit)

# Get current solar power (W) for reference
# Note: Not used for sunrise detection (see sunrise_hour logic) but useful for monitoring
try:
    solar_power_w = float(solar_power) if isinstance(solar_power, (int, float)) else 0.0
except NameError:
    solar_power_w = 0.0

# Create display string for kiosk
kiosk_line = f" ☀ {int(pv_kwh)} / ⚡ {int(load_kwh)}"

# Get inverters data safely
try:
    inverters_data = inverters if inverters else {}
except (NameError, AttributeError):
    inverters_data = {}

# Get battery SOC safely
try:
    battery_soc_raw = battery_soc
except NameError:
    battery_soc_raw = 0.0

combined_soc = get_combined_soc(battery_soc_raw, inverters_data, INVERTER_IDS)

# Get battery capacity safely
try:
    battery_capacity_raw = battery_capacity
except NameError:
    battery_capacity_raw = BATTERY_WATT_HOURS

if not isinstance(battery_capacity_raw, (int, float)) or battery_capacity_raw <= 0:
    battery_capacity_raw = BATTERY_WATT_HOURS

battery_kwh = float(battery_capacity_raw) / 1000.0

# Get current prices safely
try:
    buy_now = float(buy_price) if isinstance(buy_price, (int, float)) else 0.0
except (NameError, ValueError, TypeError):
    buy_now = 0.0

try:
    sell_now = float(sell_price) if isinstance(sell_price, (int, float)) else 0.0
except (NameError, ValueError, TypeError):
    sell_now = 0.0

# Get forecasts safely
try:
    buy_fc_raw = buy_forecast if isinstance(buy_forecast, list) else []
except (NameError, TypeError):
    buy_fc_raw = []

try:
    sell_fc_raw = sell_forecast if isinstance(sell_forecast, list) else []
except (NameError, TypeError):
    sell_fc_raw = []

# Clean forecasts
buy_fc_clean = clean_number_list(buy_fc_raw, 9999.0)
sell_fc_clean = clean_number_list(sell_fc_raw, 0.0)

# Apply uncertainty discounting
disc_result = apply_uncertainty_discount(
    buy_fc_clean,
    sell_fc_clean,
    FUTURE_FORECAST_HOURS,
    BUY_UNCERTAINTY_DISCOUNT,
    SELL_UNCERTAINTY_DISCOUNT
)
discounted_buy = disc_result["buy"]
discounted_sell = disc_result["sell"]

# Get current hour safely
try:
    current_hour = interval_time.hour
except (NameError, AttributeError):
    current_hour = 12

# Get sunrise hour safely
# Note: We use sunrise TIME (not solar_power) for GTI day switching because:
# - Need to make decisions at night when solar_power = 0
# - Sunrise time is fixed regardless of weather
# - solar_power varies with cloud cover (rainy days might show 0W at midday)
try:
    sunrise_raw = sunrise
except NameError:
    sunrise_raw = None

sunrise_hour = 6.0  # default (as float for fractional hours)

if isinstance(sunrise_raw, str) and len(sunrise_raw) >= 16:
    try:
        # Extract hour and minutes from ISO format: "2025-11-22T04:47:57..."
        # Position [11:13] = hour, [14:16] = minutes
        hour = int(sunrise_raw[11:13])
        minutes = int(sunrise_raw[14:16])
        sunrise_hour = float(hour) + (float(minutes) / 60.0)
        sunrise_hour = sunrise_hour % 24  # Ensure 0-24 range
    except (ValueError, IndexError):
        pass
else:
    # Try as datetime object
    try:
        sunrise_hour = float(sunrise_raw.hour) + (float(sunrise_raw.minute) / 60.0)
    except (ValueError, AttributeError, TypeError):
        pass

# Classify time period
time_period = classify_time_period(current_hour, sunrise_hour, PEAK_START, PEAK_END)

# Get tomorrow's GTI forecast safely
try:
    gti_tomorrow_raw = gti_sum_tomorrow if isinstance(gti_sum_tomorrow, (int, float)) else 0.0
except NameError:
    gti_tomorrow_raw = 0.0

# Get today's GTI forecast safely
try:
    gti_today_raw = gti_today if isinstance(gti_today, (int, float)) else 0.0
except NameError:
    gti_today_raw = 0.0

# Determine which GTI to use for floor calculation
# Key insight: Before sunrise, we're still in "yesterday's" overnight period,
# but TODAY's solar (ahead of us) is what will recharge the battery
if current_hour < sunrise_hour:
    # Before sunrise - use TODAY's solar (still ahead, will recharge us)
    gti_for_floor = gti_today_raw
    gti_source = "today"
else:
    # After sunrise - use TOMORROW's solar (for tonight's planning)
    gti_for_floor = gti_tomorrow_raw
    gti_source = "tomorrow"

# Classify solar forecast based on the relevant GTI
solar_class = classify_solar_forecast(gti_for_floor, GTI_SUNNY_THRESHOLD, GTI_NORMAL_THRESHOLD)

# Compute evening premium
evening_premium = compute_evening_premium(
    buy_fc_clean,
    sell_fc_clean,
    current_hour,
    PEAK_START,
    PEAK_END
)

# Compute dynamic floor and budget
fb_result = compute_floor_and_budget(
    solar_class,
    evening_premium,
    battery_kwh,
    combined_soc,
    current_hour,
    sunrise_hour,
    CONSERVATIVE_HOUSE_LOAD_KWH_PER_HOUR,
    SUNNY_FLOOR_SOC,
    NORMAL_FLOOR_SOC,
    RAINY_FLOOR_SOC,
    SUNNY_EXPORT_BUDGET,
    NORMAL_EXPORT_BUDGET,
    RAINY_EXPORT_BUDGET,
    EVENING_PREMIUM_LOW,
    EVENING_PREMIUM_HIGH
)
import_floor_soc = fb_result["import_floor"]     # For import decisions
export_floor_soc = fb_result["export_floor"]     # For export decisions
export_budget = fb_result["budget"]
overnight_reserve_soc = fb_result["overnight_reserve_soc"]
overnight_hours = fb_result["overnight_hours"]
overnight_energy_kwh = fb_result["overnight_energy_kwh"]

# ═══════════════════════════════════════════════════════════════
# SMART CHARGING LOGIC - Two-phase optimization
# ═══════════════════════════════════════════════════════════════
# Phase 1: Optimal Timing to Charge to 100% (Cheapest Period Selection)
# Phase 2: Floor Protection at Expensive Prices (Economic Logic)

should_charge_now = False
charge_priority = 50
charge_reason = "auto"
# daytime_strategy = None

if current_hour < PEAK_START:
    # Calculate energy needed to reach 100%
    energy_to_full_kwh = ((100.0 - combined_soc) / 100.0) * battery_kwh
    energy_to_floor_kwh = max(0.0, ((export_floor_soc - combined_soc) / 100.0) * battery_kwh)
    
    # Calculate periods needed (5 kWh per period = 10kW × 0.5h)
    max_charge_per_period_kwh = 5.0
    periods_needed_for_full = max(1, int(energy_to_full_kwh / max_charge_per_period_kwh + 0.999))
    periods_needed_for_floor = max(1, int(energy_to_floor_kwh / max_charge_per_period_kwh + 0.999))
    
    # Calculate periods remaining before 16:00
    periods_until_peak = (PEAK_START - current_hour) * 2  # 30-min periods
    
    if periods_until_peak > 0 and len(discounted_buy) >= periods_until_peak:
        # Get future buy prices before 16:00
        future_buys = discounted_buy[:periods_until_peak]
        
        # Get peak sell prices (for economic justification)
        peak_start_idx = periods_until_peak
        peak_end_idx = peak_start_idx + 8  # 16:00-20:00 (4 hours = 8 periods)
        if peak_end_idx <= len(discounted_sell):
            peak_sells = discounted_sell[peak_start_idx:peak_end_idx]
#            max_peak_sell = max(peak_sells) if peak_sells else 0
            avg_peak_sell = sum(peak_sells) / len(peak_sells) if peak_sells else 0
        else:
            avg_peak_sell = 0
#            max_peak_sell = 0
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 1: Optimal Timing to Charge to 100%
        # ═══════════════════════════════════════════════════════════
        
        if buy_now <= MAX_AM_BUY_PRICE:
            # Price is acceptable - but is timing optimal?
            
            # Sort future prices to find cheapest N periods
            future_buys_sorted = sorted(future_buys)
            
            # Edge case: Need all remaining periods to reach 100%
            if periods_needed_for_full >= periods_until_peak:
                should_charge_now = True
                charge_priority = 50
                charge_reason = f"Optimal charge @ {buy_now:.2f}c (need all {periods_until_peak}p)"
            
            # Normal case: Select N cheapest periods
            elif periods_needed_for_full > 0:
                # Find the Nth cheapest price (threshold)
                threshold_index = min(periods_needed_for_full - 1, len(future_buys_sorted) - 1)
                price_threshold = future_buys_sorted[threshold_index]
                
                # Charge if current price is in the cheapest N periods
                if buy_now <= price_threshold:
                    should_charge_now = True
                    charge_priority = 50
                    charge_reason = f"Optimal charge @ {buy_now:.2f}c (top {periods_needed_for_full} cheapest)"
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 2: Floor Protection at Expensive Prices
        # ═══════════════════════════════════════════════════════════
        
        elif buy_now > MAX_AM_BUY_PRICE and combined_soc < export_floor_soc:
            # Price is expensive AND below floor
            # Evaluate if floor protection is economically justified
            
            future_buys_sorted = sorted(future_buys)
            min_future_buy = min(future_buys) if future_buys else 9999
            
            # Calculate costs and revenue
            cost_now = energy_to_floor_kwh * (buy_now / 100.0)  # $ to reach floor now
#            cost_later = energy_to_floor_kwh * (min_future_buy / 100.0)  # $ to reach floor later
            
            # Estimate peak sell revenue (assuming we can export the floor energy)
            potential_export_kwh = min(energy_to_floor_kwh, 20.0)  # Realistic export limit per inverter
            potential_revenue = potential_export_kwh * (avg_peak_sell / 100.0)  # $ from peak selling
            
            # Economic justification logic
            justified = False
            justification = ""
            priority = 45  # Default for economic floor protection
            
            # Condition 1: Current price is cheaper than future prices
            if buy_now < min_future_buy:
                justified = True
                priority = 45
                justification = f"cheapest @ {buy_now:.2f}c vs {min_future_buy:.2f}c"
            
            # Condition 2: Peak revenue outweighs charge cost
            elif potential_revenue > cost_now:
                justified = True
                priority = 45
                justification = f"profitable (rev ${potential_revenue:.2f} > cost ${cost_now:.2f})"
            
            # Condition 3: Not enough periods remain to reach floor
            elif periods_needed_for_floor >= periods_until_peak:
                justified = True
                priority = 48  # Urgent - must charge now
                justification = f"urgent (need all {periods_until_peak}p)"
            
            if justified:
                should_charge_now = True
                charge_priority = priority
                charge_reason = f"Floor protect {justification}"

# Store smart charging decision for use in priority logic
smart_charge_decision = {
    "should_charge": should_charge_now,
    "priority": charge_priority,
    "reason": charge_reason
}

# Calculate available energy above floor
current_energy_kwh = max(0.0, (combined_soc / 100.0) * battery_kwh)
export_floor_energy_kwh = max(0.0, (export_floor_soc / 100.0) * battery_kwh)
available_above_floor_kwh = max(0.0, current_energy_kwh - export_floor_energy_kwh)

# Compute dynamic sell threshold
dynamic_sell_threshold = compute_dynamic_sell_threshold(
    discounted_sell,
    discounted_buy,
    available_above_floor_kwh,
    SITE_EXPORT_KWH_PER_PERIOD,
    BASE_MIN_SELL_PRICE,
    DESIRED_MARGIN
)

# Analyze overnight sell opportunities (after peak, before sunrise)
overnight_analysis = None
if current_hour >= PEAK_END or current_hour < sunrise_hour:
    # Calculate energy we need to drain to reach target
    target_soc = (TARGET_MORNING_SOC_MIN + TARGET_MORNING_SOC_MAX) / 2.0
    current_energy_kwh_calc = max(0.0, (combined_soc / 100.0) * battery_kwh)
    target_energy_kwh = max(0.0, (target_soc / 100.0) * battery_kwh)
    energy_to_drain_kwh = max(0.0, current_energy_kwh_calc - target_energy_kwh)
    
    overnight_analysis = analyze_overnight_opportunities(
        discounted_sell,
        current_hour,
        sunrise_hour,
        PEAK_END,
        energy_to_drain_kwh,
        SITE_EXPORT_KWH_PER_PERIOD
    )


# ═══════════════════════════════════════════════════════════════
# DECISION LOGIC (Priority-based)
# ═══════════════════════════════════════════════════════════════

action = "auto"

# ───────────────────────────────────────────────────────────────
# Priority 100 — Extreme Price Spike
# ───────────────────────────────────────────────────────────────
if sell_now >= ALWAYS_SELL_PRICE and combined_soc > 5:
    action = decisions.reason(
        "export",
        f"Spike {sell_now}c ≥ {ALWAYS_SELL_PRICE}c",
        priority=100,
        sell=sell_now,
        soc=combined_soc
    )

# ───────────────────────────────────────────────────────────────
# Priority 90 — Negative Buy Price (PAID to charge!)
# ───────────────────────────────────────────────────────────────
if buy_now < 0:
    if not (PEAK_START <= current_hour <= PEAK_END):
        action = decisions.reason(
            "import",
            f"PAID {abs(buy_now):.2f}c to charge!" + kiosk_line,
            priority=90,
            buy=buy_now,
            soc=combined_soc
        )

# ───────────────────────────────────────────────────────────────
# Priority 80 — Negative Feed-in Tariff
# ───────────────────────────────────────────────────────────────
if sell_now < 0:
    if combined_soc >= (FULL_BATTERY - 2):
        # Battery nearly full, curtail exports
        action = decisions.reason(
            "auto_api_curtail",
            "Neg FiT Curtail" + kiosk_line,
            priority=82,
            sell=sell_now,
            soc=combined_soc
        )
        feed_in_power_limitation = 10
    else:
        # Battery has room, just limit exports
        action = decisions.reason(
            "auto",
            "Neg FiT" + kiosk_line,
            priority=80,
            sell=sell_now,
            soc=combined_soc
        )
        feed_in_power_limitation = 10

# ───────────────────────────────────────────────────────────────
# Priority 70 — Rainy Day Extra Urgency (Handled by Smart Charging)
# ───────────────────────────────────────────────────────────────
# Note: Rainy day charging is now handled by smart charging logic above
# which considers floor protection and peak revenue economics

# ───────────────────────────────────────────────────────────────
# Priority 65 — Intelligent Overnight Drain (Forecast-Based)
# ───────────────────────────────────────────────────────────────
if overnight_analysis and overnight_analysis["has_opportunities"]:
    # We're in overnight period and have analyzed opportunities
    target_soc = (TARGET_MORNING_SOC_MIN + TARGET_MORNING_SOC_MAX) / 2.0
    
    # Calculate hours to sunrise for urgency
    if current_hour >= sunrise_hour:
        hours_to_sunrise = (24 - current_hour) + sunrise_hour
    else:
        hours_to_sunrise = sunrise_hour - current_hour
    
    # Calculate house load protection
    house_load_protection_kwh = max(0.0, hours_to_sunrise * CONSERVATIVE_HOUSE_LOAD_KWH_PER_HOUR)
    house_load_protection_soc = (house_load_protection_kwh / battery_kwh) * 100.0
    min_safe_soc = max(TARGET_MORNING_SOC_MIN, house_load_protection_soc)
    
    # Determine if we should sell based on forecast analysis
    should_sell_forecast = False
    sell_reason = ""
    
    if combined_soc > TARGET_MORNING_SOC_MAX:
        # We're above target - need to drain
        
        # Check if this is one of the best periods to sell
        if overnight_analysis["current_is_good"]:
            # This is a top-ranked sell period - definitely sell
            should_sell_forecast = True
            rank = overnight_analysis["current_rank"]
            total = overnight_analysis["total_periods"]
            sell_reason = f"Best period (rank {rank}/{total})"
        
        elif hours_to_sunrise <= 1.0:
            # Less than 1 hour to sunrise - urgent, sell anyway
            should_sell_forecast = True
            sell_reason = f"Urgent ({hours_to_sunrise:.1f}h to sunrise)"
        
        elif hours_to_sunrise <= 2.0 and combined_soc > (TARGET_MORNING_SOC_MAX + 15):
            # Less than 2 hours and still way above target
            should_sell_forecast = True
            sell_reason = f"Critical ({hours_to_sunrise:.1f}h, {combined_soc:.0f}%)"
        
        # If selling, determine appropriate threshold based on situation
        if should_sell_forecast:
            if hours_to_sunrise <= 0.5:
                # Critical - any positive price
                forecast_threshold = 0.01
            elif overnight_analysis["current_is_good"]:
                # Best period - use the worst acceptable price from analysis
                # This is the Nth best price where N = periods_needed
                forecast_threshold = max(0.01, overnight_analysis["worst_acceptable_price"])
            elif hours_to_sunrise <= 2.0:
                # Urgent but not best period - reduce threshold
                forecast_threshold = BASE_MIN_SELL_PRICE * 0.5
            else:
                # Default threshold
                forecast_threshold = BASE_MIN_SELL_PRICE * 0.7
            
            # Ensure we're above safe floor and price threshold
            if sell_now >= forecast_threshold and combined_soc > min_safe_soc:
                action = decisions.reason(
                    "export",
                    f"Drain to {target_soc:.0f}% - {sell_reason} @ {sell_now:.2f}c",
                    priority=65,
                    sell=sell_now,
                    soc=combined_soc,
                    target_soc=target_soc,
                    hours_to_sunrise=round(hours_to_sunrise, 2),
                    min_safe_soc=round(min_safe_soc, 1),
                    forecast_rank=overnight_analysis["current_rank"],
                    forecast_threshold=round(forecast_threshold, 2),
                    periods_needed=overnight_analysis["periods_needed"]
                )

# ───────────────────────────────────────────────────────────────
# Priority 60 — Dynamic Arbitrage Sell
# ───────────────────────────────────────────────────────────────
if sell_now >= 0 and available_above_floor_kwh > 0:
    # During overnight (after peak), reduce threshold to encourage selling
    if current_hour >= PEAK_END or current_hour < sunrise_hour:
        # Overnight: use 70% of normal threshold to be more aggressive
        adjusted_threshold = dynamic_sell_threshold * 0.7
    else:
        # Daytime/Peak: use full threshold
        adjusted_threshold = dynamic_sell_threshold
    
    if sell_now >= adjusted_threshold:
        action = decisions.reason(
            "export",
            f"Arb sell {sell_now:.2f}c thr {adjusted_threshold:.2f}c floor {export_floor_soc:.0f}%",
            priority=60,
            sell=sell_now,
            soc=combined_soc
        )

# ───────────────────────────────────────────────────────────────
# Priority 45, 48, 50 — Smart Charging (Two-Phase Optimization)
# ───────────────────────────────────────────────────────────────
# Priority 50: Optimal cheap charging (cheapest N periods)
# Priority 48: Urgent floor protection (insufficient time left)
# Priority 45: Economic floor protection (profitable or cheapest)
# ───────────────────────────────────────────────────────────────
if smart_charge_decision["should_charge"]:
    if not (PEAK_START <= current_hour <= PEAK_END):
        action = decisions.reason(
            "import",
            str(smart_charge_decision["reason"]) + kiosk_line,
            priority=smart_charge_decision["priority"],
            buy=buy_now,
            soc=combined_soc
        )

# ───────────────────────────────────────────────────────────────
# Priority 40 — Missed Sell Opportunity Logging
# ───────────────────────────────────────────────────────────────
if discounted_sell and available_above_floor_kwh <= 0:
    if sell_now >= max(discounted_sell) and sell_now >= BASE_MIN_SELL_PRICE:
        decisions.reason(
            "auto",
            "Missed sell — SOC at floor",
            priority=40
        )

# ───────────────────────────────────────────────────────────────
# Extract Next Best Periods for Logging
# ───────────────────────────────────────────────────────────────

# Find next best charging period (based on smart charging analysis)
next_charge_period_hour = None
next_charge_period_price = None
next_charge_periods_away = None

if current_hour < PEAK_START and combined_soc < 100.0:
    # Calculate what we need
    energy_to_full_kwh = ((100.0 - combined_soc) / 100.0) * battery_kwh
    periods_needed_for_full = max(1, int(energy_to_full_kwh / 5.0 + 0.999))
    periods_until_peak = (PEAK_START - current_hour) * 2
    
    if periods_until_peak > 0 and len(discounted_buy) >= periods_until_peak:
        # Get future buy prices and sort to find cheapest
        future_buys_with_index = []
        for i in range(1, min(periods_until_peak, len(discounted_buy))):  # Start at 1 (next period)
            period_hour = current_hour + (i * 0.5)
            if period_hour < PEAK_START:
                future_buys_with_index.append({
                    "index": i,
                    "hour": period_hour,
                    "price": discounted_buy[i]
                })
        
        if future_buys_with_index:
            # Sort by price to find cheapest
            future_buys_with_index.sort(key=lambda x: x["price"])
            
            # Take the first cheapest period as "next" (may not be the absolute next in time)
            # This shows when the next good charging opportunity is
            best_future = future_buys_with_index[0]
            next_charge_period_hour = round(best_future["hour"], 1)
            next_charge_period_price = round(best_future["price"], 2)
            next_charge_periods_away = best_future["index"]

# Find next best discharging period (if overnight selling planned)
next_discharge_period_hour = None
next_discharge_period_price = None
next_discharge_periods_away = None

if overnight_analysis and overnight_analysis.get("has_opportunities"):
    best_periods = overnight_analysis.get("best_periods", [])
    if best_periods:
        # Find the first best period that's in the future (index > 0)
        for period in best_periods:
            if period["index"] > 0:
                next_discharge_period_hour = round(period["hour"], 1)
                next_discharge_period_price = round(period["price"], 2)
                next_discharge_periods_away = period["index"]
                break

# ───────────────────────────────────────────────────────────────
# Priority 1 — Default Context Logging
# ───────────────────────────────────────────────────────────────
action = decisions.reason(
    "auto",
    f"{str(time_period)}{kiosk_line}",
    priority=1,
    buy=round(buy_now, 3),
    sell=round(sell_now, 3),
    soc=round(combined_soc, 1),
    solar_class=solar_class,
    gti_for_floor=round(gti_for_floor, 1),
    gti_source=gti_source,
    evening_premium=round(evening_premium, 2),
    import_floor_soc=round(import_floor_soc, 1),
    export_floor_soc=round(export_floor_soc, 1),
    overnight_reserve_soc=round(overnight_reserve_soc, 1),
    overnight_hours=round(overnight_hours, 1),
    overnight_energy_kwh=round(overnight_energy_kwh, 1),
    export_budget_kwh=round(export_budget, 1),
    avail_above_floor_kwh=round(available_above_floor_kwh, 1),
    dyn_sell_thr=round(dynamic_sell_threshold, 2),
    smart_charge=smart_charge_decision["should_charge"],
    smart_charge_reason=smart_charge_decision["reason"],
    pv_kwh=int(pv_kwh),
    load_kwh=int(load_kwh),
    solar_power_w=int(solar_power_w),
    sunrise_hour=round(sunrise_hour, 2),
    surplus_deficit=round(surplus_deficit, 1),
    next_charge_hour=next_charge_period_hour,
    next_charge_price=next_charge_period_price,
    next_charge_periods_away=next_charge_periods_away,
    next_discharge_hour=next_discharge_period_hour,
    next_discharge_price=next_discharge_period_price,
    next_discharge_periods_away=next_discharge_periods_away,
    fip_limitation=feed_in_power_limitation
)
