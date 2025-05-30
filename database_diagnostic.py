#!/usr/bin/env python3
"""
Database Diagnostic Script for ConsultEase Central System
Run this on your Raspberry Pi to check database health and connectivity.
"""

import sys
import os
import logging
import time
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connection."""
    logger.info("=== Testing Database Connection ===")

    try:
        from central_system.models.base import get_db

        # Test basic connection
        db = get_db()
        logger.info("✅ Database connection established successfully")

        # Test a simple query
        result = db.execute("SELECT 1 as test").fetchone()
        if result and result[0] == 1:
            logger.info("✅ Database query test successful")
        else:
            logger.error("❌ Database query test failed")
            return False

        db.close()
        return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def test_database_manager():
    """Test the database manager health."""
    logger.info("=== Testing Database Manager ===")

    try:
        from central_system.services.database_manager import get_database_manager

        db_manager = get_database_manager()
        logger.info("✅ Database manager initialized")

        # Get health status
        health_status = db_manager.get_health_status()
        logger.info(f"🏥 Database health status: {health_status}")

        # Test session creation
        with db_manager.get_session_context() as session:
            result = session.execute("SELECT 1 as test").fetchone()
            if result and result[0] == 1:
                logger.info("✅ Database manager session test successful")
                return True
            else:
                logger.error("❌ Database manager session test failed")
                return False

    except Exception as e:
        logger.error(f"❌ Database manager test failed: {e}")
        return False

def test_faculty_model():
    """Test Faculty model operations."""
    logger.info("=== Testing Faculty Model ===")

    try:
        from central_system.models.faculty import Faculty
        from central_system.models.base import get_db

        db = get_db()

        # Test faculty query
        faculties = db.query(Faculty).all()
        logger.info(f"✅ Found {len(faculties)} faculty members in database")

        for faculty in faculties:
            logger.info(f"   👤 Faculty: {faculty.name} (ID: {faculty.id}, Status: {faculty.status})")

        db.close()
        return True

    except Exception as e:
        logger.error(f"❌ Faculty model test failed: {e}")
        return False

def test_faculty_controller():
    """Test Faculty controller functionality."""
    logger.info("=== Testing Faculty Controller ===")

    try:
        from central_system.controllers.faculty_controller import FacultyController

        controller = FacultyController()
        logger.info("✅ Faculty controller initialized")

        # Test getting all faculty
        faculties = controller.get_all_faculty()
        logger.info(f"✅ Faculty controller returned {len(faculties)} faculty members")

        return True

    except Exception as e:
        logger.error(f"❌ Faculty controller test failed: {e}")
        return False

def test_mqtt_faculty_update():
    """Test MQTT faculty status update simulation."""
    logger.info("=== Testing MQTT Faculty Update ===")

    try:
        from central_system.controllers.faculty_controller import FacultyController

        controller = FacultyController()

        # Simulate MQTT message data (like from your ESP32)
        test_data = {
            'faculty_id': 1,
            'faculty_name': 'Dave Jomillo',
            'present': True,
            'status': 'AVAILABLE',
            'timestamp': int(time.time()),
            'ntp_sync_status': 'SYNCED',
            'in_grace_period': False,
            'detailed_status': 'AVAILABLE'
        }

        logger.info(f"📤 Simulating MQTT message: {test_data}")

        # Call the handler directly
        controller.handle_faculty_status_update("consultease/faculty/1/status", test_data)

        logger.info("✅ MQTT faculty status update simulation completed")

        # Test the opposite status to verify both directions work
        test_data_false = test_data.copy()
        test_data_false['present'] = False
        test_data_false['status'] = 'AWAY'

        logger.info(f"📤 Simulating MQTT message (away): {test_data_false}")
        controller.handle_faculty_status_update("consultease/faculty/1/status", test_data_false)

        logger.info("✅ MQTT faculty status update (both directions) completed")
        return True

    except Exception as e:
        logger.error(f"❌ MQTT faculty update test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_system_coordinator():
    """Test system coordinator database health check."""
    logger.info("=== Testing System Coordinator ===")

    try:
        from central_system.services.system_coordinator import get_system_coordinator

        coordinator = get_system_coordinator()
        logger.info(f"✅ System coordinator running: {coordinator.is_running}")

        # Check services
        services = coordinator.services
        logger.info(f"🔧 Registered services: {len(services)}")

        for service_name, service in services.items():
            status_icon = "✅" if service.state.name == "RUNNING" else "❌"
            logger.info(f"   {status_icon} {service_name}: {service.state.name}")

            if service_name == "database":
                logger.info(f"      📊 Error count: {service.error_count}")
                logger.info(f"      🔄 Restart count: {service.restart_count}")
                logger.info(f"      ⏰ Last health check: {service.last_health_check}")

        return True

    except Exception as e:
        logger.error(f"❌ System coordinator test failed: {e}")
        return False

def main():
    """Run all database diagnostics."""
    logger.info("🔍 Starting Database Diagnostic for ConsultEase Central System")
    logger.info(f"⏰ Timestamp: {datetime.now()}")
    logger.info("=" * 60)

    tests = [
        ("Database Connection", test_database_connection),
        ("Database Manager", test_database_manager),
        ("Faculty Model", test_faculty_model),
        ("Faculty Controller", test_faculty_controller),
        ("MQTT Faculty Update", test_mqtt_faculty_update),
        ("System Coordinator", test_system_coordinator),
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info("")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("🏁 DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
        if result:
            passed += 1

    logger.info("")
    logger.info(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! Database is healthy.")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Check the logs above for details.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
