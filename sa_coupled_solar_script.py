other_house_power = 0
other_battery_power = 0
other_house_power = 0
if inverters and 'inverter_params_71876' in inverters:
    other_solar_power = inverters['inverter_params_71876']['solar_power']
    other_battery_power = inverters['inverter_params_71876']['battery_power']
    other_house_power = inverters['inverter_params_71876']['house_power']
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