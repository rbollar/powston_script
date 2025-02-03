hour = interval_time.hour
desired_soc = 20.0
sell_price_threshold = 85  # 20 cents
sell_price_threshold_1 = 20  # sell in morning
sell_price_threshold_2 = 1000  # Sell during peak
buy_price_morning = 2  # Morning buy price
# Low battery SOC is 10% and low sell price is 15 cents
low_battery_soc = 10
morning_low_sell_price = 15
# Morning battery SOC is 20% and morning sell price is 20 cents
morning_battery_soc = 20
morning_sell_price = 20
# High battery SOC is 80% and high sell price is 25 cents
high_battery_soc = 80
high_min_sell_price = 25

if 0 <= hour < 6:
    if sell_price > sell_price_threshold:
        action = 'export'
        reason = 'vic: sell price greater than 20 cents between midnight and 6am'
    elif buy_price < 5 and battery_soc >= desired_soc:
        action = 'import'
        reason = 'vic: buy price less than 5 cents between midnight and 6am'
    else:
        action = 'auto'
        reason = 'vic: default to auto mode between midnight and 6am'
# Stop charging/discharging between 6 AM and 1 PM
if 6 <= hour < 13:
    if sell_price > sell_price_threshold_1:
        action = 'export'
        reason = 'vic: sell price greater than 20 cents between 6am and 1pm'
    elif buy_price < buy_price_morning:
        action = 'import'
        reason = 'vic: buy price less than 5 cents between 6am and 1pm'
    else:
        action = 'auto'
        reason = 'vic: default to auto mode between 6am and 1pm'
# Stop charging/discharging between 6 AM and 1 PM
if 13 <= hour < 15:
    if sell_price > sell_price_threshold_2:
        action = 'export'
        reason = 'vic: sell price greater than 20 cents between 6am and 1pm'
    elif buy_price < 20 and battery_soc < 100:
        action = 'import'
        reason = 'vic: buy price less than 25 cents between 1pm and 3pm'
    else:
        action = 'auto'
        reason = 'vic: default to auto mode between 6am and 1pm'
# Ensure 'auto' action during peak demand times from 3 PM to 9 PM, unless sell_price > 20 cents
elif 15 <= hour < 21:
    if sell_price > sell_price_threshold and battery_soc >= desired_soc:
        action = 'export'
        reason = 'vic: sell price greater than 20 cents during peak hours'
    else:
        action = 'auto'
        reason = 'vic: hour between 3pm and 9pm or battery SOC below 20%'
# Manage battery between 9 PM and midnight
if 21 <= hour < 24:
    if sell_price > sell_price_threshold:
        action = 'export'
        reason = 'vic: sell price greater than 20 cents between 9pm and midnight'
    elif buy_price < 10 and battery_soc < 100:
        action = 'import'
        reason = 'vic: buy price less than 5 cents between 9pm and midnight'
    else:
        action = 'auto'
        reason = 'vic: default to auto mode between 9pm and midnight'

if (hour > 15 or hour < 4) and battery_soc > high_battery_soc and sell_price > high_min_sell_price:
    action = 'export'
    reason = f'vic: use it or lose it down to {high_battery_soc}%'

if (hour < 4) and battery_soc > morning_battery_soc and sell_price > morning_sell_price:
    action = 'export'
    reason = f'vic: morning use it or lose it down to {morning_battery_soc}%'

if (3 < hour < 6) and battery_soc > low_battery_soc and sell_price > morning_low_sell_price:
    action = 'export'
    reason = f'vic: morning use it or lose it down to {low_battery_soc}%'

if rrp > 800 and battery_soc > 30:
    action = 'export'
    reason += 'take the money'

if (interval_time.hour > 15) and battery_soc > 50 and sell_price > 20:
    best_upcoming = max(sell_forecast)
    if best_upcoming < (sell_price + 10):
        action = 'export'
        reason = f'vic: {best_upcoming} < sell within 10c of max'
    else:
        reason += f' best upcoming: {best_upcoming}c'

if (interval_time.hour > 15) and battery_soc > 80 and sell_price > 10:
    best_upcoming = max(sell_forecast)
    if best_upcoming < (sell_price + 5):
        action = 'export'
        reason = f'vic: {best_upcoming} < sell within 5c of max'
    else:
        reason += f' best upcoming: {best_upcoming}c'
