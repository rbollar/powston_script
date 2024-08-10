# powston_script
Decision script for Powston Inverter Intelligence @ https://powston.com.au

# Installation

Adjust user variables (https://github.com/rbollar/powston_script/wiki/User-Variables) and upload through the Powston App.

# Change Log

Initial commit.

# Change Log before initial GitHub Commit
- 0.32.1 Bump Buy / Sell prices.
- 0.32 Evaluate future buy price lower than current sell price.
- 0.31.2 Adjust reserve factor
- 0.31.1 Correct minimum day sell price.
- 0.31.0 Add an always sell parameter
- 0.30.8 More timezone experiments
- 0.29 Add reserve factor to morning PV
- 0.28.8 Fix Sunrise / Sunset?
- 0.27.1 Tweak logging
- 0.27 Note good time to sell, but low SoC
- 0.26.5 Shorter descriptions; verbose codes
- 0.26.3 Time Zone tweaks.
- 0.26 Tweak time to charge calculations.
- 0.25.7 Add hours until sunset minus active variable.
- 0.25.4 Add hours until sunrise plus active variable.
- 0.25.3 Correct Peak Time calcuation.
- 0.25.2 Fix energy use estimate
- 0.25.1 Change sell price forecast logic
- 0.25 Add logic code
- 0.24.2 Fill battery regardless of price when approaching peak time.
- 0.23 Try to add required_min_soc
- 0.22 Limit forecasts to user-determined future_forecast_hours
- 0.21.3 Update descriptions
- 0.17 Bring reason variables back in -- diagnose uncertainty_discount by removing it.
- 0.16 Revert the reason variables
- 0.15.2 Remove the pesky print() statement
- 0.15.1 Tweaking location code
- 0.15 Add variables to reason description.
- 0.14 Regress 0.13 changes and update to use interval_time for simulation and astra as builtin.
- 0.13 Add the reason variable to all decisions. Remove astral import and fake sunrise / sunset.
- 0.12 Convert daytime 'charge' actions to 'auto' (didn't do what I expected and removed)
- 0.11.4 Try setting battery_charge_cost and min_auto_price to 0 (didn't work)
- 0.11.3 Add a second attempt at override.
- 0.11.2 Override 'auto' and 'stopped' with 'discharge'.
- 0.11.1 Try 'discharge' instead of 'export'.
- 0.11 Try to override the over ride. At the end of the script, change 'auto' to 'export'.
- 0.10 Define daytime as sunrise / sunset excluding the solar_active_hours
- 0.9.2 Let's be a little smarter with the default. 'charge' in daytime, 'discharge' at other times.
- 0.9.1 Chage default action to 'charge' instead of 'auto'
- 0.9 Remove action 'auto' in attempt to override default 'stopped' state.
- 0.8 Correct Solar action typo.
- 0.7 Adjust overnight forecasts to only include period where array is not live.
- 0.6.1 Allow a lower daytime sell price
- 0.6 Change forecast evaulation order / remove evening demand charge code
- 0.5 Divide house power by number of inverters / Expressly define using solar while array is live
- 0.4 Code cleanup / remove exit(0) code and replace with elif tests
- 0.3 Tweak overnight forecasts to account for upcoming daytime; add discount rate for future hour forecasts
- 0.2 Initial buy / sell forecast
- 0.1 Initial version
