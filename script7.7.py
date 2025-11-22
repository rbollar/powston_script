# Priority Rules Decision
# Powston Dynamic Arbitrage — v7.7 (Daytime Opportunistic Sell)
# Author: powston.com.au@bol.la

# ═══════════════════════════════════════════════════════════════
# STRATEGY OVERVIEW
# ═══════════════════════════════════════════════════════════════
# Advanced battery arbitrage strategy with:
# - Weather-adaptive floor management (sunny/normal/rainy)
# - Forecast-based optimal charge/discharge timing
# - Two-phase charging (optimal timing + floor protection)
# - Overnight drain to morning target SOC
# - Dynamic sell thresholds based on available energy
# - NEW v7.7: Daytime opportunistic selling (morning + midday arbitrage)
# 
# Key Innovation: Floors step down hourly after peak based on
# remaining hours until sunrise, protecting house load while
# maximizing revenue opportunities.
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# STRATEGY CONFIGURATION
# ═══════════════════════════════════════════════════════════════
# Core parameters controlling battery arbitrage strategy.
# Tune these values based on your:
# - House load patterns (HOUSE_LOAD_KWH_PER_HOUR)
# - Local solar conditions (GTI thresholds)
# - Risk tolerance (floor SOC values)
# - Electricity prices (margin requirements)
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    # ─────────────────────────────────────────────────────────
    # Time Windows
    # ─────────────────────────────────────────────────────────
    "PEAK_START": 16,              # Peak period starts (evening demand)
    "PEAK_END": 20,                # Peak period ends
    "DAYTIME_BUY_START_HOUR": 9,   # When daytime charging window begins
    
    # ─────────────────────────────────────────────────────────
    # Price Thresholds (c/kWh)
    # ─────────────────────────────────────────────────────────
    "MAX_AM_BUY_PRICE": 10.0,      # Maximum acceptable buy price
    "BASE_MIN_SELL_PRICE": 5.0,    # Minimum acceptable sell price
    "ALWAYS_SELL_PRICE": 35.0,     # Price spike threshold - sell regardless
    "DESIRED_MARGIN": 5.0,         # Target profit margin above buy price
    
    # ─────────────────────────────────────────────────────────
    # Forecast Settings
    # ─────────────────────────────────────────────────────────
    "FUTURE_FORECAST_HOURS": 8,             # How far ahead to look
    "BUY_UNCERTAINTY_DISCOUNT": 0.03,       # Increase buy prices for caution (3%)
    "SELL_UNCERTAINTY_DISCOUNT": 0.07,      # Decrease sell prices for caution (7%)
    
    # ─────────────────────────────────────────────────────────
    # House Load (Per Inverter)
    # ─────────────────────────────────────────────────────────
    # CRITICAL: This is per 50kWh inverter, not total system
    # Total house load = 2 × HOUSE_LOAD_KWH_PER_HOUR
    # Tuned based on actual overnight consumption: ~2.72 kWh/h observed
    # Rounded up to 2.75 for safety margin
    # ─────────────────────────────────────────────────────────
    "HOUSE_LOAD_KWH_PER_HOUR": 2.75,       # Conservative estimate per inverter
    
    # ─────────────────────────────────────────────────────────
    # Solar Classification (GTI W·h/m²)
    # ─────────────────────────────────────────────────────────
    # Global Tilted Irradiance thresholds for classifying days:
    # - Sunny: ≥ 6000 → aggressive selling (low floor, trust recharge)
    # - Normal: 3500-6000 → balanced strategy
    # - Rainy: < 3500 → conservative (high floor, no recharge expected)
    # ─────────────────────────────────────────────────────────
    "GTI_SUNNY_THRESHOLD": 6000.0,
    "GTI_NORMAL_THRESHOLD": 3500.0,
    
    # ─────────────────────────────────────────────────────────
    # SOC Floors by Weather (Per Inverter %)
    # ─────────────────────────────────────────────────────────
    # Base safety buffer added to overnight house load reserve
    # Determines minimum SOC before overnight consumption
    # Lower floor = more aggressive selling = higher revenue risk
    # ─────────────────────────────────────────────────────────
    "SUNNY_FLOOR_SOC": 7.5,        # Aggressive (solar will recharge tomorrow)
    "NORMAL_FLOOR_SOC": 17.5,      # Balanced (moderate recharge expected)
    "RAINY_FLOOR_SOC": 30.0,       # Conservative (may not recharge)
    
    # ─────────────────────────────────────────────────────────
    # Export Budgets by Weather (kWh per inverter)
    # ─────────────────────────────────────────────────────────
    # Maximum energy to sell during peak based on solar forecast
    # Scaled by evening premium (peak sell - daytime buy prices)
    # Higher premium = larger budget
    # ─────────────────────────────────────────────────────────
    "SUNNY_EXPORT_BUDGET": 20.0,   # Can sell more when recharge likely
    "NORMAL_EXPORT_BUDGET": 12.5,  # Moderate selling
    "RAINY_EXPORT_BUDGET": 5.0,    # Minimal selling when no recharge
    
    # ─────────────────────────────────────────────────────────
    # Morning Target SOC (%)
    # ─────────────────────────────────────────────────────────
    # Overnight drain strategy aims to reach this range by sunrise
    # Benefits:
    # - Low SOC = more capacity for cheap solar charging
    # - Avoids curtailment during high solar generation
    # - Maximizes use of free solar energy
    # ─────────────────────────────────────────────────────────
    "TARGET_MORNING_SOC_MIN": 10.0,
    "TARGET_MORNING_SOC_MAX": 20.0,
    
    # ─────────────────────────────────────────────────────────
    # Overnight Threshold Scaling
    # ─────────────────────────────────────────────────────────
    # Reduce sell price threshold overnight to encourage draining
    # 0.70 = accept prices 30% lower than daytime threshold
    # Helps reach morning target SOC reliably
    # ─────────────────────────────────────────────────────────
    "OVERNIGHT_THRESHOLD_FACTOR": 0.70,
    
    # ─────────────────────────────────────────────────────────
    # NEW v7.7: Daytime Opportunistic Selling
    # ─────────────────────────────────────────────────────────
    # Catch profitable sell opportunities throughout the day
    # Two phases:
    #   1. Morning aggressive (low SOC, PV imminent)
    #   2. Midday arbitrage (high SOC, grid glitches)
    # ─────────────────────────────────────────────────────────
    "DAYTIME_OPPORTUNISTIC_SELL_PRICE": 5.0,   # Minimum sell price (5¢+)
    "DAYTIME_ARBITRAGE_MARGIN": 3.0,           # Must beat future buy by 3¢
    
    # PV generation start (hours after sunrise, by weather)
    "SUNNY_PV_OFFSET": 1.0,    # 1h after sunrise on sunny days
    "NORMAL_PV_OFFSET": 2.0,   # 2h after sunrise on normal days
    "RAINY_PV_OFFSET": 3.0,    # 3h after sunrise on rainy days
    
    "DAYTIME_SAFETY_MARGIN": 1.5,  # Safety factor for midday arbitrage
}


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def apply_discount(forecast, hours, discount_rate):
    """
    Apply exponential discounting to price forecasts.
    
    Accounts for forecast uncertainty - predictions further in the 
    future are less reliable. Creates conservative estimates:
    - Buy prices: Increased (pessimistic - assume higher cost)
    - Sell prices: Decreased (conservative - assume lower revenue)
    
    Formula: price[i] * (1 + discount_rate)^i
    
    Args:
        forecast: List of future prices (c/kWh)
        hours: Number of hours/periods to discount
        discount_rate: Rate per period (0.03 = 3% per period)
    
    Returns:
        List of discounted prices matching input length
    
    Example:
        buy_forecast = [10, 12, 15]
        discounted = apply_discount(buy_forecast, 3, 0.03)
        # Returns: [10.0, 12.36, 15.92] - prices increase with uncertainty
    """
    if not forecast or hours <= 0:
        return []
    return [forecast[i] * ((1 + discount_rate) ** i) for i in range(min(hours, len(forecast)))]


def classify_solar(gti, cfg):
    """
    Classify solar forecast as sunny, normal, or rainy.
    
    Uses Global Tilted Irradiance (W·h/m²) to determine expected
    solar generation and adjust strategy accordingly:
    - Sunny: Aggressive selling, low floors (confident in recharge)
    - Normal: Balanced approach
    - Rainy: Conservative, high floors (protect against no recharge)
    
    Args:
        gti: Global tilted irradiance forecast (W·h/m²)
        cfg: CONFIG dictionary with thresholds
    
    Returns:
        String: "sunny", "normal", or "rainy"
    
    Example:
        gti = 6500  # W·h/m²
        classify_solar(gti, CONFIG)  # Returns: "sunny"
    """
    if gti >= cfg["GTI_SUNNY_THRESHOLD"]:
        return "sunny"
    elif gti >= cfg["GTI_NORMAL_THRESHOLD"]:
        return "normal"
    return "rainy"


def compute_evening_premium(buy_fc, sell_fc, hour, cfg):
    """
    Calculate evening premium: peak sell prices vs daytime buy prices.
    
    The premium represents arbitrage opportunity:
    High premium = Buy cheap during day, sell expensive at peak
    Low/negative premium = No arbitrage opportunity
    
    Used to scale export budgets - only sell aggressively when
    there's a clear profit opportunity.
    
    Args:
        buy_fc: Buy price forecast (c/kWh)
        sell_fc: Sell price forecast (c/kWh)
        hour: Current hour
        cfg: CONFIG dictionary
    
    Returns:
        Float: Premium in c/kWh (max_peak_sell - min_daytime_buy)
    
    Example:
        If peak sells at 15c and daytime buys at 8c:
        Premium = 7c/kWh → Good arbitrage opportunity
    """
    daytime = [
        buy_fc[i]
        for i in range(min(len(buy_fc), len(sell_fc)))
        if cfg["DAYTIME_BUY_START_HOUR"] <= (hour + i) % 24 < cfg["PEAK_START"]
    ]
    peak = [
        sell_fc[i]
        for i in range(min(len(buy_fc), len(sell_fc)))
        if cfg["PEAK_START"] <= (hour + i) % 24 <= cfg["PEAK_END"]
    ]
    return max(peak) - min(daytime) if daytime and peak else 0.0


def compute_floor(solar_class, evening_premium, soc, hour, sunrise, battery_wh, cfg):
    """
    Compute dynamic SOC floor and export budget.
    
    Floor = Base safety margin + Overnight house load reserve
    
    The floor protects:
    1. Base solar buffer (varies by weather forecast)
    2. House load until sunrise (calculated from remaining hours)
    
    Floor steps down each hour after peak as sunrise approaches,
    allowing more selling while maintaining house load protection.
    
    Args:
        solar_class: "sunny", "normal", or "rainy"
        evening_premium: Arbitrage opportunity (c/kWh)
        soc: Current battery SOC (%)
        hour: Current hour
        sunrise: Sunrise hour (float, e.g., 4.78 = 04:47)
        battery_wh: Battery capacity (Wh)
        cfg: CONFIG dictionary
    
    Returns:
        Dict with:
        - import_floor: Minimum SOC for import decisions (%)
        - export_floor: Minimum SOC for export decisions (%)
        - budget: Available export budget (kWh)
        - overnight_reserve_soc: SOC needed for house load (%)
        - overnight_hours: Hours until sunrise
    
    Example at 20:00 on sunny day:
        Base floor: 7.5%
        Hours to sunrise: 8.78h
        House load: 8.78h × 2.75 kWh/h = 24.1 kWh = 47.3%
        Total floor: 7.5% + 47.3% = 54.8%
    """
    # Select base values by weather classification
    if solar_class == "sunny":
        base_floor = cfg["SUNNY_FLOOR_SOC"]
        base_budget = cfg["SUNNY_EXPORT_BUDGET"]
    elif solar_class == "rainy":
        base_floor = cfg["RAINY_FLOOR_SOC"]
        base_budget = cfg["RAINY_EXPORT_BUDGET"]
    else:
        base_floor = cfg["NORMAL_FLOOR_SOC"]
        base_budget = cfg["NORMAL_EXPORT_BUDGET"]

    # Calculate overnight requirements from peak start to sunrise
    if cfg["PEAK_START"] >= sunrise:
        hours_peak_to_sunrise = (24 - cfg["PEAK_START"]) + sunrise
    else:
        hours_peak_to_sunrise = sunrise - cfg["PEAK_START"]

    overnight_reserve_soc = (
        hours_peak_to_sunrise
        * cfg["HOUSE_LOAD_KWH_PER_HOUR"]
        / (battery_wh / 1000.0)
    ) * 100.0

    # Before peak: Target 100% for imports, protect peak-to-sunrise for exports
    if hour < cfg["PEAK_START"]:
        import_floor = 100.0
        export_floor = base_floor + overnight_reserve_soc
        overnight_hours = hours_peak_to_sunrise
    else:
        # After peak: Both floors step down together as sunrise approaches
        hours_to_sunrise = ((24 - hour) + sunrise) if hour >= sunrise else (sunrise - hour)
        overnight_hours = max(0.0, hours_to_sunrise)
        overnight_reserve_soc = (
            overnight_hours
            * cfg["HOUSE_LOAD_KWH_PER_HOUR"]
            / (battery_wh / 1000.0)
        ) * 100.0
        import_floor = base_floor + overnight_reserve_soc
        export_floor = base_floor + overnight_reserve_soc

    # Scale budget by evening premium
    low = cfg["DESIRED_MARGIN"]
    high = 2 * cfg["DESIRED_MARGIN"]

    if evening_premium <= low:
        budget_factor = 0.0  # No arbitrage opportunity
    elif evening_premium <= high:
        budget_factor = 0.5  # Moderate opportunity
    else:
        budget_factor = 1.0  # Strong opportunity

    budget = base_budget * budget_factor
    
    # Limit budget to available energy above floor
    available_kwh = max(0.0, (soc - export_floor) / 100.0 * battery_wh / 1000.0)
    budget = min(budget, available_kwh)

    return {
        "import_floor": max(0.0, import_floor),
        "export_floor": max(0.0, export_floor),
        "budget": budget,
        "overnight_reserve_soc": overnight_reserve_soc,
        "overnight_hours": overnight_hours,
    }


def smart_charging(soc, export_floor, buy_fc, sell_fc, buy_now, hour, battery_wh, max_charge_kwh, cfg):
    """
    Determine smart charging strategy with two-phase optimization.
    
    Phase 1: Optimal Timing (when buy price ≤ MAX_AM_BUY_PRICE)
    - Ranks all future periods by price
    - Charges during the cheapest N periods needed to reach 100%
    - Maximizes use of low-cost energy
    
    Phase 2: Floor Protection (when buy price > MAX_AM_BUY_PRICE)
    - Only charges if below floor AND economically justified
    - Three justification criteria:
      a) Cheapest future price (no better opportunity coming)
      b) Profitable vs peak sell revenue (charge cost < sell revenue)
      c) Urgent (insufficient time remaining to reach floor)
    
    Args:
        soc: Current battery SOC (%)
        export_floor: Minimum SOC for exports (%)
        buy_fc: Discounted buy forecast (c/kWh)
        sell_fc: Discounted sell forecast (c/kWh)
        buy_now: Current buy price (c/kWh)
        hour: Current hour
        battery_wh: Battery capacity (Wh)
        max_charge_kwh: Max charge per period (kWh)
        cfg: CONFIG dictionary
    
    Returns:
        Dict with:
        - should_charge: Boolean
        - priority: 45 (economic), 48 (urgent), or 50 (optimal)
        - reason: Human-readable explanation
    
    Example:
        At 09:00 with 60% SOC, buy price 8c:
        - Need 20 kWh to reach 100% = 4 periods
        - Future prices: [8, 9, 7, 10, 8, 9]
        - Sorted: [7, 8, 8, 9, 9, 10]
        - Current (8c) is 2nd cheapest of next 6 periods
        - Decision: CHARGE (in top 4 cheapest)
    """
    if hour >= cfg["PEAK_START"] or not buy_fc:
        return {"should_charge": False, "priority": 50, "reason": "auto"}

    battery_kwh = battery_wh / 1000.0
    energy_to_full = ((100.0 - soc) / 100.0) * battery_kwh
    energy_to_floor = max(0.0, ((export_floor - soc) / 100.0) * battery_kwh)
    periods_full = max(1, int(energy_to_full / max_charge_kwh + 0.999))
    periods_floor = max(1, int(energy_to_floor / max_charge_kwh + 0.999))
    periods_left = int((cfg["PEAK_START"] - hour) * 2)

    if periods_left <= 0 or len(buy_fc) < periods_left:
        return {"should_charge": False, "priority": 50, "reason": "auto"}

    future_buys = buy_fc[:periods_left]
    peak_idx = periods_left
    peak_sells = (
        sell_fc[peak_idx:peak_idx + int((cfg["PEAK_END"] - cfg["PEAK_START"]) * 2)]
        if peak_idx < len(sell_fc)
        else []
    )
    avg_peak_sell = sum(peak_sells) / len(peak_sells) if peak_sells else 0

    # Phase 1: Optimal timing to reach 100%
    if buy_now <= cfg["MAX_AM_BUY_PRICE"]:
        sorted_buys = sorted(future_buys)
        if periods_full >= periods_left:
            # Edge case: Need all remaining periods
            return {
                "should_charge": True,
                "priority": 50,
                "reason": "Optimal charge @ %.2fc (need all %dp)" % (buy_now, periods_left),
            }
        elif periods_full > 0 and buy_now <= sorted_buys[min(periods_full - 1, len(sorted_buys) - 1)]:
            # Normal case: Current price in top N cheapest
            return {
                "should_charge": True,
                "priority": 50,
                "reason": "Optimal charge @ %.2fc (top %d cheapest)" % (buy_now, periods_full),
            }

    # Phase 2: Floor protection (expensive price but below floor)
    elif buy_now > cfg["MAX_AM_BUY_PRICE"] and soc < export_floor:
        min_buy = min(future_buys)
        cost = energy_to_floor * (buy_now / 100.0)
        revenue = min(energy_to_floor, 20.0) * (avg_peak_sell / 100.0)

        # Criterion A: Cheapest available
        if buy_now < min_buy:
            return {
                "should_charge": True,
                "priority": 45,
                "reason": "Floor protect cheapest @ %.2fc vs %.2fc" % (buy_now, min_buy),
            }
        # Criterion B: Profitable vs peak revenue
        elif revenue > cost:
            return {
                "should_charge": True,
                "priority": 45,
                "reason": "Floor protect profitable (rev $%.2f > cost $%.2f)" % (revenue, cost),
            }
        # Criterion C: Insufficient time remaining
        elif periods_floor >= periods_left:
            return {
                "should_charge": True,
                "priority": 48,
                "reason": "Floor protect urgent (need all %dp)" % periods_left,
            }

    return {"should_charge": False, "priority": 50, "reason": "auto"}


def overnight_opportunities(sell_fc, hour, sunrise, soc, battery_wh, max_discharge_kwh, cfg):
    """
    Analyze overnight sell opportunities (from PEAK_START to sunrise).
    
    Identifies best periods to sell battery energy overnight based on:
    1. Price ranking (highest prices first)
    2. Energy needed to drain to morning target SOC
    3. Current period's position in rankings
    
    Strategy:
    - Rank all overnight periods by sell price (high to low)
    - Calculate how many periods needed to reach target SOC
    - Sell during the top N ranked periods only
    
    Args:
        sell_fc: Discounted sell forecast (c/kWh)
        hour: Current hour
        sunrise: Sunrise hour (float)
        soc: Current SOC (%)
        battery_wh: Battery capacity (Wh)
        max_discharge_kwh: Max discharge per period (kWh)
        cfg: CONFIG dictionary
    
    Returns:
        Dict with:
        - has_opportunities: Boolean
        - best_periods: List of top N periods (sorted by price)
        - current_is_good: True if current period is in top N
        - current_rank: Current period's rank (1 = best price)
        - total_periods: Total overnight periods available
        - periods_needed: How many periods needed to drain
        - worst_acceptable_price: Lowest price in top N
        
        Returns None if no opportunities or not in overnight window
    
    Example at 18:00 with 80% SOC:
        Target: 15%
        Energy to drain: 65% = 33 kWh
        Periods needed: 33 / 5 = 7 periods
        Overnight prices: [9.8, 8.5, 7.2, 6.8, ...]
        Best 7: [9.8, 8.5, 7.2, 6.8, 6.5, 6.2, 5.9]
        Current (9.8): rank 1, is_good = True
        Threshold: 5.9c (worst of best 7)
    """
    if not sell_fc:
        return None

    target = (cfg["TARGET_MORNING_SOC_MIN"] + cfg["TARGET_MORNING_SOC_MAX"]) / 2.0
    drain_kwh = max(0.0, ((soc - target) / 100.0) * (battery_wh / 1000.0))

    periods = []
    for i in range(len(sell_fc)):
        period_hour = (hour + i * 0.5) % 24

        # Check if period is in drain window (PEAK_START to sunrise)
        if cfg["PEAK_START"] < sunrise:
            is_overnight = cfg["PEAK_START"] <= period_hour < sunrise
        else:
            is_overnight = period_hour >= cfg["PEAK_START"] or period_hour < sunrise

        if is_overnight:
            periods.append({"index": i, "hour": period_hour, "price": sell_fc[i]})

    if not periods:
        return None

    # Sort by price (highest first) to find best opportunities
    periods = sorted(periods, key=lambda x: x["price"], reverse=True)
    needed = max(1, int(drain_kwh / max_discharge_kwh + 0.999))
    best = periods[:min(needed, len(periods))]

    # Find current period's rank in sorted list
    current_rank = None
    for idx in range(len(periods)):
        if periods[idx]["index"] == 0:
            current_rank = idx + 1
            break

    return {
        "has_opportunities": True,
        "best_periods": best,
        "current_is_good": 0 in [p["index"] for p in best],
        "current_rank": current_rank,
        "total_periods": len(periods),
        "periods_needed": needed,
        "worst_acceptable_price": best[-1]["price"] if best else 0,
    }


def next_best(forecast, hour, end):
    """
    Find next best opportunity in forecast.
    
    Used to display upcoming charge/discharge opportunities in kiosk.
    Excludes current period (index 0), only looks ahead.
    
    Args:
        forecast: Price forecast (c/kWh)
        hour: Current hour
        end: End hour to consider
    
    Returns:
        Dict with hour, price, and periods_away, or None if no opportunities
    
    Example:
        forecast = [10, 8, 12, 7, 9]
        next_best(forecast, 9, 16)
        Returns: {hour: 10.0, price: 7, periods_away: 3}
    """
    if not forecast:
        return None
    periods = [
        {"index": i, "hour": hour + i * 0.5, "price": forecast[i]}
        for i in range(1, len(forecast))
        if hour + i * 0.5 < end
    ]
    if not periods:
        return None
    periods = sorted(periods, key=lambda x: x["price"])
    return {
        "hour": round(periods[0]["hour"], 1),
        "price": round(periods[0]["price"], 2),
        "periods_away": periods[0]["index"],
    }


def build_kiosk_info(
    time_period,
    pv_kwh,
    load_kwh,
    surplus_deficit,
    hour,
    sunrise_hour,
    battery_soc,
    floor_soc,
    battery_kwh,
    next_charge_info,
    next_discharge_info,
    opp_analysis,
    house_load_per_hour
):
    """
    Build context-aware kiosk information line for house displays.
    
    Creates informative single-line status showing:
    - Current generation and load
    - Surplus or deficit situation
    - Next expected action (charge/sell)
    - Time-period specific context
    
    Format varies by time of day:
    - Day: Solar generation, load, next charge opportunity
    - Peak: Export status, floor level, next sell opportunity
    - Night: Load to sunrise, sell opportunities
    
    Args:
        time_period: "Day", "Peak", or "Night"
        pv_kwh: Solar generation remaining today (kWh)
        load_kwh: Forecast house load (kWh)
        surplus_deficit: Net energy balance (+ surplus, - deficit)
        hour: Current hour
        sunrise_hour: Sunrise time (float)
        battery_soc: Current SOC (%)
        floor_soc: Export floor SOC (%)
        battery_kwh: Battery capacity (kWh)
        next_charge_info: Next charge opportunity dict (from next_best)
        next_discharge_info: Next discharge opportunity dict
        opp_analysis: Overnight opportunities dict
        house_load_per_hour: House load rate (kWh/h)
    
    Returns:
        String formatted for display (emojis + compact info)
    
    Examples:
        Day:   "☀138kWh ⚡184kWh ➖46kWh | Next charge 7.5h@6.2c"
        Peak:  "☀0kWh ⚡2kWh ➖2kWh | Avail 11.5kWh to 42%"
        Night: "🌙 Load→☀ 22.8kWh | Next sell 21.0h@8.5c"
    """
    # Core metrics (always shown)
    base = "☀%dkWh ⚡%dkWh" % (int(pv_kwh), int(load_kwh))
    
    # Add surplus/deficit indicator
    if surplus_deficit >= 0:
        base = base + " ➕%dkWh" % int(surplus_deficit)
    else:
        base = base + " ➖%dkWh" % int(abs(surplus_deficit))
    
    # Add time-period specific context
    if time_period == "Day":
        # Daytime: Show next charging opportunity
        if surplus_deficit < 0:
            # Deficit - show when we'll charge
            if next_charge_info:
                h = next_charge_info["hour"]
                p = next_charge_info["price"]
                base = base + " | Next charge %.1fh@%.1fc" % (h, p)
            else:
                base = base + " | No cheap charge periods"
        else:
            # Surplus - indicate we're okay
            base = base + " | Solar covers load"
    
    elif time_period == "Peak":
        # Peak: Show available energy and floor status
        avail_kwh = ((battery_soc - floor_soc) / 100.0) * battery_kwh
        if avail_kwh > 0:
            base = base + " | Avail %.1fkWh to %.0f%%" % (avail_kwh, floor_soc)
        else:
            base = base + " | At floor %.0f%%" % floor_soc
        
        # Show next sell opportunity if available
        if next_discharge_info:
            h = next_discharge_info["hour"]
            p = next_discharge_info["price"]
            base = base + " | Next sell %.1fh@%.1fc" % (h, p)
    
    elif time_period == "Night":
        # Night: Show load to sunrise prominently
        hrs_to_sunrise = ((24 - hour) + sunrise_hour) if hour >= sunrise_hour else (sunrise_hour - hour)
        load_to_sunrise = hrs_to_sunrise * house_load_per_hour
        
        base = "🌙 Load→☀ %.1fkWh" % load_to_sunrise
        
        # Add sell opportunity info
        if next_discharge_info:
            h = next_discharge_info["hour"]
            p = next_discharge_info["price"]
            base = base + " | Next sell %.1fh@%.1fc" % (h, p)
        elif opp_analysis and opp_analysis.get("has_opportunities"):
            # Has opportunities but none upcoming - must be in one now or past best
            avail_kwh = ((battery_soc - floor_soc) / 100.0) * battery_kwh
            if avail_kwh > 0:
                base = base + " | Avail %.1fkWh" % avail_kwh
            else:
                base = base + " | At floor %.0f%%" % floor_soc
        else:
            base = base + " | No good sell periods"
    
    return base


def scalar_sanitise(x):
    """
    Extract float from various formats (dict, scalar, etc.).
    
    Used to safely extract GTI values from weather data which can
    come in various formats (float, dict with 'value' key, etc.)
    
    Args:
        x: Value to extract (float, dict, or other)
    
    Returns:
        Float value, or 0.0 if extraction fails
    """
    try:
        return float(x)
    except Exception:
        try:
            return float(x.get("value"))
        except Exception:
            return 0.0


# ═══════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# Hardware Configuration
# ─────────────────────────────────────────────────────────────
# Extract inverter limits from API
# Each period is 30 minutes (0.5 hours)
# Energy = Power × Time → kWh = kW × 0.5h
# ─────────────────────────────────────────────────────────────
feed_in_power_limitation = optimal_charging
max_charge_kwh_per_period = (optimal_charging / 1000.0) * 0.5
max_discharge_kwh_per_period = (optimal_discharging / 1000.0) * 0.5

# ─────────────────────────────────────────────────────────────
# Input Parsing
# ─────────────────────────────────────────────────────────────
# Extract solar estimates from MQTT data
pv_kwh = mqtt_data.get("solar_estimate", {}).get("solar_estimate_remaining", 0.0)
surplus = mqtt_data.get("solar_estimate", {}).get("solar_surplus_deficit", 0.0)
load_kwh = max(0.0, pv_kwh - surplus)

# Get current hour from interval time
hour = interval_time.hour

# ─────────────────────────────────────────────────────────────
# Sunrise Parsing
# ─────────────────────────────────────────────────────────────
# Parse sunrise robustly (handles both datetime object and ISO string)
# Converts to fractional hour (e.g., 04:47 → 4.78)
# ─────────────────────────────────────────────────────────────
try:
    sunrise_hour = float(sunrise.hour) + float(sunrise.minute) / 60.0
except (AttributeError, TypeError):
    try:
        sunrise_time = sunrise.split("T")[1].split("+")[0].split(".")[0]
        sunrise_parts = sunrise_time.split(":")
        sunrise_hour = float(sunrise_parts[0]) + float(sunrise_parts[1]) / 60.0
    except (AttributeError, IndexError, ValueError):
        sunrise_hour = 6.0

# ─────────────────────────────────────────────────────────────
# Time Period Classification
# ─────────────────────────────────────────────────────────────
if CONFIG["PEAK_START"] <= hour <= CONFIG["PEAK_END"]:
    time_period = "Peak"
elif sunrise_hour <= hour < CONFIG["PEAK_START"]:
    time_period = "Day"
else:
    time_period = "Night"

# ─────────────────────────────────────────────────────────────
# GTI Forecast Selection (Pure Tomorrow After Sunrise)
# ─────────────────────────────────────────────────────────────
# Key insight: After sunrise, we care about TOMORROW's solar for
# tonight's strategy. Use pure tomorrow GTI from hourly forecast.
# 
# Powston's gti_sum_tomorrow is a rolling window that mixes today
# and tomorrow, so we calculate pure tomorrow ourselves when possible.
# ─────────────────────────────────────────────────────────────
if hour >= sunrise_hour:
    # After sunrise: Calculate pure tomorrow GTI
    try:
        hourly_gti = weather_data.get('hourly', {}).get('global_tilted_irradiance_instant', [])
        if len(hourly_gti) >= 48:
            # Hourly array has 48 hours: [0-23]=today, [24-47]=tomorrow
            gti = float(sum(hourly_gti[24:48]))
            gti_src = "tomorrow_pure"
        else:
            # Fallback to Powston's calculation (mixed)
            gti = scalar_sanitise(gti_sum_tomorrow)
            gti_src = "tomorrow_mixed"
    except Exception:
        gti = scalar_sanitise(gti_sum_tomorrow)
        gti_src = "tomorrow_fallback"
else:
    # Before sunrise: Use today's GTI (what's ahead of us)
    gti = scalar_sanitise(gti_today)
    gti_src = "today"

# Classify solar forecast
solar_cls = classify_solar(gti, CONFIG)

# ─────────────────────────────────────────────────────────────
# Forecast Discounting
# ─────────────────────────────────────────────────────────────
# Apply exponential discounting to account for forecast uncertainty
# Buy prices increase (pessimistic), sell prices decrease (conservative)
# ─────────────────────────────────────────────────────────────
buy_disc = apply_discount(
    buy_forecast,
    CONFIG["FUTURE_FORECAST_HOURS"],
    CONFIG["BUY_UNCERTAINTY_DISCOUNT"],
)
sell_disc = apply_discount(
    sell_forecast,
    CONFIG["FUTURE_FORECAST_HOURS"],
    -CONFIG["SELL_UNCERTAINTY_DISCOUNT"],
)

# ─────────────────────────────────────────────────────────────
# Floor and Budget Calculation
# ─────────────────────────────────────────────────────────────
eve_prem = compute_evening_premium(buy_forecast, sell_forecast, hour, CONFIG)
floor = compute_floor(
    solar_cls,
    eve_prem,
    battery_soc,
    hour,
    sunrise_hour,
    battery_capacity,
    CONFIG,
)

# ─────────────────────────────────────────────────────────────
# Smart Charging Analysis
# ─────────────────────────────────────────────────────────────
sc = smart_charging(
    battery_soc,
    floor["export_floor"],
    buy_disc,
    sell_disc,
    buy_price,
    hour,
    battery_capacity,
    max_charge_kwh_per_period,
    CONFIG,
)

# ─────────────────────────────────────────────────────────────
# Available Energy Above Floor
# ─────────────────────────────────────────────────────────────
avail_soc = max(0.0, battery_soc - floor["export_floor"])

# ─────────────────────────────────────────────────────────────
# Dynamic Sell Threshold
# ─────────────────────────────────────────────────────────────
# Calculates minimum acceptable sell price based on:
# 1. Available energy above floor
# 2. How many periods needed to export it
# 3. Forecasted sell prices (ranked)
# 4. Minimum buy price + margin
# ─────────────────────────────────────────────────────────────
thr = 9999.0
if sell_disc:
    positive_sells = [s for s in sell_disc if s > 0]
    if positive_sells and avail_soc > 0:
        positive_sells = sorted(positive_sells, reverse=True)
        avail_kwh = (avail_soc / 100.0) * (battery_capacity / 1000.0)
        periods = max(1, int(avail_kwh / max_discharge_kwh_per_period + 0.999))
        thr_sell = (
            min(positive_sells)
            if periods >= len(positive_sells)
            else positive_sells[periods - 1]
        )
        valid_buys = [b for b in buy_disc if b > 0]
        thr = max(
            CONFIG["BASE_MIN_SELL_PRICE"],
            thr_sell,
            (min(valid_buys) if valid_buys else 0.0) + CONFIG["DESIRED_MARGIN"],
        )

# ─────────────────────────────────────────────────────────────
# Overnight Opportunities Analysis
# ─────────────────────────────────────────────────────────────
# Starts analysis at PEAK_START (16:00) not PEAK_END (20:00)
# Allows selling during peak period at best prices
# ─────────────────────────────────────────────────────────────
if CONFIG["PEAK_START"] >= sunrise_hour:
    is_overnight_window = hour >= CONFIG["PEAK_START"] or hour < sunrise_hour
else:
    is_overnight_window = CONFIG["PEAK_START"] <= hour < sunrise_hour

opp = (
    overnight_opportunities(
        sell_disc,
        hour,
        sunrise_hour,
        battery_soc,
        battery_capacity,
        max_discharge_kwh_per_period,
        CONFIG,
    )
    if is_overnight_window
    else None
)

# ─────────────────────────────────────────────────────────────
# Next Best Periods
# ─────────────────────────────────────────────────────────────
# Find upcoming charge/discharge opportunities for kiosk display
# ─────────────────────────────────────────────────────────────
next_ch = (
    next_best(buy_disc, hour, CONFIG["PEAK_START"])
    if hour < CONFIG["PEAK_START"] and battery_soc < 100.0
    else None
)
next_dis = None
if opp:
    for p in opp.get("best_periods", []):
        if p["index"] > 0:
            next_dis = {
                "hour": round(p["hour"], 1),
                "price": round(p["price"], 2),
                "periods_away": p["index"],
            }
            break

# ─────────────────────────────────────────────────────────────
# Build Kiosk Information Line
# ─────────────────────────────────────────────────────────────
kiosk = build_kiosk_info(
    time_period=time_period,
    pv_kwh=pv_kwh,
    load_kwh=load_kwh,
    surplus_deficit=surplus,
    hour=hour,
    sunrise_hour=sunrise_hour,
    battery_soc=battery_soc,
    floor_soc=floor["export_floor"],
    battery_kwh=battery_capacity / 1000.0,
    next_charge_info=next_ch,
    next_discharge_info=next_dis,
    opp_analysis=opp,
    house_load_per_hour=CONFIG["HOUSE_LOAD_KWH_PER_HOUR"]
)

# ═══════════════════════════════════════════════════════════════
# DECISION LOGIC (Priority-based)
# ═══════════════════════════════════════════════════════════════
# Decisions are evaluated in priority order (highest first).
# Once a higher priority decision is made, it overrides lower ones.
# Priority ranges:
#   100: Extreme price spikes (always sell)
#   90:  Hard overrides (negative pricing)
#   75:  NEW v7.7: Daytime opportunistic selling
#   65:  Overnight drain to morning target
#   60:  Arbitrage opportunities
#   45-50: Smart charging (optimal & floor protection)
#   41-42: Negative FiT handling
#   40:  Missed opportunity logging
#   1:   Default context/info
# ═══════════════════════════════════════════════════════════════

action = "auto"

# ───────────────────────────────────────────────────────────────
# Priority 100 — Extreme Price Spike
# ───────────────────────────────────────────────────────────────
# Sell immediately regardless of floor when price is exceptional
# This overrides all other logic - revenue opportunity too good to miss
# ───────────────────────────────────────────────────────────────
if sell_price >= CONFIG["ALWAYS_SELL_PRICE"] and battery_soc > 5:
    action = decisions.reason(
        "export",
        "Spike %.1fc >= %.0fc" % (sell_price, CONFIG["ALWAYS_SELL_PRICE"]),
        priority=100,
        sell=sell_price,
        soc=battery_soc,
    )

# ───────────────────────────────────────────────────────────────
# Priority 90 — Negative Buy Price (PAID to import!)
# ───────────────────────────────────────────────────────────────
# Grid pays you to import - always take advantage
# If battery full, curtail solar and import for house
# If battery has room, charge battery
# ───────────────────────────────────────────────────────────────
if buy_price < 0:
    if not (CONFIG["PEAK_START"] <= hour <= CONFIG["PEAK_END"]):
        if battery_soc >= 98:
            # Battery full - curtail solar, import for house
            feed_in_power_limitation = 10
            action = decisions.reason(
                "import",
                "PAID %.2fc + solar curtail " % abs(buy_price) + kiosk,
                priority=90,
                buy=buy_price,
                soc=battery_soc,
            )
        else:
            # Battery has room - charge it
            feed_in_power_limitation = 10000
            action = decisions.reason(
                "import",
                "PAID %.2fc to charge! " % abs(buy_price) + kiosk,
                priority=90,
                buy=buy_price,
                soc=battery_soc,
            )

# ───────────────────────────────────────────────────────────────
# Priority 75 — NEW v7.7: Daytime Opportunistic Sell
# ───────────────────────────────────────────────────────────────
# Catch profitable sell opportunities throughout the day
# Two phases:
#   1. Morning aggressive (low SOC, PV generation imminent)
#   2. Midday arbitrage (high SOC, grid price glitches)
# ───────────────────────────────────────────────────────────────
if sunrise_hour <= hour < CONFIG["PEAK_START"] and sell_price >= CONFIG["DAYTIME_OPPORTUNISTIC_SELL_PRICE"]:
    
    # Calculate when meaningful PV generation starts (weather-dependent)
    if solar_cls == "rainy":
        pv_offset = CONFIG["RAINY_PV_OFFSET"]
    elif solar_cls == "sunny":
        pv_offset = CONFIG["SUNNY_PV_OFFSET"]
    else:
        pv_offset = CONFIG["NORMAL_PV_OFFSET"]
    
    pv_generation_hour = sunrise_hour + pv_offset
    
    # Find cheapest future buy before peak
    periods_until_peak = int((CONFIG["PEAK_START"] - hour) * 2)
    if buy_disc and periods_until_peak > 0:
        min_future_buy = min(buy_disc[:periods_until_peak])
        
        # Is this price opportunity worth taking?
        # Either: beats current buy, or beats future buy + margin
        price_opportunity = (
            sell_price >= (buy_price - 2.0) or
            sell_price >= (min_future_buy + CONFIG["DAYTIME_ARBITRAGE_MARGIN"])
        )
        
        if price_opportunity:
            # PHASE 1: Morning Aggressive (PV coming soon)
            if hour < pv_generation_hour:
                # Before PV starts - can sell aggressively
                # Only need enough to reach PV generation time
                hours_to_pv = pv_generation_hour - hour
                energy_to_pv = hours_to_pv * CONFIG["HOUSE_LOAD_KWH_PER_HOUR"]
                min_soc_for_pv = (energy_to_pv / (battery_capacity / 1000.0)) * 100.0
                
                # Can sell if we're above minimum + small buffer
                if battery_soc > (min_soc_for_pv + 5):
                    action = decisions.reason(
                        "export",
                        "Morning arb %.1fc, PV in %.1fh @ %.1f" % (
                            sell_price, hours_to_pv, pv_generation_hour
                        ),
                        priority=75,
                        sell=sell_price,
                        soc=battery_soc,
                        min_soc_for_pv=round(min_soc_for_pv, 1),
                        hours_to_pv=round(hours_to_pv, 2)
                    )
            
            # PHASE 2: Midday/Afternoon Arbitrage (Grid glitches)
            else:
                # After PV has started - normal arbitrage
                # Use already-calculated next cheap buy period
                if next_ch:
                    hours_to_cheap_buy = next_ch["periods_away"] * 0.5
                    energy_to_cheap_buy = hours_to_cheap_buy * CONFIG["HOUSE_LOAD_KWH_PER_HOUR"] * CONFIG["DAYTIME_SAFETY_MARGIN"]
                    min_soc_needed = (energy_to_cheap_buy / (battery_capacity / 1000.0)) * 100.0
                else:
                    # No cheap buy period found - use conservative reserve
                    min_soc_needed = 20.0
                
                if battery_soc > (min_soc_needed + 15):
                    action = decisions.reason(
                        "export",
                        "Day arb %.1fc vs buy %.1fc" % (sell_price, min_future_buy),
                        priority=75,
                        sell=sell_price,
                        soc=battery_soc,
                        min_future_buy=round(min_future_buy, 2),
                        min_soc_needed=round(min_soc_needed, 1)
                    )

# ───────────────────────────────────────────────────────────────
# Priority 65 — Intelligent Overnight Drain (Forecast-Based)
# ───────────────────────────────────────────────────────────────
# Drain battery to morning target (10-20%) using ranked sell periods
# Only sells during best-priced periods to maximize revenue
# Respects export floor to protect house load
# ───────────────────────────────────────────────────────────────
if opp and opp["has_opportunities"] and battery_soc > CONFIG["TARGET_MORNING_SOC_MAX"]:
    target = (CONFIG["TARGET_MORNING_SOC_MIN"] + CONFIG["TARGET_MORNING_SOC_MAX"]) / 2.0
    hrs = ((24 - hour) + sunrise_hour) if hour >= sunrise_hour else (sunrise_hour - hour)

    should_sell = False
    reason = ""

    # Determine if we should sell this period
    if opp["current_is_good"]:
        should_sell = True
        reason = "Best period (rank %d/%d)" % (opp["current_rank"], opp["total_periods"])
    elif hrs <= 1.0:
        should_sell = True
        reason = "Urgent (%.1fh to sunrise)" % hrs
    elif hrs <= 2.0 and battery_soc > CONFIG["TARGET_MORNING_SOC_MAX"] + 15:
        should_sell = True
        reason = "Critical (%.1fh, %.0f%%)" % (hrs, battery_soc)

    if should_sell:
        # Calculate appropriate threshold based on urgency
        if hrs <= 0.5:
            forecast_thr = 0.01
        elif opp["current_is_good"]:
            forecast_thr = max(0.01, opp["worst_acceptable_price"])
        elif hrs <= 2.0:
            forecast_thr = CONFIG["BASE_MIN_SELL_PRICE"] * 0.5
        else:
            forecast_thr = CONFIG["BASE_MIN_SELL_PRICE"] * 0.7

        # Check price and floor before selling
        if sell_price >= forecast_thr and battery_soc > floor["export_floor"]:
            action = decisions.reason(
                "export",
                "Drain to %.0f%% - %s @ %.2fc" % (target, reason, sell_price),
                priority=65,
                sell=sell_price,
                soc=battery_soc,
                target_soc=target,
                hours_to_sunrise=round(hrs, 2),
                min_safe_soc=round(floor["export_floor"], 1),
                forecast_rank=opp["current_rank"],
                forecast_threshold=round(forecast_thr, 2),
                periods_needed=opp["periods_needed"],
            )

# ───────────────────────────────────────────────────────────────
# Priority 60 — Dynamic Arbitrage Sell
# ───────────────────────────────────────────────────────────────
# Sell when price beats dynamic threshold
# Threshold based on available energy and forecast ranking
# More aggressive overnight (70% of normal threshold)
# ───────────────────────────────────────────────────────────────
if sell_price >= 0 and avail_soc > 0:
    # Adjust threshold for overnight period
    if hour >= CONFIG["PEAK_END"] or hour < sunrise_hour:
        adj_thr = thr * CONFIG["OVERNIGHT_THRESHOLD_FACTOR"]
    else:
        adj_thr = thr

    if sell_price >= adj_thr:
        action = decisions.reason(
            "export",
            "Arb sell %.2fc thr %.2fc floor %.0f%%" % (sell_price, adj_thr, floor["export_floor"]),
            priority=60,
            sell=sell_price,
            soc=battery_soc,
        )

# ───────────────────────────────────────────────────────────────
# Priority 45, 48, 50 — Smart Charging (Two-Phase Optimization)
# ───────────────────────────────────────────────────────────────
# Priority 50: Optimal cheap charging (cheapest N periods)
# Priority 48: Urgent floor protection (insufficient time left)
# Priority 45: Economic floor protection (profitable or cheapest)
# ───────────────────────────────────────────────────────────────
if sc["should_charge"] and not (CONFIG["PEAK_START"] <= hour <= CONFIG["PEAK_END"]):
    feed_in_power_limitation = optimal_charging
    action = decisions.reason(
        "import",
        str(sc["reason"]) + " " + kiosk,
        priority=sc["priority"],
        buy=buy_price,
        soc=battery_soc,
    )

# ───────────────────────────────────────────────────────────────
# Priority 41/42 — Negative Feed-in Tariff (Solar Curtailment)
# ───────────────────────────────────────────────────────────────
# When exporting costs money AND battery is full, curtail solar
# If battery has capacity, let it charge from solar (no curtailment)
# Only curtail when we'd be forced to export at negative prices
# ───────────────────────────────────────────────────────────────
if sell_price < 0 and not sc["should_charge"]:
    
    if battery_soc >= 98:
        # Battery full - must curtail solar to avoid negative FiT export
        feed_in_power_limitation = 10
        action = decisions.reason(
            "auto_api_curtail",
            "Neg FiT Curtail " + kiosk,
            priority=42,
            sell=sell_price,
            soc=battery_soc,
        )
    else:
        # Battery has room - let it charge from solar, no curtailment needed
        feed_in_power_limitation = 10000
        action = decisions.reason(
            "auto",
            "Neg FiT, batt charging " + kiosk,
            priority=41,
            sell=sell_price,
            soc=battery_soc,
        )

# ───────────────────────────────────────────────────────────────
# Priority 40 — Missed Sell Opportunity Logging
# ───────────────────────────────────────────────────────────────
# Log when price is good but can't sell due to insufficient SOC
# Informational only - helps tune floor settings
# ───────────────────────────────────────────────────────────────
if sell_disc and avail_soc <= 0:
    if sell_price >= max(sell_disc) and sell_price >= CONFIG["BASE_MIN_SELL_PRICE"]:
        action = decisions.reason(
            "auto",
            "Missed sell — SOC at floor",
            priority=40
        )

# ───────────────────────────────────────────────────────────────
# Priority 1 — Default Context Logging
# ───────────────────────────────────────────────────────────────
# Always executes last to provide comprehensive state information
# All key variables logged for analysis and debugging
# ───────────────────────────────────────────────────────────────
action = decisions.reason(
    "auto",
    time_period + " " + kiosk,
    priority=1,
    buy=round(buy_price, 3),
    sell=round(sell_price, 3),
    soc=round(battery_soc, 1),
    solar_class=solar_cls,
    gti_for_floor=round(gti, 1),
    gti_source=gti_src,
    evening_premium=round(eve_prem, 2),
    import_floor_soc=round(floor["import_floor"], 1),
    export_floor_soc=round(floor["export_floor"], 1),
    overnight_reserve_soc=round(floor["overnight_reserve_soc"], 1),
    overnight_hours=round(floor["overnight_hours"], 1),
    overnight_energy_kwh=round(
        floor["overnight_hours"] * CONFIG["HOUSE_LOAD_KWH_PER_HOUR"], 1
    ),
    export_budget_kwh=round(floor["budget"], 1),
    avail_above_floor_soc=round(avail_soc, 1),
    dyn_sell_thr=round(thr, 2),
    smart_charge=sc["should_charge"],
    smart_charge_reason=sc["reason"],
    pv_kwh=int(pv_kwh),
    load_kwh=int(load_kwh),
    solar_power_w=int(solar_power),
    sunrise_hour=round(sunrise_hour, 2),
    surplus_deficit=round(surplus, 1),
    next_charge_hour=next_ch["hour"] if next_ch else None,
    next_charge_price=next_ch["price"] if next_ch else None,
    next_charge_periods_away=next_ch["periods_away"] if next_ch else None,
    next_discharge_hour=next_dis["hour"] if next_dis else None,
    next_discharge_price=next_dis["price"] if next_dis else None,
    next_discharge_periods_away=next_dis["periods_away"] if next_dis else None,
    fip_limitation=feed_in_power_limitation,
    raw_current_hour=interval_time.hour,
    interval_time_str=str(interval_time),
)
