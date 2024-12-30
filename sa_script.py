daytime = sunrise > interval_time and interval_time < sunset
action = 'auto'
reason = f'SA: user default {interval_time}'

in_sapn_peak = interval_time.hour in [0, 6, 7, 8, 9] or interval_time.hour >= 15
if 'import' in action and in_sapn_peak and buy_price > 12:
    action = 'auto'
    reason += ' sapn peak override to auto not import'

if sell_price > 25:
    action = 'export'
    reason = 'SA: bigger battery so export'
elif battery_soc > 50 and sell_price > 20:
    action = 'export'
    reason = 'SA: export over wholesale replacement cost'

lowest_six_buy_price = sorted(buy_forecast)[:6]
approx_battery_charge_cost = sum(lowest_six_buy_price) / 6
soc_prod = pow(1.5, 1 - (battery_soc / 100))

if (interval_time.hour > 16) or (interval_time.hour < 7):
    if action == 'export' and sell_price < (soc_prod * approx_battery_charge_cost):
        action = 'discharge'  # Changed from 'auto' to 'discharge'
        reason = f'SA: Using stored energy: sell price ({sell_price}) < soc_prod * charge_cost ({soc_prod * approx_battery_charge_cost})'
    elif action == 'import' and battery_soc > 30:
        action = 'auto'
        reason = f'SA: battery soc is {battery_soc} sell price greater than soc pow(5, {battery_soc}/100) factor {approx_battery_charge_cost}'
    else:
        reason += f' sell price greater than soc pow(5, {battery_soc}/100) factor {approx_battery_charge_cost}'

if (interval_time.hour > 20) and battery_soc > 80 and sell_price > 18:
    action = 'export'
    reason = 'SA: recover daily fees'

if (interval_time.hour < 5) and (battery_soc < 20) and (action == 'export') and (sell_price < 100):
    action = 'auto'
    reason = 'keep battery at 10% unless price over 100c'

if daytime and 'stopped' in action and sell_price < 0:
    action = 'charge'
    reason = 'SA: curtail not stopped in negative prices'

if 'export' == action and (sell_price < 18 or rrp < 180):
    action = 'auto'
    reason = f"SA: sanity check: don't sell under 20c [lv:{sell_price} v nem:{rrp}]"

# if in_sapn_peak is False and daytime and sell_price < 0 and battery_soc > 95:
#    action = 'limit'
#    active_power_ratio = 10
#    reason = f'battery full enough and need to wind down active power to {active_power_ratio}'

# if daytime and 'charge' in action and (buy_price < 0 and rrp < -80) and battery_soc > 95:
#    action = 'fullstop'
#    reason = 'test full stop'

if rrp > 0:
    feed_in_power_limitation = 25000
    reason += f' rrp > 0 so feed_in_power_limitation {feed_in_power_limitation}'

if grid_power < 0 and buy_price > 5 and battery_soc > 50 and 'charge' in action:
    action = 'auto'
    reason = 'SA: should not charge if using power'

if solar == 'curtail' and battery_soc < 95:
    feed_in_power_limitation = 1000
    reason += f' aim higher to increase solar {solar}'

if interval_time.hour < 21 and battery_soc > 80:
    if action == 'auto' and rrp > 300:
        action = 'export'
        reason += ' test export over 300rrp'

if 'charge' in action:
    action = 'auto'
    reason += ' no (dis)charge as a test'

if 'auto' in action and (buy_price < 0 and rrp < -100) and battery_soc > 95:
    action = 'fullstop'
    reason = 'SA: test full stop'

if 'export' == action and battery_soc < 60 and interval_time.hour < 18:
    if (sell_price < 50 or rrp < 500) and max(sell_forecast) > 100:
        action = 'auto'
        reason += ' save it for later'

# waiting for to confirm this rule change
if buy_price < 0 and battery_soc < 70 and interval_time.hour < 9:
    action = 'import'
    reason += ' import at negative buy and low SOC'
