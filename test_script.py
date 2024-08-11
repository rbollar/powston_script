import unittest
import os
import requests

class TestUserScript(unittest.TestCase):

    def test_script(self):
        filename = "script.py"
        try:
            with open(filename, "r") as file:
                content = file.read()
        except FileNotFoundError:
            self.fail(f"R001 File {filename} not found")
            return

        API_KEY = os.getenv("POWSTON_API_KEY")
        if not API_KEY:
            self.fail("POWSTON_API_KEY environment variable is not set")
            return

        powston_test_server = os.getenv("POWSTON_TEST_SERVER", 'https://dev.inverterintelligence.com')
        powston_api_test_code_endpoint = f'{powston_test_server}/api/check_code'
        
        body = {
            "code": content,
        }
        header = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            check_code_response = requests.post(powston_api_test_code_endpoint, json=body, headers=header)
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