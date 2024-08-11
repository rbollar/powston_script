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
            yield 0, 0, f"R001 File {filename} not found", type(self)
            return

        API_KEY = os.getenv("POWSTON_API_KEY")
        powston_test_server = os.getenv("POWSTON_TEST_SERVER", 'https://dev.inverterintelligence.com')
        powston_api_test_code_endpoint = f'{powston_test_server}/api/check_code'
        
        body = {
            "code": content,
        }
        header = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        check_code_response = requests.post(powston_api_test_code_endpoint, json=body, headers=header)
        self.assertEqual(check_code_response.status_code, 200)
        self.assertIn('Success', check_code_response.json()['problems'])
        self.assertEqual(check_code_response.json()['status'], True)
        
        
        
        
if __name__ == '__main__':
    unittest.main()
