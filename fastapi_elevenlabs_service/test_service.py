#!/usr/bin/env python3
"""
Test script for ElevenLabs Voice Cloning Service
Comprehensive testing of all components and endpoints
"""

import asyncio
import requests
import json
import time
from pathlib import Path
import tempfile
import os

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30  # seconds

def test_app_initialization():
    """Test that the FastAPI app can be initialized"""
    print("\n=== Testing App Initialization ===")

    try:
        # Import and create app
        from main import app
        print("+ FastAPI app created successfully")

        # Test settings
        from config.settings import get_settings
        settings = get_settings()
        print(f"+ Settings loaded: {settings.app_name} v{settings.app_version}")

        # Test services
        from services.voice_cloning import get_voice_cloning_service
        voice_service = get_voice_cloning_service()
        print("+ Voice cloning service initialized")

        from services.queue_manager import get_queue_manager
        queue_manager = get_queue_manager()
        print("+ Queue manager initialized")

        from services.notifications import get_notification_manager
        notification_manager = get_notification_manager()
        print("+ Notification manager initialized")

        print("SUCCESS: All components initialized correctly")
        return True

    except Exception as e:
        print(f"FAILED: Initialization error: {e}")
        return False

def test_health_endpoint():
    """Test health check endpoint"""
    print("\n=== Testing Health Endpoint ===")

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)

        if response.status_code == 200:
            health_data = response.json()
            print(f"+ Health status: {health_data.get('status', 'unknown')}")
            print(f"+ Version: {health_data.get('version', 'unknown')}")
            print(f"+ ElevenLabs API: {health_data.get('elevenlabs_api', 'unknown')}")
            print("SUCCESS: Health endpoint working")
            return True
        else:
            print(f"FAILED: Health endpoint returned {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"FAILED: Could not reach health endpoint: {e}")
        return False

def test_voices_list_endpoint():
    """Test voices listing endpoint"""
    print("\n=== Testing Voices List Endpoint ===")

    try:
        response = requests.get(f"{BASE_URL}/voices/list", timeout=15)

        if response.status_code == 200:
            voices_data = response.json()
            total_voices = voices_data.get('total_voices', 0)
            custom_voices = voices_data.get('custom_voices', 0)
            print(f"+ Total voices: {total_voices}")
            print(f"+ Custom voices: {custom_voices}")
            print("SUCCESS: Voices list endpoint working")
            return True
        else:
            print(f"FAILED: Voices list returned {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"FAILED: Could not reach voices list endpoint: {e}")
        return False

def test_notification_system():
    """Test notification system"""
    print("\n=== Testing Notification System ===")

    try:
        # Test email notification
        email_payload = {
            "notification_type": "email",
            "recipient": "test@example.com",
            "test_data": {
                "job_id": "test_job_123",
                "voice_name": "Test Voice"
            }
        }

        response = requests.post(
            f"{BASE_URL}/test/notification",
            json=email_payload,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"+ Email notification test: {result.get('success', False)}")
        else:
            print(f"- Email notification test failed: {response.status_code}")

        # Test webhook notification
        webhook_payload = {
            "notification_type": "webhook",
            "recipient": "https://api.example.com/webhook",
            "test_data": {
                "job_id": "test_job_456",
                "voice_name": "Test Voice"
            }
        }

        response = requests.post(
            f"{BASE_URL}/test/notification",
            json=webhook_payload,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"+ Webhook notification test: {result.get('success', False)}")
            print("SUCCESS: Notification system working")
            return True
        else:
            print(f"- Webhook notification test failed: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"FAILED: Could not test notifications: {e}")
        return False

def create_test_audio_file():
    """Create a test MP3 file for testing"""
    try:
        # Create a small test MP3 file (just headers)
        test_content = b'ID3\x04\x00\x00\x00\x00\x00\x00' + b'\x00' * 1000  # Minimal MP3 structure

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file.write(test_content)
        temp_file.close()

        return temp_file.name
    except Exception as e:
        print(f"Could not create test audio file: {e}")
        return None

def test_voice_cloning_submission():
    """Test voice cloning job submission"""
    print("\n=== Testing Voice Cloning Submission ===")

    # Check if we have real marjorie files to use
    real_files = []
    for filename in ["marjorie1.mp3", "marjorie2.mp3", "marjorie3.mp3"]:
        file_path = Path("../") / filename
        if file_path.exists():
            real_files.append(file_path)

    if real_files:
        print(f"+ Using real audio files: {[f.name for f in real_files]}")
        test_files = real_files
    else:
        print("+ Creating test audio file...")
        test_file = create_test_audio_file()
        if test_file:
            test_files = [test_file]
        else:
            print("FAILED: Could not create test audio file")
            return False

    try:
        # Prepare files for upload
        files = []
        for file_path in test_files:
            with open(file_path, 'rb') as f:
                files.append(('files', (Path(file_path).name, f.read(), 'audio/mpeg')))

        # Prepare form data
        data = {
            'voice_name': 'Test Voice Clone',
            'text': 'This is a test of voice cloning functionality.',
            'description': 'Test voice clone for service validation',
            'notification_email': 'test@example.com'
        }

        print("+ Submitting voice cloning job...")
        response = requests.post(
            f"{BASE_URL}/clone-voice",
            files=files,
            data=data,
            timeout=30
        )

        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data.get('job_id')
            print(f"+ Job submitted successfully: {job_id}")
            print(f"+ Status: {job_data.get('status')}")

            # Test job status endpoint
            time.sleep(2)  # Wait a bit for processing
            status_response = requests.get(
                f"{BASE_URL}/job/{job_id}/status",
                timeout=10
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"+ Job status check successful: {status_data.get('status')}")
                print(f"+ Progress: {status_data.get('progress', 0)}%")
                print("SUCCESS: Voice cloning submission working")
                return True
            else:
                print(f"- Job status check failed: {status_response.status_code}")
                return False

        else:
            print(f"FAILED: Voice cloning submission returned {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"FAILED: Could not submit voice cloning job: {e}")
        return False
    finally:
        # Cleanup test file if created
        if not real_files and 'test_file' in locals() and test_file:
            try:
                os.unlink(test_file)
            except:
                pass

def run_full_test_suite():
    """Run complete test suite"""
    print("ELEVENLABS VOICE CLONING SERVICE - TEST SUITE")
    print("=" * 60)

    tests = [
        ("App Initialization", test_app_initialization),
        ("Health Endpoint", test_health_endpoint),
        ("Voices List Endpoint", test_voices_list_endpoint),
        ("Notification System", test_notification_system),
        ("Voice Cloning Submission", test_voice_cloning_submission),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"FAILED: {test_name} - Exception: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("SUCCESS: All tests passed!")
    else:
        print(f"WARNING: {total - passed} tests failed")

    return passed == total

if __name__ == "__main__":
    run_full_test_suite()