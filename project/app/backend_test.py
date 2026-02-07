#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Legal Aid System
Tests all endpoints with proper error handling and validation
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

class LegalAidAPITester:
    def __init__(self, base_url="https://jurismate.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_resources = {
            'students': [],
            'cases': [],
            'queries': [],
            'documents': []
        }

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
        
        self.test_results.append({
            'test': name,
            'success': success,
            'details': details,
            'response_data': response_data
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> tuple:
        """Make HTTP request and return success status and response"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, f"Unsupported method: {method}", {}

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            if not success:
                return False, f"Expected {expected_status}, got {response.status_code}: {response.text}", response_data
            
            return True, "Success", response_data

        except requests.exceptions.Timeout:
            return False, "Request timeout (30s)", {}
        except requests.exceptions.ConnectionError:
            return False, "Connection error - server may be down", {}
        except Exception as e:
            return False, f"Request error: {str(e)}", {}

    def test_health_check(self):
        """Test basic health check endpoint"""
        success, message, data = self.make_request('GET', '')
        self.log_test("Health Check", success, message, data)
        return success

    def test_seed_database(self):
        """Test database seeding"""
        success, message, data = self.make_request('POST', 'seed')
        self.log_test("Seed Database", success, message, data)
        return success

    def test_query_processing(self):
        """Test legal query processing with different languages and categories"""
        test_queries = [
            {
                "query_text": "How to file an FIR for theft?",
                "language": "en",
                "expected_category": "fir"
            },
            {
                "query_text": "मैं RTI कैसे दाखिल करूं?",
                "language": "hi", 
                "expected_category": "rti"
            },
            {
                "query_text": "Consumer complaint for defective product",
                "language": "en",
                "expected_category": "consumer"
            },
            {
                "query_text": "Domestic violence protection order",
                "language": "en",
                "expected_category": "family"
            }
        ]

        all_passed = True
        for i, query_data in enumerate(test_queries):
            success, message, response_data = self.make_request('POST', 'queries', query_data, 200)
            
            if success:
                # Validate response structure
                required_fields = ['id', 'query_text', 'detected_language', 'category', 'response_text', 'created_at']
                missing_fields = [field for field in required_fields if field not in response_data]
                
                if missing_fields:
                    success = False
                    message = f"Missing fields: {missing_fields}"
                else:
                    # Store query ID for later tests
                    self.created_resources['queries'].append(response_data['id'])
                    
                    # Check if category detection is working
                    if 'expected_category' in query_data:
                        if response_data.get('category') != query_data['expected_category']:
                            print(f"⚠️  Category mismatch for query {i+1}: expected {query_data['expected_category']}, got {response_data.get('category')}")

            self.log_test(f"Query Processing {i+1} ({query_data['language']})", success, message, response_data)
            if not success:
                all_passed = False

        return all_passed

    def test_query_retrieval(self):
        """Test query retrieval endpoints"""
        # Test get all queries
        success, message, data = self.make_request('GET', 'queries')
        self.log_test("Get All Queries", success, message, data)
        
        # Test get specific query if we have any
        if success and self.created_resources['queries']:
            query_id = self.created_resources['queries'][0]
            success2, message2, data2 = self.make_request('GET', f'queries/{query_id}')
            self.log_test("Get Specific Query", success2, message2, data2)
            return success and success2
        
        return success

    def test_student_management(self):
        """Test student CRUD operations"""
        # Test create student
        student_data = {
            "name": "Test Student",
            "email": "test.student@lawcollege.edu",
            "college": "Test Law University",
            "skills": ["Criminal Law", "RTI"]
        }
        
        success, message, response_data = self.make_request('POST', 'students', student_data, 200)
        self.log_test("Create Student", success, message, response_data)
        
        if success:
            student_id = response_data.get('id')
            self.created_resources['students'].append(student_id)
            
            # Test get all students
            success2, message2, data2 = self.make_request('GET', 'students')
            self.log_test("Get All Students", success2, message2, data2)
            
            # Test get specific student
            success3, message3, data3 = self.make_request('GET', f'students/{student_id}')
            self.log_test("Get Specific Student", success3, message3, data3)
            
            # Test get student cases (should be empty initially)
            success4, message4, data4 = self.make_request('GET', f'students/{student_id}/assigned-cases')
            self.log_test("Get Student Cases", success4, message4, data4)
            
            return success and success2 and success3 and success4
        
        return False

    def test_case_management(self):
        """Test case CRUD operations"""
        # Test create case
        case_data = {
            "title": "Test Legal Case",
            "description": "This is a test case for API testing",
            "category": "consumer"
        }
        
        success, message, response_data = self.make_request('POST', 'cases', case_data, 200)
        self.log_test("Create Case", success, message, response_data)
        
        if success:
            case_id = response_data.get('id')
            self.created_resources['cases'].append(case_id)
            
            # Test get all cases
            success2, message2, data2 = self.make_request('GET', 'cases')
            self.log_test("Get All Cases", success2, message2, data2)
            
            # Test get specific case
            success3, message3, data3 = self.make_request('GET', f'cases/{case_id}')
            self.log_test("Get Specific Case", success3, message3, data3)
            
            # Test update case (assign to student if available)
            if self.created_resources['students']:
                student_id = self.created_resources['students'][0]
                update_data = {
                    "status": "assigned",
                    "assigned_student_id": student_id
                }
                success4, message4, data4 = self.make_request('PATCH', f'cases/{case_id}', update_data)
                self.log_test("Update Case", success4, message4, data4)
                
                return success and success2 and success3 and success4
            
            return success and success2 and success3
        
        return False

    def test_document_generation(self):
        """Test document generation for FIR and RTI"""
        # Test FIR document generation
        fir_data = {
            "doc_type": "FIR",
            "language": "en",
            "details": {
                "name": "Test User",
                "age": "30",
                "address": "123 Test Street, Delhi",
                "incident_date": "2024-01-15",
                "incident_time": "10:00 AM",
                "incident_place": "Test Location",
                "incident_description": "Test incident description",
                "mobile": "9876543210",
                "email": "test@example.com"
            }
        }
        
        success, message, response_data = self.make_request('POST', 'documents', fir_data, 200)
        self.log_test("Generate FIR Document", success, message, response_data)
        
        if success:
            self.created_resources['documents'].append(response_data.get('id'))
        
        # Test RTI document generation
        rti_data = {
            "doc_type": "RTI",
            "language": "en",
            "details": {
                "name": "Test User",
                "address": "123 Test Street, Delhi",
                "department_name": "Municipal Corporation",
                "department_address": "City Hall, Delhi",
                "question_1": "What is the status of road construction project?",
                "question_2": "How much budget was allocated?",
                "question_3": "When will the project be completed?",
                "mobile": "9876543210",
                "email": "test@example.com"
            }
        }
        
        success2, message2, response_data2 = self.make_request('POST', 'documents', rti_data, 200)
        self.log_test("Generate RTI Document", success2, message2, response_data2)
        
        if success2:
            self.created_resources['documents'].append(response_data2.get('id'))
        
        # Test get all documents
        success3, message3, data3 = self.make_request('GET', 'documents')
        self.log_test("Get All Documents", success3, message3, data3)
        
        return success and success2 and success3

    def test_audio_functionality(self):
        """Test text-to-speech functionality"""
        tts_data = {
            "text": "This is a test audio message",
            "language": "en"
        }
        
        success, message, response_data = self.make_request('POST', 'tts', tts_data, 200)
        self.log_test("Text-to-Speech Generation", success, message, response_data)
        
        if success and 'audio_id' in response_data:
            # Test audio file retrieval
            audio_id = response_data['audio_id']
            try:
                audio_url = f"{self.base_url}/api/audio/{audio_id}"
                audio_response = requests.get(audio_url, timeout=30)
                audio_success = audio_response.status_code == 200 and audio_response.headers.get('content-type') == 'audio/mpeg'
                self.log_test("Audio File Retrieval", audio_success, 
                            f"Status: {audio_response.status_code}, Content-Type: {audio_response.headers.get('content-type')}")
                return success and audio_success
            except Exception as e:
                self.log_test("Audio File Retrieval", False, f"Error: {str(e)}")
                return False
        
        return success

    def test_statistics(self):
        """Test statistics endpoint"""
        success, message, data = self.make_request('GET', 'stats')
        self.log_test("Get Statistics", success, message, data)
        
        if success:
            # Validate statistics structure
            expected_fields = ['total_students', 'total_cases', 'total_queries', 'total_documents', 'cases_by_status']
            missing_fields = [field for field in expected_fields if field not in data]
            if missing_fields:
                self.log_test("Statistics Structure", False, f"Missing fields: {missing_fields}")
                return False
        
        return success

    def test_cleanup(self):
        """Clean up created test resources"""
        cleanup_success = True
        
        # Delete created students
        for student_id in self.created_resources['students']:
            success, message, _ = self.make_request('DELETE', f'students/{student_id}', expected_status=200)
            if not success:
                cleanup_success = False
                print(f"⚠️  Failed to delete student {student_id}: {message}")
        
        # Delete created cases
        for case_id in self.created_resources['cases']:
            success, message, _ = self.make_request('DELETE', f'cases/{case_id}', expected_status=200)
            if not success:
                cleanup_success = False
                print(f"⚠️  Failed to delete case {case_id}: {message}")
        
        self.log_test("Cleanup Resources", cleanup_success, 
                     f"Cleaned {len(self.created_resources['students'])} students, {len(self.created_resources['cases'])} cases")
        
        return cleanup_success

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("🚀 Starting Legal Aid System API Tests")
        print(f"📡 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("Seed Database", self.test_seed_database),
            ("Query Processing", self.test_query_processing),
            ("Query Retrieval", self.test_query_retrieval),
            ("Student Management", self.test_student_management),
            ("Case Management", self.test_case_management),
            ("Document Generation", self.test_document_generation),
            ("Audio Functionality", self.test_audio_functionality),
            ("Statistics", self.test_statistics),
            ("Cleanup", self.test_cleanup)
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 Running {test_name} tests...")
            try:
                test_func()
            except Exception as e:
                self.log_test(f"{test_name} (Exception)", False, f"Unexpected error: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  • {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = LegalAidAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())