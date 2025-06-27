min_soc = 5  # % Minimum battery SOC
action = 'auto'
# Pricing Decisions
IMPORT_TOLERANCE = 1
BATTERY_SOC_NEEDED = 9
BUY_DELTA_THRESHOLD = 87
CUT_OFF_THRESHOLD = 47
MORNING_SELL_MARGIN = 82
MORNING_SELL_SOC = 42
BATTERY_EXPORT_SOC_THRESHOLD = 24
GOOD_SUN_DAY = 44
GOOD_SUN_HOUR = 64
BAD_SUN_DAY_KEEP_SOC = 16
ALWAYS_IMPORT_SOC = 22  # The battery SOC at which we always import

# Determine Local Time
hour = interval_time.hour
current_hour = interval_time.hour
gti = weather_data.get('hourly', {}).get('global_tilted_irradiance_instant', [-1] * 48)
tomorrow_morning_hours_away = 24 - hour
global_tilted_irradiance_tomorrow = sum(gti[tomorrow_morning_hours_away:])
soc_diff = 0.0
time_left = 0.0
soc_diff_remaining = 0.0
night_reserve = BATTERY_SOC_NEEDED
if global_tilted_irradiance_tomorrow < (GOOD_SUN_DAY * 100):
    night_reserve += BAD_SUN_DAY_KEEP_SOC
if forecast and hour > 16:
    morning_peak = max(forecast[:-6])
    if morning_peak > 400:
        night_reserve += 10
elif forecast and hour < 6:
    morning_away = hour * 2
    morning_peak = max(forecast[morning_away:])
    if morning_peak > 400:
        night_reserve += 10

def find_first_index(gti, threshold):
    for i in range(len(gti)):
        if gti[i] > threshold:
            return i
    return -1

def find_last_index(gti, threshold):
    for i in range(len(gti)):
        if gti[i] < threshold:
            return i
    return -1

first_good_gti = find_first_index(gti, GOOD_SUN_HOUR * 10)
last_good_gti = find_last_index(gti[:24], GOOD_SUN_HOUR * 10)
solar_charge_time = (interval_time.hour >= first_good_gti) and (interval_time.hour <= last_good_gti)
daytime = sunrise.time() < interval_time.time() < sunset.time()
if daytime:
    soc_diff = battery_soc - night_reserve
    time_left = (((sunset - interval_time).total_seconds() - 1800) % 86400) / 3600
elif not daytime:
    night_hours = (((sunrise - sunset).total_seconds()) % 86400) / 3600
    time_left = (((sunrise - interval_time).total_seconds() + 1800) % 86400) / 3600
    soc_diff = (battery_soc - night_reserve)
    soc_diff_remaining = battery_soc - night_reserve * (time_left / night_hours)

action = 'auto'
if rrp > 990:
    action = 'export'
    reason = f'RRP {rrp} is high, exporting'
reason = f'Default to auto: {solar_charge_time} soc {night_reserve:.0f}%->{soc_diff:.1f}%, time left {time_left:.1f}h, battery soc {battery_soc:.1f}%'
global_tilted_irradiance_today = sum(gti)
if global_tilted_irradiance_today > (GOOD_SUN_DAY * 100):
    if interval_time.hour < 12:
        low_buy_price = min(buy_forecast)
        if rrp < 0:
            action = 'charge'
        elif action in ['auto', 'charge', 'import'] and sell_price > low_buy_price:
            action = 'discharge'
            reason += ' not charging too early'

    if interval_time.hour < 10:
        if battery_soc > MORNING_SELL_SOC:
            low_buy_price = min(buy_forecast)
            if sell_price > (low_buy_price + MORNING_SELL_MARGIN):
                action = 'export'
                reason += f' lots of SOC, good sun and better buys coming {low_buy_price}c'
            else:
                reason += f' low buy not enough {low_buy_price}c'
else:
    reason += f' low PV day {global_tilted_irradiance_today:.2f}W/m2'

if 14 < interval_time.hour < 16 and battery_soc < 60 and action != 'import' and buy_price < 30:
    if buy_forecast and buy_price > min(buy_forecast[:6]):
        reason += ' wait for lower buy soon'
    else:
        action = 'import'
        reason += ' panic buy SOC < 50'

global_tilted_irradiance_past = sum(gti[:interval_time.hour])
global_tilted_irradiance_to_2pm = sum(gti[:15])
reason += f" tomorrow PV {global_tilted_irradiance_tomorrow:.1f}W/m2"
if 4 < interval_time.hour < 16 and buy_forecast and battery_soc:
    charge_fors = max(1, int(6 * battery_soc / 100))
    low_buy_price = round(max(sorted(buy_forecast)[:charge_fors]), 2)
    precent_pv_past = round(global_tilted_irradiance_past / global_tilted_irradiance_to_2pm * 100, 2)
    reason += f' pv {precent_pv_past}% vs {battery_soc}%'
    tolerant_low_price = round(low_buy_price * ((100 + IMPORT_TOLERANCE) / 100), 2)
    if action in ['auto', 'charge'] and (battery_soc - ALWAYS_IMPORT_SOC) < precent_pv_past:
        if buy_forecast and buy_price > min(buy_forecast[:6]) and battery_soc > 85:
            reason += ' wait for lower buy soon'
        elif buy_price < tolerant_low_price:
            action = 'import'
            reason += f' buy price {buy_price} is lower than {tolerant_low_price}'
        else:
            if action == 'import':
                action = 'auto'
        reason += f' wait on {action} not import {tolerant_low_price}'
    if action == 'import' and current_hour < 10 and global_tilted_irradiance_to_2pm > 4000:
        action = 'auto'
        reason += f' wait for more sun before importing {global_tilted_irradiance_to_2pm} to go'
if action == 'export' and current_hour > 16 and battery_soc < min_soc:
    action = 'auto'
    reason += f' battery SOC < {min_soc}%'
# no point exporting unless this sell price is
# lower than the sorted forecasted sell prices
windows_can_export = int(battery_soc / (100 - BATTERY_EXPORT_SOC_THRESHOLD))
if sell_forecast and action == 'export':
    # Count sells above the current sell_price
    sorted_sell_forecast = sorted(sell_forecast)
    cut_off = sorted_sell_forecast[min(windows_can_export, len(sorted_sell_forecast) - 1)]
    max_buy_forecast = max(buy_forecast)
    if sell_price < (max_buy_forecast * BUY_DELTA_THRESHOLD / 100):
        action = 'auto'
        reason += f' sell price {sell_price} is higher than buy price {max_buy_forecast}'
    elif sell_price < (cut_off - CUT_OFF_THRESHOLD):
        action = 'auto'
        reason += f' sell price {sell_price} is lower than 3c within {cut_off}'
    else:
        reason += f' okay to export {windows_can_export}'

if action == 'export' and battery_soc > night_reserve and interval_time > sunset and buy_price < 98:
    action = 'auto'
    reason += ' in night reserve mode'
    if buy_price > 25:
        action = 'export'
        solar = 'curtail'
        feed_in_power_limitation = 1000
        reason += f' aim higher during high prices {feed_in_power_limitation}'

if sell_forecast and buy_forecast and soc_diff_remaining > 25:
    high_sell_price = max(sorted(sell_forecast)[:-3]) if sell_forecast else 0
    if high_sell_price < (sell_price + 5):
        action = 'export'
        reason += f' export: with 5c of high_sell_price {high_sell_price}c/kWh'
if sell_forecast and buy_forecast and soc_diff_remaining > 15:
    high_sell_price = max(sorted(sell_forecast)[:-3]) if sell_forecast else 0
    low_buy_price = min(buy_forecast) * 1.3
    if sell_price > low_buy_price:
        action = 'export'
        reason += f' export: sell price {sell_price} is higher than low buy price {low_buy_price}c/kWh'
if not daytime and time_left < 2 and soc_diff_remaining > 0:
    high_sell_price = max(sorted(sell_forecast)[:-3]) if sell_forecast else 0
    if sell_price > (high_sell_price - 5):
        action = 'export'
        reason += f' export: sell price {sell_price} is higher than high sell price {high_sell_price}c/kWh'

if sell_forecast and soc_diff < 5:
    # Now we only want to export if the RRP is high enough
    high_sell_price = max(sorted(sell_forecast)[:-3]) if sell_forecast else 0
    if sell_price < high_sell_price and action == 'export':
        action = 'auto'
        reason += f' waiting for {high_sell_price}c, battery SOC {battery_soc:.1f}%'

# Spike Hacking
if forecast and action == 'export':
    over_count = int(np.sum(np.array(forecast) > (rrp + 2000)))
    is_spike = (max(forecast) - rrp) > 1000
    if rrp > 1000:
        action = 'export'
        feed_in_power_limitation = 20000
        reason += f' exporting at ${rrp}/MWH, feed in power limitation {feed_in_power_limitation}W'
    elif is_spike and over_count > 1:
        action = 'auto'
        reason += f' not exporting, {over_count} prices over sell price {sell_price}c'
    else:
        reason += f' exporting at ${rrp}/MWH'
if battery_soc and battery_soc < 10 and action == 'export':
    action = 'auto'
    reason += ' battery SOC < 7%'
# Stop always exporting if battery SOC is low
always_export_rrp = 1000
if soc_diff < 10:
    always_export_rrp = None
elif battery_soc < (soc_diff + 20):
    always_export_rrp = 10000
    reason += f" increasing always_export_rrp: {always_export_rrp}"
if battery_soc < night_reserve:
    always_export_rrp = None
    reason += f" remove always_export_rrp under night reserve: {night_reserve:.1f}%"
