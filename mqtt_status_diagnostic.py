#!/usr/bin/env python3
"""
MQTT Status Diagnostic Script for ConsultEase Faculty Status Issues

This script helps diagnose MQTT connectivity and faculty status update issues.
Run this script to check if MQTT services are working properly.
"""

import sys
import os
import logging
import time
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mqtt_diagnostic.log')
    ]
)
logger = logging.getLogger(__name__)

def check_mqtt_service():
    """Check MQTT service status and connectivity."""
    logger.info("=== MQTT Service Diagnostic ===")
    
    try:
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        mqtt_service = get_async_mqtt_service()
        
        logger.info(f"✅ MQTT Service instance: {mqtt_service}")
        logger.info(f"📡 MQTT Connected: {mqtt_service.is_connected}")
        logger.info(f"🏃 MQTT Running: {mqtt_service.running}")
        logger.info(f"🏠 MQTT Broker: {mqtt_service.broker_host}:{mqtt_service.broker_port}")
        
        # Get service statistics
        stats = mqtt_service.get_stats()
        logger.info(f"📊 MQTT Stats: {stats}")
        
        # Check message handlers
        handlers = mqtt_service.message_handlers
        logger.info(f"🔧 Registered handlers: {len(handlers)} topics")
        for topic, handler in handlers.items():
            logger.info(f"   📝 {topic} -> {handler.__name__ if hasattr(handler, '__name__') else str(handler)}")
        
        return mqtt_service.is_connected
        
    except Exception as e:
        logger.error(f"❌ Error checking MQTT service: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def check_faculty_controller():
    """Check faculty controller status and subscriptions."""
    logger.info("=== Faculty Controller Diagnostic ===")
    
    try:
        from central_system.controllers.faculty_controller import FacultyController
        
        # Create faculty controller instance
        faculty_controller = FacultyController()
        logger.info(f"✅ Faculty Controller instance: {faculty_controller}")
        
        # Check attributes
        has_callbacks = hasattr(faculty_controller, 'callbacks')
        has_queue_service = hasattr(faculty_controller, 'queue_service')
        
        logger.info(f"📞 Has callbacks: {has_callbacks}")
        logger.info(f"🔄 Has queue service: {has_queue_service}")
        
        if has_callbacks:
            logger.info(f"📞 Callback count: {len(faculty_controller.callbacks)}")
        
        # Start the controller to register MQTT subscriptions
        logger.info("🚀 Starting faculty controller...")
        faculty_controller.start()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking faculty controller: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def check_database():
    """Check database connectivity and faculty data."""
    logger.info("=== Database Diagnostic ===")
    
    try:
        from central_system.models import get_db, Faculty
        
        db = get_db()
        logger.info(f"✅ Database connection: {db}")
        
        # Count faculty
        faculty_count = db.query(Faculty).count()
        logger.info(f"👥 Total faculty: {faculty_count}")
        
        # Get faculty with status
        available_faculty = db.query(Faculty).filter(Faculty.status == True).count()
        unavailable_faculty = db.query(Faculty).filter(Faculty.status == False).count()
        
        logger.info(f"✅ Available faculty: {available_faculty}")
        logger.info(f"❌ Unavailable faculty: {unavailable_faculty}")
        
        # Show first few faculty
        faculty_list = db.query(Faculty).limit(5).all()
        for faculty in faculty_list:
            status_icon = "✅" if faculty.status else "❌"
            logger.info(f"   {status_icon} {faculty.name} (ID: {faculty.id}) - {faculty.department}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking database: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def simulate_faculty_status_update():
    """Simulate a faculty status update to test the pipeline."""
    logger.info("=== Faculty Status Update Simulation ===")
    
    try:
        from central_system.controllers.faculty_controller import FacultyController
        
        faculty_controller = FacultyController()
        faculty_controller.start()
        
        # Simulate MQTT message data
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
        
        logger.info(f"📤 Simulating MQTT message: {test_data}")
        
        # Call the handler directly
        faculty_controller.handle_faculty_status_update("consultease/faculty/1/status", test_data)
        
        logger.info("✅ Faculty status update simulation completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error simulating faculty status update: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def check_system_coordinator():
    """Check system coordinator status."""
    logger.info("=== System Coordinator Diagnostic ===")
    
    try:
        from central_system.services.system_coordinator import get_system_coordinator
        
        coordinator = get_system_coordinator()
        logger.info(f"✅ System Coordinator: {coordinator}")
        logger.info(f"🏃 Is Running: {coordinator.is_running}")
        
        # Check services
        services = coordinator.services
        logger.info(f"🔧 Registered services: {len(services)}")
        
        for service_name, service in services.items():
            status_icon = "✅" if service.state.name == "RUNNING" else "❌"
            logger.info(f"   {status_icon} {service_name}: {service.state.name}")
        
        return coordinator.is_running
        
    except Exception as e:
        logger.error(f"❌ Error checking system coordinator: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all diagnostics."""
    logger.info("🔍 Starting ConsultEase MQTT Status Diagnostic")
    logger.info(f"⏰ Timestamp: {datetime.now()}")
    logger.info("=" * 60)
    
    # Run diagnostics
    results = {}
    
    results['system_coordinator'] = check_system_coordinator()
    results['database'] = check_database()
    results['mqtt_service'] = check_mqtt_service()
    results['faculty_controller'] = check_faculty_controller()
    results['status_simulation'] = simulate_faculty_status_update()
    
    # Summary
    logger.info("=" * 60)
    logger.info("🏁 DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)
    
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"{status_icon} {component.replace('_', ' ').title()}: {'PASS' if status else 'FAIL'}")
    
    # Overall status
    all_passed = all(results.values())
    overall_icon = "🎉" if all_passed else "⚠️"
    overall_status = "ALL SYSTEMS OPERATIONAL" if all_passed else "ISSUES DETECTED"
    
    logger.info("=" * 60)
    logger.info(f"{overall_icon} OVERALL STATUS: {overall_status}")
    logger.info("=" * 60)
    
    if not all_passed:
        logger.info("🔧 TROUBLESHOOTING RECOMMENDATIONS:")
        if not results['system_coordinator']:
            logger.info("   - Check system coordinator startup logs")
        if not results['database']:
            logger.info("   - Verify database connection and faculty data")
        if not results['mqtt_service']:
            logger.info("   - Check MQTT broker connectivity")
            logger.info("   - Verify MQTT service configuration")
        if not results['faculty_controller']:
            logger.info("   - Check faculty controller initialization")
        if not results['status_simulation']:
            logger.info("   - Check faculty status update pipeline")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
