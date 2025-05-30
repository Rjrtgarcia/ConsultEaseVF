#!/usr/bin/env python3
"""
Debug script to test MQTT functionality and identify issues with faculty status updates.
"""

import sys
import os
import logging
import time
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mqtt_debug.log')
    ]
)
logger = logging.getLogger(__name__)

def test_mqtt_service():
    """Test MQTT service functionality."""
    logger.info("=== MQTT Service Test ===")
    
    try:
        # Import MQTT service
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        mqtt_service = get_async_mqtt_service()
        
        logger.info(f"MQTT Service initialized: {mqtt_service}")
        logger.info(f"MQTT Service connected: {mqtt_service.is_connected}")
        logger.info(f"MQTT Service running: {mqtt_service.running}")
        
        # Try to connect if not connected
        if not mqtt_service.is_connected:
            logger.info("Attempting to connect MQTT service...")
            mqtt_service.connect()
            
            # Wait a bit for connection
            time.sleep(2)
            logger.info(f"MQTT Service connected after connect attempt: {mqtt_service.is_connected}")
        
        # Get service stats
        stats = mqtt_service.get_stats()
        logger.info(f"MQTT Service stats: {stats}")
        
        return mqtt_service.is_connected
        
    except Exception as e:
        logger.error(f"Error testing MQTT service: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_faculty_controller():
    """Test faculty controller MQTT subscriptions."""
    logger.info("=== Faculty Controller Test ===")
    
    try:
        # Import faculty controller
        from central_system.controllers.faculty_controller import FacultyController
        faculty_controller = FacultyController()
        
        logger.info(f"Faculty Controller initialized: {faculty_controller}")
        logger.info(f"Faculty Controller has callbacks: {hasattr(faculty_controller, 'callbacks')}")
        logger.info(f"Faculty Controller has queue_service: {hasattr(faculty_controller, 'queue_service')}")
        
        # Start the controller
        logger.info("Starting faculty controller...")
        faculty_controller.start()
        
        # Test a manual status update
        logger.info("Testing manual faculty status update...")
        test_data = {
            'faculty_id': 1,
            'faculty_name': 'Test Faculty',
            'present': True,
            'status': 'AVAILABLE',
            'timestamp': int(time.time()),
            'ntp_sync_status': 'SYNCED',
            'in_grace_period': False,
            'detailed_status': 'AVAILABLE'
        }
        
        # Call the handler directly
        faculty_controller.handle_faculty_status_update("consultease/faculty/1/status", test_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing faculty controller: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_database_connection():
    """Test database connection."""
    logger.info("=== Database Connection Test ===")
    
    try:
        # Import database
        from central_system.models import get_db, Faculty
        
        db = get_db()
        logger.info(f"Database connection established: {db}")
        
        # Try to query faculty
        faculty_count = db.query(Faculty).count()
        logger.info(f"Faculty count in database: {faculty_count}")
        
        # Get first faculty
        first_faculty = db.query(Faculty).first()
        if first_faculty:
            logger.info(f"First faculty: ID={first_faculty.id}, Name={first_faculty.name}, Status={first_faculty.status}")
        else:
            logger.warning("No faculty found in database")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing database: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_mqtt_subscription():
    """Test MQTT subscription mechanism."""
    logger.info("=== MQTT Subscription Test ===")
    
    try:
        from central_system.utils.mqtt_utils import subscribe_to_topic, get_mqtt_service
        
        # Test callback function
        def test_callback(topic, data):
            logger.info(f"TEST CALLBACK - Topic: {topic}, Data: {data}")
        
        # Subscribe to test topic
        success = subscribe_to_topic("test/topic", test_callback)
        logger.info(f"Subscription success: {success}")
        
        # Get MQTT service and check handlers
        mqtt_service = get_mqtt_service()
        logger.info(f"Registered handlers: {list(mqtt_service.message_handlers.keys())}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error testing MQTT subscription: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting MQTT Debug Tests...")
    
    # Test database first
    db_ok = test_database_connection()
    logger.info(f"Database test result: {db_ok}")
    
    # Test MQTT service
    mqtt_ok = test_mqtt_service()
    logger.info(f"MQTT service test result: {mqtt_ok}")
    
    # Test MQTT subscription
    sub_ok = test_mqtt_subscription()
    logger.info(f"MQTT subscription test result: {sub_ok}")
    
    # Test faculty controller
    faculty_ok = test_faculty_controller()
    logger.info(f"Faculty controller test result: {faculty_ok}")
    
    # Summary
    logger.info("=== Test Summary ===")
    logger.info(f"Database: {'✅' if db_ok else '❌'}")
    logger.info(f"MQTT Service: {'✅' if mqtt_ok else '❌'}")
    logger.info(f"MQTT Subscription: {'✅' if sub_ok else '❌'}")
    logger.info(f"Faculty Controller: {'✅' if faculty_ok else '❌'}")
    
    if all([db_ok, mqtt_ok, sub_ok, faculty_ok]):
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
