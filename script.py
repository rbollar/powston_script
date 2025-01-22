# Powston Inverter Decision Script
# Comments to powston.com.au@bol.la

# User-entered data

# Pricing Decisions
max_buy_price = 10.0  # Maximum energy purchase (Import) price in cents / kWh
max_am_buy_price = 20.0  # In very low battery state, max price to pay to charge battery to be past AM peak in cents / kWh
min_sell_price = 25.0  # Minimum energy sell (Export) price in cents / kWh
min_day_sell_price = 15.0  # Daytime minimum energy sell (Export) price in cents / kWh
always_sell_price = 75.0  # The price to sell (Export) regardless of remaining storage in cents / kWh
min_sell_soc = 10  # The minimum battery State of Charge to make a sell decision 10 = 10%
max_day_opportunistic_buy_price = 5.0  # Max price to pay to opportunistically grid-charge batteries in daytime

# Forecast Adjustments
# Minimum house power usage to accept in the forecast (in Wh) in the event reported house_power is missing
min_house_power = [
    1500.0,  # 12:00 AM - 1:00 AM
    1500.0,  # 1:00 AM - 2:00 AM
    1500.0,  # 2:00 AM - 3:00 AM
    1500.0,  # 3:00 AM - 4:00 AM
    1500.0,  # 4:00 AM - 5:00 AM
    2000.0,  # 5:00 AM - 6:00 AM
    2000.0,  # 6:00 AM - 7:00 AM
    2500.0,  # 7:00 AM - 8:00 AM
    3000.0,  # 8:00 AM - 9:00 AM
    3500.0,  # 9:00 AM - 10:00 AM
    4000.0,  # 10:00 AM - 11:00 AM
    4500.0,  # 11:00 AM - 12:00 PM
    5000.0,  # 12:00 PM - 1:00 PM
    5500.0,  # 1:00 PM - 2:00 PM
    5000.0,  # 2:00 PM - 3:00 PM
    4500.0,  # 3:00 PM - 4:00 PM
    4000.0,  # 4:00 PM - 5:00 PM
    3500.0,  # 5:00 PM - 6:00 PM
    3000.0,  # 6:00 PM - 7:00 PM
    2500.0,  # 7:00 PM - 8:00 PM
    2000.0,  # 8:00 PM - 9:00 PM
    1500.0,  # 9:00 PM - 10:00 PM
    1500.0,  # 10:00 PM - 11:00 PM
    1500.0   # 11:00 PM - 12:00 AM
]
# Compounding discount to buy and sell forecast. For each additional future period, buy price increases by x% / sell decreases by x%.
uncertainty_discount = 0.10  # 0.05 is 5% per hour. Larger values are more conservative.

future_forecast_hours = 8.0  # Future forecast hours to consider. Forecasts beyond the battery's capacity are less useful.

desired_daytime_battery_soc = 50.0  # noqa Desired daytime battery SOC

# Facility, Inverter and Battery specifications
facility_name = "65 Qld"
num_inverters = 2  # Number of inverters at this facility
solar_active_hours = 2.0  # How long after sunrise and before sunset until the solar array is active (in hours)
battery_capacity_kWh = battery_capacity / 1000  # noqa
max_charge_rate_kW = 10.0  # noqa
full_charge_target = 1.0  # noqa 1.0 is 100% SOC
full_charge_discount = 0.8  # When charging to full SOC, discount the charge rate by this amount to allow more time.
full_battery = 99.0  # Define Full Battery %
timezone = 0.0  # noqa Local timezone +/- UTC
peak_time = 16  # When does peak start? (Typically 4:00pm)
peak_time_end = 20  # When does peak end (Typically 9:00pm) Select 20 for 8:59:59

# End user-entered data

def update_reason(facility_name, buy_price, sell_price, lowest_buy_price, highest_sell_price,
                  hours_until_lowest_buy, hours_until_highest_sell, house_load,
                  sunrise_plus_active, sunset_minus_active, base_reason, required_min_soc,
                  code, hours_until_sunrise_plus_active, hours_until_sunset_minus_active, local_time, **kwargs):
    """
    Returns:
    - str: The updated reason message, trimmed to 256 characters if necessary.
    """
    additional_info = ", ".join([f"{key}={value}" for key, value in kwargs.items()])
    reason = (f"{facility_name}: {base_reason}. Buy: {buy_price:.1f}c, Sell: {sell_price:.1f}c, Low Buy: {lowest_buy_price:.1f}c ({hours_until_lowest_buy}h), "  # noqa
              f"High Sell: {highest_sell_price:.1f}c ({hours_until_highest_sell}h), Load: {house_load:,.0f}W, Req Min SOC: {required_min_soc:.1f}, "
              f"Code: {code} Hr to SRise: {hours_until_sunrise_plus_active:.1f}h, Hr to SSet: {hours_until_sunset_minus_active:.1f}h. {local_time} "
              f"{additional_info}")

    # Trim the reason to ensure it does not exceed 256 characters
    return reason[:256]

# Initialize the code tracking variable
code = ''

# Determine Local Time
local_time = interval_time  # + timedelta(hours=timezone)

current_hour = local_time.hour

# Calculate the energy required to reach full charge (in kWh)
remaining_energy_kWh = (100 - battery_soc) / 100 * battery_capacity_kWh

# Calculate the time required to charge the battery to full (in hours)
time_to_full_charge = remaining_energy_kWh / (max_charge_rate_kW * full_charge_discount)

# Determine the time to start charging to be full by peak time
start_charging_time = int(peak_time - time_to_full_charge) - 1

# Margin between min / max buy & sell prices
price_margin = min_sell_price - max_buy_price # noqa

# Adjusted sunrise and sunset times with solar active hours
sunrise_plus_active = sunrise + timedelta(hours=solar_active_hours)
sunset_minus_active = sunset - timedelta(hours=solar_active_hours)

# Calculate hours until sunrise plus active
hours_until_sunrise_plus_active = ((sunrise_plus_active - local_time).total_seconds() / 3600.0)
if hours_until_sunrise_plus_active > 24:
    hours_until_sunrise_plus_active -= 24

# Calculate hours until sunset minus active
if local_time <= sunset_minus_active:
    hours_until_sunset_minus_active = (sunset_minus_active - local_time).total_seconds() / 3600.0
else:
    # If already past sunset_minus_active, calculate for the next day's sunset_minus_active
    next_sunset_minus_active = sunset_minus_active + timedelta(days=1)
    hours_until_sunset_minus_active = (next_sunset_minus_active - local_time).total_seconds() / 3600.0

# Hack: Determine if it's daytime based PV generation and time before peak.
daytime = (solar_power > 0) and (local_time.hour < peak_time)

# Adjust the reserve factor to decrease until solar_active_hours after sunrise (Code=B)
if 0 <= hours_until_sunrise_plus_active <= solar_active_hours:
    reserve_factor = max(0, 1 - hours_until_sunrise_plus_active / solar_active_hours)
    code += f'Reserve: {reserve_factor:.2f}, '
else:
    reserve_factor = 1
    code += f'Reserve: {reserve_factor:.2f}, '

# Check if buy_forecast is empty
if not buy_forecast:
    hours_until_lowest_buy = 99
else:
    # Identify the index of the lowest buy price in the forecast (How many hours in the future)
    index_lowest_buy = buy_forecast.index(min(buy_forecast))

    # Calculate the time until the lowest buy price
    hours_until_lowest_buy = index_lowest_buy

# Ensure house power is at least min_house_power for the current hour divided by the number of inverters
current_hour = local_time.hour
effective_house_power = max(house_power / num_inverters, min_house_power[current_hour] / num_inverters)

# Estimate power consumption until the lowest buy price period
estimated_consumption_kW = effective_house_power * hours_until_lowest_buy

# Calculate the required minimum SOC to ensure the battery lasts until the lowest buy price period
required_min_soc = reserve_factor * (estimated_consumption_kW / battery_capacity) * 100  # Convert to percentage

# Initialize the forecasts with default values
discounted_buy_forecast = []
discounted_sell_forecast = []

try:
    # Check if buy_forecast and sell_forecast are valid
    if not buy_forecast or not isinstance(buy_forecast, list) or any(v <= 0 for v in buy_forecast):
        raise ValueError("Invalid buy_forecast")
    if not sell_forecast or not isinstance(sell_forecast, list) or any(v <= 0 for v in sell_forecast):
        raise ValueError("Invalid sell_forecast")

    # Apply the discount to forecasted buy prices up to future_forecast_hours
    for i in range(int(future_forecast_hours)):
        if i < len(buy_forecast):
            discounted_buy_forecast.append(buy_forecast[i] * ((1 + uncertainty_discount) ** i))

    # Apply the discount to forecasted sell prices up to future_forecast_hours
    for i in range(int(future_forecast_hours)):
        if i < len(sell_forecast):
            discounted_sell_forecast.append(sell_forecast[i] * ((1 - uncertainty_discount) ** i))
except ValueError as e:  # noqa
    # If an error occurs, assign default values
    discounted_buy_forecast = [100000] * int(future_forecast_hours)
    discounted_sell_forecast = [1] * int(future_forecast_hours)
# Calculate the index of the cutoff period for future forecasts based on sunrise and solar active hours
cutoff_index = min(len(discounted_buy_forecast), int(solar_active_hours)) # noqa

#
# Begin decision evaluations
#

#
# Set default behavior for day & night if no other conditions applies (Code = C)
#

if daytime:
    action = 'auto'
    solar = 'export'
    code += 'Day, '
    reason = update_reason(
        facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
        discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
        effective_house_power, sunrise_plus_active, sunset_minus_active, 'Daytime Default: No other rule applies',
        required_min_soc, code, hours_until_sunrise_plus_active, hours_until_sunset_minus_active, local_time
    )

else:
    action = 'auto'
    solar = 'export'
    code += 'Night, '
    reason = update_reason(
        facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
        discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
        effective_house_power, sunrise_plus_active, sunset_minus_active, 'Night Default: No other rule applies',
        required_min_soc, code, hours_until_sunrise_plus_active, hours_until_sunset_minus_active, local_time,
    )

# Ensure the battery is fully charged for the evening peak event (Code = D)
if battery_soc < full_battery and (
    start_charging_time <= current_hour < peak_time or buy_price <= max_day_opportunistic_buy_price
):
    action = 'import'
    solar = 'export'
    code += 'Chg for Peak or Opportunistic Buy, '
    reason = update_reason(
        facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
        discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
        effective_house_power, sunrise_plus_active, sunset_minus_active,
        'IMPORT to reach full battery by 4 PM or Opportunistic Buy',
        required_min_soc, code, hours_until_sunrise_plus_active, hours_until_sunset_minus_active, interval_time
    )
# Always sell if sell price is greater than always sell price.
elif sell_price >= always_sell_price and battery_soc > min_sell_soc:
    action = 'export'
    solar = 'export'
    code += 'Always Sell, '
    reason = update_reason(
        facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
        discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
        effective_house_power, sunrise_plus_active, sunset_minus_active,
        'Sell price exceeds the always sell price',
        required_min_soc, code, hours_until_sunrise_plus_active, hours_until_sunset_minus_active, local_time
    )

# Evaluate for negative feed-in tariff scenarios and end script if any test positive.
elif buy_price <= 0.0 and battery_soc < full_battery:
    action = 'import'
    solar = 'curtail'
    code += 'Neg FiT Import, '
    reason = update_reason(
        facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
        discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
        effective_house_power, sunrise_plus_active, sunset_minus_active,
        'Negative FiT: If buy price is <= 0, IMPORT electricity and CURTAIL solar', required_min_soc, code, hours_until_sunrise_plus_active,
        hours_until_sunset_minus_active, local_time
    )

# If EXPORT is more expensive than buy, action CHARGE and CURTAIL solar.
elif sell_price < 0.0 and buy_price < abs(sell_price) and battery_soc > full_battery:
    action = 'auto'
    solar = 'curtail'
    code += 'Neg FiT Auto, '
    reason = update_reason(
        facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
        discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
        effective_house_power, sunrise_plus_active, sunset_minus_active,
        'Negative FiT: If EXPORT is more expensive than buy, action CHARGE and CURTAIL solar', required_min_soc, code,
        hours_until_sunrise_plus_active, hours_until_sunset_minus_active, local_time
    )

# If sell price < 0, action CHARGE and CURTAIL solar.
elif sell_price < 0.0 and battery_soc > full_battery:
    action = 'auto'
    solar = 'curtail'
    code += 'Neg FiT Neg Sell, '
    reason = update_reason(
        facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
        discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
        effective_house_power, sunrise_plus_active, sunset_minus_active,
        'Negative FiT: If sell price < 0, action CHARGE and CURTAIL solar', required_min_soc, code, hours_until_sunrise_plus_active,
        hours_until_sunset_minus_active, local_time
    )

# Use solar power to meet house demand and charge batteries when available
elif daytime:
    if sell_price >= min_day_sell_price and battery_soc >= required_min_soc:  # Export at lower price if battery is >= desired
        action = 'export'
        solar = 'export'
        code += 'Daytime and hi SoC, '
        reason = update_reason(
            facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
            discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
            effective_house_power, sunrise_plus_active, sunset_minus_active,
            'PV > 0 and high SoC: EXPORT excess',
            required_min_soc, code, hours_until_sunrise_plus_active, hours_until_sunset_minus_active, local_time
        )
    else:
        action = 'auto'
        solar = 'export'
        code += 'PV > 0 and lo SoC, '
        reason = update_reason(
            facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
            discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
            effective_house_power, sunrise_plus_active, sunset_minus_active,
            'PV > 0 and low SoC or low Sell Price',
            required_min_soc, code, hours_until_sunrise_plus_active, hours_until_sunset_minus_active, local_time
        )

# Evaluate forecast-based buy/sell decisions based on Powston 8-hour buy/sell forecasts (Code = E)
else:
    # Check if the maximum forecasted sell price is in the current period and discharge only if battery SOC is above required_min_soc
    if (
        buy_price < max_buy_price and
        battery_soc > required_min_soc and
        sell_price >= max(discounted_sell_forecast) and
        sell_price >= min_sell_price
    ):
        action = 'export'
        solar = 'export'
        code += 'Sell Now, '
        reason = update_reason(
            facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
            discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
            effective_house_power, sunrise_plus_active, sunset_minus_active,
            'Fcst: Max sell price now; EXPORT if SOC > required', required_min_soc, code, hours_until_sunrise_plus_active,
            hours_until_sunset_minus_active, local_time
        )

    # If could have sold, but battery SoC is too low, say so:
    elif sell_price >= max(discounted_sell_forecast) and sell_price >= min_sell_price:
        code += 'Could Sell; lo SoC, '
        reason = update_reason(
            facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
            discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
            effective_house_power, sunrise_plus_active, sunset_minus_active,
            'Fcst: Max sell price now; SoC < required', required_min_soc, code, hours_until_sunrise_plus_active,
            hours_until_sunset_minus_active, local_time
        )

    # If the buy price for the current period is the lowest in the forecast and the battery SOC is less than the min SOC, charge only at night
    elif not daytime and buy_price == min(discounted_buy_forecast) and battery_soc < required_min_soc and not (peak_time <= current_hour < peak_time_end):
        action = 'import'
        solar = 'export'
        code += 'Buy Now, min SoC, '
        reason = update_reason(
            facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
            discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
            effective_house_power, sunrise_plus_active, sunset_minus_active,
            'Fcst: Low buy price now; IMPORT if SOC < required', required_min_soc, code, hours_until_sunrise_plus_active,
            hours_until_sunset_minus_active, local_time
        )

    else:
        # Check if there's any future buy price lower than any future sell price within the forecast
        buy_sell_opportunity_exists = False
        for i in range(len(discounted_buy_forecast)):
            for j in range(i + 1, len(discounted_sell_forecast)):
                if discounted_buy_forecast[i] < discounted_sell_forecast[j]:
                    buy_sell_opportunity_exists = True
                    break
            if buy_sell_opportunity_exists:
                break

        if buy_sell_opportunity_exists and not (peak_time <= current_hour < peak_time_end):
            action = 'import'
            solar = 'export'
            code += 'Buy Low, Sell High, '
            reason = update_reason(
                facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
                discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
                effective_house_power, sunrise_plus_active, sunset_minus_active,
                f'Fcst: {sell_price} Buy low, sell high opportunity exists', required_min_soc, code, hours_until_sunrise_plus_active,
                hours_until_sunset_minus_active, local_time
            )
        else:
            # Buy if price low and battery soc low.
            if battery_soc < min_sell_soc and local_time < sunrise and buy_price < max_am_buy_price:
                action = 'import'
                solar = 'export'
                code += 'Buy Low Battery, '
                reason = update_reason(
                    facility_name, buy_price, sell_price, min(discounted_buy_forecast), max(discounted_sell_forecast),
                    discounted_buy_forecast.index(min(discounted_buy_forecast)), discounted_sell_forecast.index(max(discounted_sell_forecast)),
                    effective_house_power, sunrise_plus_active, sunset_minus_active,
                    'Fcst: Buy Low Battery', required_min_soc, code, hours_until_sunrise_plus_active,
                    hours_until_sunset_minus_active, local_time
                )

if 14 < interval_time.hour < 16 and battery_soc < 60 and action != 'import' and buy_price < 30:
    action = 'import'
    reason += ' panic buy SOC < 50'

# Declare no exports when negative
if rrp < 0:
    feed_in_power_limitation = 0
    reason += f' setting feed in to {feed_in_power_limitation}'
