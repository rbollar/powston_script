hour = interval_time.hour
desired_soc = 20.0
min_sell_soc = 30  # 'Take the money (sell > 80c)' down to this SOC
sell_price_threshold = 85  # 20 cents
sell_price_threshold_1 = 20  # sell in morning
sell_price_threshold_2 = 1000  # Sell during peak
buy_price_morning = 5  # Morning buy price
# This is when we expect the solar production to meet our house load
minutes_after_sunrise_solar_matches_load = 30
solar_production_time = sunrise + timedelta(minutes=minutes_after_sunrise_solar_matches_load)

if 0 <= hour < 6:
    if sell_price > sell_price_threshold:
        action = 'export'
        reason = f'nsw: sell price greater than {sell_price_threshold} cents between midnight and 6am'
    elif buy_price < buy_price_morning and battery_soc >= desired_soc:
        action = 'import'
        reason = f'nsw: buy price less than {buy_price_morning} cents between midnight and 6am'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between midnight and 6am'
# Stop charging/discharging between 6 AM and 1 PM
if 6 <= hour < 13:
    if sell_price > sell_price_threshold_1:
        action = 'export'
        reason = f'nsw: sell price greater than {sell_price_threshold_1} cents between 6am and 1pm'
    elif battery_soc > 50 and buy_price > 0:
        action = 'auto'
        reason = 'nsw: buy price is over 0 wait for afternoon to buy'
    elif buy_price < buy_price_morning:
        action = 'import'
        reason = f'nsw: buy price less than {buy_price_morning} cents between 6am and 1pm'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between 6am and 1pm'
# Stop charging/discharging between 6 AM and 1 PM
if 13 <= hour < 15:
    if sell_price > sell_price_threshold_2:
        action = 'export'
        reason = f'nsw: sell price greater than {sell_price_threshold_2} cents between 6am and 1pm'
    elif battery_soc < 60 and buy_price < sell_price_threshold_2:
        action = 'import'
        reason = f'nsw: buy price less than {sell_price_threshold_2} cents between 1pm and 3pm'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between 6am and 1pm'
if rrp < 0:
    feed_in_limitation = 0
    reason += f' setting feed in to {feed_in_limitation}'
# Ensure 'auto' action during peak demand times from 3 PM to 9 PM, unless sell_price > 20 cents
elif 15 <= hour < 21:
    if sell_price > sell_price_threshold and battery_soc >= desired_soc:
        action = 'export'
        reason = f'nsw: sell price greater than {sell_price_threshold} cents during peak hours'
    else:
        action = 'auto'
        reason = f'nsw: hour between 3pm and 9pm or battery SOC below {desired_soc}%'
# Manage battery between 9 PM and midnight
if 21 <= hour < 24:
    if sell_price > sell_price_threshold:
        action = 'export'
        reason = f'nsw: sell price greater than {sell_price_threshold} cents between 9pm and midnight'
    elif buy_price < 10 and battery_soc < 30:
        action = 'import'
        reason = 'nsw: buy price less than 10 cents between 9pm and midnight'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between 9pm and midnight'

if (interval_time.hour > 15) and battery_soc > 80 and sell_price > 10:
    best_upcoming = max(sell_forecast)
    if best_upcoming < (sell_price + 5):
        action = 'export'
        reason = f'nsw: {best_upcoming} < sell within 5c of max'
    else:
        reason += f' best upcoming: {best_upcoming}c'

if (hour < 5) and battery_soc > desired_soc and sell_price > 20:
    action = 'export'
    reason = f'nsw: pre 5am use it or lose it down to {desired_soc}%'

if 4 < hour and interval_time < solar_production_time and battery_soc > 10 and sell_price > 15:
    action = 'export'
    reason = f'nsw: before solar production time use it or lose it {solar_production_time}'

if rrp > 800 and battery_soc > min_sell_soc:
    action = 'export'
    reason += f'take the money down to {min_sell_soc}%'