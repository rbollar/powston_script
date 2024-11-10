import unittest
import os
import io
from inverter_simulator.simulator import InverterSimulator
from aemo_to_tariff import spot_to_tariff
import json
import requests
from datetime import datetime, timedelta
import pandas as pd
from astral import LocationInfo
from astral.sun import sun

class TestUserScript(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(TestUserScript, self).__init__(*args, **kwargs)
        self.API_KEY = os.getenv("POWSTON_API_KEY")
        API_KEY = os.getenv("POWSTON_API_KEY")
        if not self.API_KEY:
            self.fail("POWSTON_API_KEY environment variable is not set")
            return
    
        filename = "script.py"
        try:
            with open(filename, "r") as file:
                self.content = file.read()
        except FileNotFoundError:
            self.fail(f"R001 File {filename} not found")
            return
        self.powston_test_server = os.getenv("POWSTON_TEST_SERVER", 'https://dev.inverterintelligence.com')
        self.header = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        self.site_id = 1
        
        response = requests.get(f'{self.powston_test_server}/api/meter_data/{self.site_id}?from_date="2024-11-07"&to_date="2024-11-08"', headers=self.header).json()

        self.meter_data_df = pd.read_json(response, orient="records")
        self.meter_data_df.set_index('interval_time', inplace=True)
        
    def always_auto(self, inverval_time, **kwargs):
        return 'auto', 'always_auto'
    
    def test_sim_script(self):
        battery_capacity = 25000
        charge_rate = 10000
        max_ppv_power = 10000
        sim = InverterSimulator(self.meter_data_df, self.always_auto, battery_capacity=battery_capacity,
                                charge_rate=charge_rate, max_ppv_power=max_ppv_power)
        auto_bill, ret_df = sim.run_simulation()
        
        def run_user_code(interval_time, **kwargs):
            params = {'interval_time': interval_time,
                      'battery_capacity': battery_capacity,
                      'charge_rate': charge_rate,
                      'max_ppv_power': max_ppv_power,
                      'location': LocationInfo("Brisbane", "Australia", "Australia/Brisbane", -27.4698, 153.0251)}
            for key, val in kwargs.items():
                params[key] = val
            eval(compile(self.content, '<string>', 'exec'), globals(), params)
            return params['action'], params['reason']
        
        sim = InverterSimulator(self.meter_data_df, run_user_code, battery_capacity=battery_capacity,
                                spot_to_tariff=spot_to_tariff, tariff='6900', network='energex',
                                charge_rate=charge_rate, max_ppv_power=max_ppv_power)
        sim_bill, ret_df = sim.run_simulation()
        
        print('User bill', sim_bill, 'v auto only', auto_bill)

if __name__ == '__main__':
    unittest.main()
