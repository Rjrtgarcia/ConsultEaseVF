#!/usr/bin/env python3
"""
Run MQTT Diagnostics for ConsultEase System
This script runs comprehensive MQTT diagnostics from within the ConsultEase environment.
"""

import sys
import os
import logging
import time

# Add the central_system directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mqtt_diagnostics_run.log')
    ]
)
logger = logging.getLogger(__name__)


def run_mqtt_diagnostics():
    """Run comprehensive MQTT diagnostics."""
    logger.info("🔍 Starting ConsultEase MQTT Diagnostics")
    logger.info("=" * 60)
    
    try:
        # Import the diagnostics tool
        from central_system.utils.mqtt_diagnostics import MQTTDiagnostics
        
        # Create diagnostics instance
        diagnostics = MQTTDiagnostics()
        
        # Run diagnostics for 2 minutes
        logger.info("⏰ Running diagnostics for 2 minutes...")
        diagnostics.start_diagnostics(duration_minutes=2)
        
        logger.info("✅ MQTT diagnostics completed successfully")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import diagnostics module: {e}")
        logger.error("Make sure you're running this from the ConsultEase root directory")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error running diagnostics: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
        
    return True


def test_mqtt_service_directly():
    """Test the MQTT service directly."""
    logger.info("🔧 Testing MQTT service directly...")
    
    try:
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        from central_system.config import get_config
        
        # Get configuration
        config = get_config()
        logger.info("📋 Current MQTT Configuration:")
        logger.info(f"  Broker Host: {config.get('mqtt.broker_host', 'localhost')}")
        logger.info(f"  Broker Port: {config.get('mqtt.broker_port', 1883)}")
        logger.info(f"  Username: {config.get('mqtt.username', 'None')}")
        logger.info(f"  Password: {'Set' if config.get('mqtt.password') else 'None'}")
        
        # Get MQTT service
        mqtt_service = get_async_mqtt_service()
        
        logger.info("🔍 MQTT Service Status:")
        logger.info(f"  Connected: {mqtt_service.is_connected}")
        logger.info(f"  Running: {mqtt_service.running}")
        
        if hasattr(mqtt_service, 'get_stats'):
            stats = mqtt_service.get_stats()
            logger.info(f"  Messages Received: {stats.get('messages_received', 'Unknown')}")
            logger.info(f"  Messages Published: {stats.get('messages_published', 'Unknown')}")
            logger.info(f"  Last Error: {stats.get('last_error', 'None')}")
        
        # Check registered handlers
        handlers = mqtt_service.message_handlers
        logger.info(f"📡 Registered Message Handlers ({len(handlers)}):")
        for topic, handler in handlers.items():
            handler_name = getattr(handler, '__name__', str(handler))
            logger.info(f"  - {topic} -> {handler_name}")
            
        # Test publishing a diagnostic message
        if mqtt_service.is_connected:
            logger.info("📤 Testing message publishing...")
            test_topic = "consultease/diagnostics/test"
            test_data = {
                'type': 'diagnostic_test',
                'timestamp': time.time(),
                'source': 'mqtt_diagnostics_script'
            }
            
            mqtt_service.publish_async(test_topic, test_data)
            logger.info(f"✅ Test message published to {test_topic}")
        else:
            logger.warning("⚠️ Cannot test publishing - MQTT service not connected")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing MQTT service: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def test_faculty_controller():
    """Test the faculty controller MQTT integration."""
    logger.info("👥 Testing Faculty Controller MQTT Integration...")
    
    try:
        from central_system.controllers.faculty_controller import FacultyController
        
        # Create faculty controller instance
        faculty_controller = FacultyController()
        
        logger.info(f"📊 Faculty Controller Status:")
        logger.info(f"  Callbacks registered: {len(faculty_controller.callbacks)}")
        
        # List callback functions
        for i, callback in enumerate(faculty_controller.callbacks):
            callback_name = getattr(callback, '__name__', f'callback_{i}')
            logger.info(f"    - {callback_name}")
            
        # Test the real-time update system
        logger.info("🧪 Testing faculty controller real-time updates...")
        success = faculty_controller.test_real_time_updates()
        
        if success:
            logger.info("✅ Faculty controller real-time update test successful")
        else:
            logger.warning("⚠️ Faculty controller real-time update test failed")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error testing faculty controller: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def check_system_integration():
    """Check the overall system integration."""
    logger.info("🔗 Checking System Integration...")
    
    try:
        # Test if main application components are available
        from central_system.main import ConsultEaseApp
        from central_system.models import Faculty, get_db
        
        # Check database connectivity
        logger.info("🗄️ Testing database connectivity...")
        db = get_db()
        faculties = db.query(Faculty).all()
        logger.info(f"📊 Found {len(faculties)} faculty records in database")
        
        for faculty in faculties:
            logger.info(f"  - ID: {faculty.id}, Name: {faculty.name}, Status: {faculty.status}")
            
        db.close()
        
        logger.info("✅ System integration check completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking system integration: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def main():
    """Main function to run all diagnostics."""
    print("🔍 ConsultEase MQTT Diagnostics Runner")
    print("This script will run comprehensive MQTT diagnostics")
    print("=" * 60)
    
    results = {
        'mqtt_service': False,
        'faculty_controller': False,
        'system_integration': False,
        'full_diagnostics': False
    }
    
    # Test 1: MQTT Service
    logger.info("\n🔧 TEST 1: MQTT Service Direct Test")
    results['mqtt_service'] = test_mqtt_service_directly()
    
    # Test 2: Faculty Controller
    logger.info("\n👥 TEST 2: Faculty Controller Test")
    results['faculty_controller'] = test_faculty_controller()
    
    # Test 3: System Integration
    logger.info("\n🔗 TEST 3: System Integration Test")
    results['system_integration'] = check_system_integration()
    
    # Test 4: Full Diagnostics
    logger.info("\n🔍 TEST 4: Full MQTT Diagnostics")
    results['full_diagnostics'] = run_mqtt_diagnostics()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DIAGNOSTIC RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 All tests passed! MQTT system appears to be working correctly.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
        
    print("\n📝 Detailed logs saved to mqtt_diagnostics_run.log")
    print("🔍 For standalone MQTT testing, run: python mqtt_investigation.py")


if __name__ == "__main__":
    main()
