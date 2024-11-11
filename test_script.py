import unittest
import os
import json
import requests

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
    
    def test_sim_script(self):
        powston_api_sim_code_endpoint = f'{self.powston_test_server}/api/sim_code'
        action_params = {}
        with open("./tests/action_params1.json", "r", encoding="UTF-8") as file:
            action_params = json.load(file)
        body = {
            "code": self.content,
            "action_params": action_params,
            'timezone': 'Australia/Brisbane',
            'latitude': -27.4698,
            'longitude': 153.0251,
            "inverter_action_id": 1,
        }
        
        sim_code_response = requests.post(powston_api_sim_code_endpoint, json=body, headers=self.header).json()
        
        self.assertEqual(sim_code_response['action'], 'import', "Expected charge action")
        self.assertIn('sell high opportunity exists', sim_code_response['reason'], "Expected sell high opportunity exists")

    def test_script(self):
        powston_api_test_code_endpoint = f'{self.powston_test_server}/api/check_code'
        
        body = {
            "code": self.content,
            "inverter_action_id": 1,
        }
        
        
        try:
            check_code_response = requests.post(powston_api_test_code_endpoint, json=body, headers=self.header)
            check_code_response.raise_for_status()
            
            response_json = check_code_response.json()
            self.assertEqual(check_code_response.status_code, 200, "Expected status code 200")
            self.assertIn('Success', response_json['problems'], "Expected 'Success' in problems")
            self.assertTrue(response_json['status'], "Expected status to be True")
        except requests.RequestException as e:
            self.fail(f"Request failed: {str(e)}")
        except KeyError as e:
            self.fail(f"Unexpected response format: {str(e)}")
        except Exception as e:
            self.fail(f"Unexpected error: {str(e)}")

if __name__ == '__main__':
    unittest.main()
