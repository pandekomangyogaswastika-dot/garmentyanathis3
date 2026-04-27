#!/usr/bin/env python3
"""
Focused Backend API Testing for Garment ERP v8.0 - Phase 10C + Phase 10B-rem
Testing specific requirements from the review request.
"""

import requests
import sys
import json
from datetime import datetime

class FocusedGarmentERPTester:
    def __init__(self, base_url="https://erp-audit-ready.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.passed_tests.append(name)
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.failed_tests.append({
                    'test': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:500]
                })
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            self.failed_tests.append({
                'test': name,
                'error': str(e)
            })
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def login_admin(self):
        """Login as admin user"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@garment.com", "password": "Admin@123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            return True
        return False

    def test_specific_requirements(self):
        """Test specific requirements from review request"""
        print("\n" + "="*80)
        print("TESTING SPECIFIC REQUIREMENTS FROM REVIEW REQUEST")
        print("="*80)
        
        # 1. Backend pagination envelope shape: GET /api/products?page=1&per_page=5
        success, response = self.run_test(
            "Products pagination envelope {items, total, page, per_page, total_pages}",
            "GET",
            "products?page=1&per_page=5",
            200
        )
        
        if success:
            required_keys = ['items', 'total', 'page', 'per_page', 'total_pages']
            if all(key in response for key in required_keys):
                print(f"✅ Products envelope has all required keys: {required_keys}")
                # Verify types
                if (isinstance(response['items'], list) and 
                    isinstance(response['total'], int) and
                    isinstance(response['page'], int) and
                    isinstance(response['per_page'], int) and
                    isinstance(response['total_pages'], int)):
                    print(f"✅ All envelope fields have correct types")
                else:
                    print(f"❌ Some envelope fields have incorrect types")
                    self.failed_tests.append({
                        'test': 'Products envelope field types',
                        'issue': 'Incorrect field types in envelope'
                    })
            else:
                missing = [k for k in required_keys if k not in response]
                print(f"❌ Products envelope missing keys: {missing}")
                self.failed_tests.append({
                    'test': 'Products pagination envelope structure',
                    'issue': f'Missing keys: {missing}'
                })

        # 2. Backend pagination legacy compat: GET /api/products (no page param) returns JSON array
        success, response = self.run_test(
            "Products legacy compatibility (no page param returns array)",
            "GET",
            "products",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"✅ Products returns JSON array without pagination params")
            else:
                print(f"❌ Products should return JSON array, got: {type(response)}")
                self.failed_tests.append({
                    'test': 'Products legacy compatibility',
                    'issue': f'Expected JSON array, got {type(response)}'
                })

        # 3. Backend pagination on /api/production-pos with specific params
        success, response = self.run_test(
            "Production POs pagination with sort and H-1 fields",
            "GET",
            "production-pos?page=1&per_page=5&sort_by=created_at&sort_dir=desc",
            200
        )
        
        if success:
            # Check envelope structure
            required_keys = ['items', 'total', 'page', 'per_page', 'total_pages']
            if all(key in response for key in required_keys):
                print(f"✅ Production POs envelope structure correct")
                
                # Check H-1 fields in items (if any items exist)
                items = response.get('items', [])
                if items:
                    first_item = items[0]
                    if 'remaining_qty_to_ship' in first_item and 'over_shipped_qty' in first_item:
                        print(f"✅ H-1 fields present: remaining_qty_to_ship, over_shipped_qty")
                        
                        # Verify remaining_qty_to_ship is clamped at 0
                        remaining = first_item.get('remaining_qty_to_ship')
                        if remaining is not None and remaining >= 0:
                            print(f"✅ remaining_qty_to_ship properly clamped: {remaining}")
                        elif remaining is not None:
                            print(f"❌ remaining_qty_to_ship is negative: {remaining}")
                            self.failed_tests.append({
                                'test': 'H-1 remaining_qty_to_ship clamping',
                                'issue': f'remaining_qty_to_ship is negative: {remaining}'
                            })
                    else:
                        print(f"❌ H-1 fields missing from production POs")
                        self.failed_tests.append({
                            'test': 'H-1 fields in production POs',
                            'issue': 'Missing remaining_qty_to_ship or over_shipped_qty fields'
                        })
                else:
                    print(f"ℹ️  No production POs to test H-1 fields")

        # 4. Test all paginated endpoints mentioned in review request
        paginated_endpoints = [
            ("invoices", "Invoices"),
            ("payments", "Payments"),
            ("activity-logs", "Activity Logs")
        ]
        
        for endpoint, name in paginated_endpoints:
            # Test envelope when page param provided
            success, response = self.run_test(
                f"{name} pagination envelope",
                "GET",
                f"{endpoint}?page=1&per_page=5",
                200
            )
            
            if success:
                required_keys = ['items', 'total', 'page', 'per_page', 'total_pages']
                if all(key in response for key in required_keys):
                    print(f"✅ {name} envelope structure correct")
                else:
                    missing = [k for k in required_keys if k not in response]
                    print(f"❌ {name} envelope missing keys: {missing}")
                    self.failed_tests.append({
                        'test': f'{name} pagination envelope',
                        'issue': f'Missing keys: {missing}'
                    })
            
            # Test legacy array when no page param
            success, response = self.run_test(
                f"{name} legacy array compatibility",
                "GET",
                endpoint,
                200
            )
            
            if success:
                if isinstance(response, list):
                    print(f"✅ {name} returns array without pagination")
                else:
                    print(f"❌ {name} should return array, got: {type(response)}")
                    self.failed_tests.append({
                        'test': f'{name} legacy compatibility',
                        'issue': f'Expected array, got {type(response)}'
                    })

        # 5. Test Phase 10B-rem report endpoints
        report_endpoints = [
            ("reports/production?status=Draft", "Production Report"),
            ("reports/shipment", "Shipment Report"),
            ("reports/progress", "Progress Report"),
            ("reports/return", "Return Report"),
            ("reports/accessory", "Accessory Report"),
            ("distribusi-kerja", "Distribusi Kerja"),
            ("production-monitoring-v2", "Production Monitoring V2")
        ]
        
        for endpoint, name in report_endpoints:
            success, response = self.run_test(
                f"{name} optimized endpoint",
                "GET",
                endpoint,
                200
            )
            
            if success:
                if isinstance(response, list):
                    print(f"✅ {name} returns array (count: {len(response)})")
                elif isinstance(response, dict):
                    if name == "Distribusi Kerja" and 'hierarchy' in response and 'flat' in response:
                        print(f"✅ {name} returns expected structure")
                    elif 'data' in response and isinstance(response['data'], list):
                        print(f"✅ {name} returns data array (count: {len(response['data'])})")
                    else:
                        print(f"❌ {name} unexpected structure: {list(response.keys())}")
                        self.failed_tests.append({
                            'test': f'{name} response structure',
                            'issue': f'Unexpected structure: {type(response)}'
                        })

        # 6. Test variance feature endpoints (smoke test)
        variance_endpoints = [
            ("production-variances", "Production Variances"),
            ("production-variances/stats", "Production Variances Stats")
        ]
        
        for endpoint, name in variance_endpoints:
            success, response = self.run_test(
                f"{name} endpoint",
                "GET",
                endpoint,
                200
            )
            
            if success:
                print(f"✅ {name} endpoint working")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("FOCUSED TEST SUMMARY")
        print("="*80)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {len(self.failed_tests)}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for i, failure in enumerate(self.failed_tests, 1):
                print(f"{i}. {failure.get('test', 'Unknown test')}")
                if 'issue' in failure:
                    print(f"   Issue: {failure['issue']}")
                if 'error' in failure:
                    print(f"   Error: {failure['error']}")
                if 'expected' in failure and 'actual' in failure:
                    print(f"   Expected: {failure['expected']}, Got: {failure['actual']}")

def main():
    print("🎯 Focused Backend Testing for Garment ERP v8.0")
    print("Phase 10C (pagination) + Phase 10B-rem (batch-fix N+1)")
    print("="*80)
    
    tester = FocusedGarmentERPTester()
    
    # Login as admin
    if not tester.login_admin():
        print("❌ Cannot proceed without admin login")
        return 1
    
    # Run focused tests
    tester.test_specific_requirements()
    
    # Print summary
    tester.print_summary()
    
    # Return appropriate exit code
    return 0 if len(tester.failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())