other_house_power = inverters.get(0, {}).get('house_power', 0)
other_battery_power = inverters.get(0, {}).get('battery_power', 0)
other_solar_power = inverters.get(0, {}).get('solar_power', 0)

other_grid_need = other_solar_power - other_house_power + other_battery_power
reason += f' no battery ({other_solar_power} - {other_house_power} + {other_battery_power})'
action = 'auto'

if rrp < 0 and other_grid_need < -5000:
    solar = 'maximize'
    reason += f" do not curtail {other_grid_need}"
elif rrp < 0 and other_grid_need < -solar_power:
    feed_in_power_limitation = -other_grid_need
    reason += f" curtail but feed in {feed_in_power_limitation}"
else:
    reason += f" curtail as {other_grid_need}"

if buy_price < 0 and rrp < 100:
    solar = 'curtail'
    reason += ' always curtail this negative'