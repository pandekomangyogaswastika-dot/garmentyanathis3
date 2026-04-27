#!/usr/bin/env python3
"""
Backend API Testing for Garment ERP v8.0 - Phase 10C + Phase 10B-rem
Testing pagination envelope shape, legacy compatibility, and regression fixes.
"""

import requests
import sys
import json
from datetime import datetime

class GarmentERPTester:
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
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

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
                print(f"Response: {response.text[:200]}")
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
            print(f"✅ Admin logged in successfully")
            return True
        print(f"❌ Admin login failed")
        return False

    def test_pagination_envelope_shape(self):
        """Test Phase 10C: Backend pagination envelope shape"""
        print("\n" + "="*60)
        print("TESTING PAGINATION ENVELOPE SHAPE")
        print("="*60)
        
        # Test products pagination envelope
        success, response = self.run_test(
            "Products pagination envelope (page=1&per_page=5)",
            "GET",
            "products?page=1&per_page=5",
            200
        )
        
        if success:
            required_keys = ['items', 'total', 'page', 'per_page', 'total_pages']
            if all(key in response for key in required_keys):
                print(f"✅ Products envelope has all required keys: {required_keys}")
                print(f"   Items count: {len(response.get('items', []))}")
                print(f"   Total: {response.get('total')}")
                print(f"   Page: {response.get('page')}")
                print(f"   Per page: {response.get('per_page')}")
                print(f"   Total pages: {response.get('total_pages')}")
            else:
                missing = [k for k in required_keys if k not in response]
                print(f"❌ Products envelope missing keys: {missing}")
                self.failed_tests.append({
                    'test': 'Products pagination envelope structure',
                    'issue': f'Missing keys: {missing}'
                })

        # Test production-pos pagination envelope with sorting
        success, response = self.run_test(
            "Production POs pagination with sort (page=1&per_page=5&sort_by=created_at&sort_dir=desc)",
            "GET",
            "production-pos?page=1&per_page=5&sort_by=created_at&sort_dir=desc",
            200
        )
        
        if success:
            required_keys = ['items', 'total', 'page', 'per_page', 'total_pages']
            if all(key in response for key in required_keys):
                print(f"✅ Production POs envelope has all required keys")
                # Check H-1 fix: remaining_qty_to_ship and over_shipped_qty fields
                items = response.get('items', [])
                if items:
                    first_item = items[0]
                    if 'remaining_qty_to_ship' in first_item and 'over_shipped_qty' in first_item:
                        print(f"✅ H-1 fix verified: remaining_qty_to_ship and over_shipped_qty fields present")
                        print(f"   remaining_qty_to_ship: {first_item.get('remaining_qty_to_ship')}")
                        print(f"   over_shipped_qty: {first_item.get('over_shipped_qty')}")
                        
                        # Verify remaining_qty_to_ship is clamped at 0 (if not None)
                        remaining = first_item.get('remaining_qty_to_ship')
                        if remaining is not None and remaining >= 0:
                            print(f"✅ remaining_qty_to_ship properly clamped at 0 or positive: {remaining}")
                        elif remaining is not None and remaining < 0:
                            print(f"❌ remaining_qty_to_ship is negative: {remaining}")
                            self.failed_tests.append({
                                'test': 'H-1 remaining_qty_to_ship clamping',
                                'issue': f'remaining_qty_to_ship is negative: {remaining}'
                            })
                        else:
                            print(f"ℹ️  remaining_qty_to_ship is None (no data to test clamping)")
                    else:
                        print(f"❌ H-1 fix missing: remaining_qty_to_ship or over_shipped_qty fields not found")
                        self.failed_tests.append({
                            'test': 'H-1 fix verification',
                            'issue': 'Missing remaining_qty_to_ship or over_shipped_qty fields'
                        })
                else:
                    print(f"ℹ️  No production POs found to test H-1 fix fields")

    def test_legacy_compatibility(self):
        """Test Phase 10C: Legacy compatibility (no page param returns array)"""
        print("\n" + "="*60)
        print("TESTING LEGACY COMPATIBILITY")
        print("="*60)
        
        # Test products without pagination params
        success, response = self.run_test(
            "Products legacy array (no page param)",
            "GET",
            "products",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"✅ Products returns array without pagination params (count: {len(response)})")
            else:
                print(f"❌ Products should return array without pagination params, got: {type(response)}")
                self.failed_tests.append({
                    'test': 'Products legacy compatibility',
                    'issue': f'Expected array, got {type(response)}'
                })

        # Test production-pos without pagination params
        success, response = self.run_test(
            "Production POs legacy array (no page param)",
            "GET",
            "production-pos",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"✅ Production POs returns array without pagination params (count: {len(response)})")
            else:
                print(f"❌ Production POs should return array without pagination params, got: {type(response)}")
                self.failed_tests.append({
                    'test': 'Production POs legacy compatibility',
                    'issue': f'Expected array, got {type(response)}'
                })

    def test_report_endpoints_optimization(self):
        """Test Phase 10B-rem: Report endpoints still return correct shape (arrays)"""
        print("\n" + "="*60)
        print("TESTING PHASE 10B-REM REPORT ENDPOINTS")
        print("="*60)
        
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
                f"{name} endpoint shape",
                "GET",
                endpoint,
                200
            )
            
            if success:
                if isinstance(response, list):
                    print(f"✅ {name} returns array as expected (count: {len(response)})")
                elif isinstance(response, dict):
                    # Check for specific distribusi-kerja format
                    if name == "Distribusi Kerja" and 'hierarchy' in response and 'flat' in response:
                        print(f"✅ {name} returns expected structure with hierarchy and flat arrays")
                    elif 'data' in response and isinstance(response['data'], list):
                        # Some reports might return {data: [...], ...} format
                        print(f"✅ {name} returns data array as expected (count: {len(response['data'])})")
                    else:
                        print(f"❌ {name} data field should be array, got: {type(response.get('data', 'missing'))}")
                        self.failed_tests.append({
                            'test': f'{name} data structure',
                            'issue': f'Expected data array, got {type(response.get("data", "missing"))}'
                        })
                else:
                    print(f"❌ {name} should return array or {{data: array}}, got: {type(response)}")
                    self.failed_tests.append({
                        'test': f'{name} response structure',
                        'issue': f'Expected array or data object, got {type(response)}'
                    })

    def test_pagination_with_filters(self):
        """Test pagination with filters and sorting"""
        print("\n" + "="*60)
        print("TESTING PAGINATION WITH FILTERS")
        print("="*60)
        
        # Test production-pos with status filter and sorting
        success, response = self.run_test(
            "Production POs with filter and sort (page=1&per_page=5&status=Draft&sort_by=po_number&sort_dir=asc)",
            "GET",
            "production-pos?page=1&per_page=5&status=Draft&sort_by=po_number&sort_dir=asc",
            200
        )
        
        if success:
            items = response.get('items', [])
            total = response.get('total', 0)
            
            # Verify items length <= per_page
            if len(items) <= 5:
                print(f"✅ Items length ({len(items)}) <= per_page (5)")
            else:
                print(f"❌ Items length ({len(items)}) > per_page (5)")
                self.failed_tests.append({
                    'test': 'Pagination per_page limit',
                    'issue': f'Items length {len(items)} exceeds per_page 5'
                })
            
            # Verify total >= items length
            if total >= len(items):
                print(f"✅ Total ({total}) >= items length ({len(items)})")
            else:
                print(f"❌ Total ({total}) < items length ({len(items)})")
                self.failed_tests.append({
                    'test': 'Pagination total consistency',
                    'issue': f'Total {total} < items length {len(items)}'
                })
            
            # Verify items satisfy filter (status=Draft)
            draft_items = [item for item in items if item.get('status') == 'Draft']
            if len(draft_items) == len(items):
                print(f"✅ All items satisfy status=Draft filter")
            else:
                print(f"❌ Not all items satisfy status=Draft filter ({len(draft_items)}/{len(items)})")
                self.failed_tests.append({
                    'test': 'Filter application',
                    'issue': f'Only {len(draft_items)}/{len(items)} items match status=Draft'
                })

    def test_other_paginated_endpoints(self):
        """Test other endpoints mentioned for pagination"""
        print("\n" + "="*60)
        print("TESTING OTHER PAGINATED ENDPOINTS")
        print("="*60)
        
        endpoints = [
            ("invoices?page=1&per_page=5", "Invoices"),
            ("payments?page=1&per_page=5", "Payments"),
            ("activity-logs?page=1&per_page=5", "Activity Logs")
        ]
        
        for endpoint, name in endpoints:
            success, response = self.run_test(
                f"{name} pagination envelope",
                "GET",
                endpoint,
                200
            )
            
            if success:
                required_keys = ['items', 'total', 'page', 'per_page', 'total_pages']
                if all(key in response for key in required_keys):
                    print(f"✅ {name} envelope has all required keys")
                else:
                    missing = [k for k in required_keys if k not in response]
                    print(f"❌ {name} envelope missing keys: {missing}")
                    self.failed_tests.append({
                        'test': f'{name} pagination envelope',
                        'issue': f'Missing keys: {missing}'
                    })
            
            # Test legacy compatibility
            legacy_endpoint = endpoint.split('?')[0]  # Remove query params
            success, response = self.run_test(
                f"{name} legacy array",
                "GET",
                legacy_endpoint,
                200
            )
            
            if success:
                if isinstance(response, list):
                    print(f"✅ {name} returns array without pagination params")
                else:
                    print(f"❌ {name} should return array without pagination params, got: {type(response)}")
                    self.failed_tests.append({
                        'test': f'{name} legacy compatibility',
                        'issue': f'Expected array, got {type(response)}'
                    })

    def test_regression_fixes(self):
        """Test regression fixes from production flow audit"""
        print("\n" + "="*60)
        print("TESTING REGRESSION FIXES")
        print("="*60)
        
        # C-3: GET /api/production-jobs returns total_shipped_to_buyer correctly
        success, response = self.run_test(
            "C-3: Production jobs total_shipped_to_buyer",
            "GET",
            "production-jobs",
            200
        )
        
        if success and isinstance(response, list) and response:
            first_job = response[0]
            if 'total_shipped_to_buyer' in first_job:
                print(f"✅ C-3: total_shipped_to_buyer field present: {first_job.get('total_shipped_to_buyer')}")
            else:
                print(f"❌ C-3: total_shipped_to_buyer field missing")
                self.failed_tests.append({
                    'test': 'C-3 total_shipped_to_buyer field',
                    'issue': 'total_shipped_to_buyer field missing from production jobs'
                })

    def test_variance_feature_integrity(self):
        """Test variance feature endpoints (smoke test)"""
        print("\n" + "="*60)
        print("TESTING VARIANCE FEATURE INTEGRITY")
        print("="*60)
        
        # Test GET /api/production-variances/stats
        success, response = self.run_test(
            "Production variances stats",
            "GET",
            "production-variances/stats",
            200
        )
        
        if success:
            print(f"✅ Production variances stats endpoint working")
        
        # Test GET /api/production-variances
        success, response = self.run_test(
            "Production variances list",
            "GET",
            "production-variances",
            200
        )
        
        if success:
            print(f"✅ Production variances list endpoint working")

    def test_critical_guardrails_spot_check(self):
        """Spot check critical guardrails (C-1, C-2, H-4, M-1, M-3)"""
        print("\n" + "="*60)
        print("TESTING CRITICAL GUARDRAILS (SPOT CHECK)")
        print("="*60)
        
        # Note: These are spot checks to verify the endpoints exist
        # Full testing would require creating test data which is complex
        
        # Test that endpoints exist and return proper responses
        test_cases = [
            ("production-returns", "GET", None, "Production returns endpoint exists"),
            ("buyer-shipments", "GET", None, "Buyer shipments endpoint exists"),
            ("production-jobs", "GET", None, "Production jobs endpoint exists"),
        ]
        
        for endpoint, method, data, description in test_cases:
            success, response = self.run_test(
                description,
                method,
                endpoint,
                200  # Expecting 200 OK for GET requests
            )
            
            if success:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - endpoint not accessible")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
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
        
        if self.passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for i, test in enumerate(self.passed_tests, 1):
                print(f"{i}. {test}")

def main():
    print("🚀 Starting Garment ERP v8.0 Backend Testing")
    print("Phase 10C (pagination) + Phase 10B-rem (batch-fix N+1)")
    print("="*80)
    
    tester = GarmentERPTester()
    
    # Login as admin
    if not tester.login_admin():
        print("❌ Cannot proceed without admin login")
        return 1
    
    # Run all test suites
    tester.test_pagination_envelope_shape()
    tester.test_legacy_compatibility()
    tester.test_report_endpoints_optimization()
    tester.test_pagination_with_filters()
    tester.test_other_paginated_endpoints()
    tester.test_regression_fixes()
    tester.test_variance_feature_integrity()
    tester.test_critical_guardrails_spot_check()
    
    # Print summary
    tester.print_summary()
    
    # Return appropriate exit code
    return 0 if len(tester.failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())