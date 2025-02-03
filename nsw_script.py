hour = interval_time.hour
desired_soc = 20.0
sell_price_threshold = 85  # 20 cents
sell_price_threshold_1 = 20  # sell in morning
sell_price_threshold_2 = 1000  # Sell during peak
buy_price_morning = 20  # Morning buy price threshold

if 0 <= hour < 6:
    if sell_price > sell_price_threshold:
        action = 'export'
        reason = 'nsw: sell price greater than 20 cents between midnight and 6am'
    elif buy_price < 5 and battery_soc >= desired_soc:
        action = 'import'
        reason = 'nsw: buy price less than 5 cents between midnight and 6am'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between midnight and 6am'

# FROM 6 AM to 1 PM
if 6 <= hour < 13:
    if sell_price > sell_price_threshold_1:
        action = 'export'
        reason = 'nsw: sell price greater than 20 cents between 6am and 1pm'
    # CHANGED to require battery_soc < 25 and buy_price < 20
    elif buy_price < buy_price_morning and battery_soc < 25:
        action = 'import'
        reason = 'nsw: buy price less than 20 cents and battery SOC below 25% between 6am and 1pm'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between 6am and 1pm'

# FROM 1 PM to 3 PM
if 13 <= hour < 15:
    if sell_price > sell_price_threshold_2:
        action = 'export'
        reason = 'nsw: sell price greater than 20 cents between 1pm and 3pm'
    # CHANGED battery_soc < 60 to < 25
    elif battery_soc < 25 and buy_price < 20:
        action = 'import'
        reason = 'nsw: buy price less than 20 cents and battery SOC below 25% between 1pm and 3pm'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between 1pm and 3pm'

if rrp < 0:
    feed_in_power_limitation = 0
    reason += f' setting feed in to {feed_in_power_limitation}'
elif 15 <= hour < 21:
    if sell_price > sell_price_threshold and battery_soc >= desired_soc:
        action = 'export'
        reason = 'nsw: sell price greater than 20 cents during peak hours'
    else:
        action = 'auto'
        reason = 'nsw: hour between 3pm and 9pm or battery SOC below 20%'

if 21 <= hour < 24:
    if sell_price > sell_price_threshold:
        action = 'export'
        reason = 'nsw: sell price greater than 20 cents between 9pm and midnight'
    elif buy_price < 10 and battery_soc < 30:
        action = 'import'
        reason = 'nsw: buy price less than 5 cents between 9pm and midnight'
    else:
        action = 'auto'
        reason = 'nsw: default to auto mode between 9pm and midnight'

if (hour > 15 or hour < 4) and battery_soc > 80 and sell_price > 25:
    action = 'export'
    reason = 'nsw: use it or lose it'

if (hour < 4) and battery_soc > 20 and sell_price > 20:
    action = 'export'
    reason = 'nsw: use it or lose it'

if (3 < hour < 6) and battery_soc > 10 and sell_price > 15:
    action = 'export'
    reason = 'nsw: use it or lose it'

if rrp > 800 and battery_soc > 30:
    action = 'export'
    reason += 'take the money'
