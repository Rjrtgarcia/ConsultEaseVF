#!/usr/bin/env python3
"""
MQTT Connection Diagnostic Script

This script helps diagnose MQTT connectivity issues by testing different configurations
and providing detailed connection information.
"""

import sys
import os
import logging
import time
import socket
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mqtt_connection_diagnostic.log')
    ]
)
logger = logging.getLogger(__name__)

def check_network_connectivity():
    """Check basic network connectivity."""
    logger.info("=== Network Connectivity Check ===")
    
    # Get local IP address
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"🏠 Hostname: {hostname}")
        logger.info(f"📍 Local IP: {local_ip}")
    except Exception as e:
        logger.error(f"❌ Error getting local IP: {e}")
        return False
    
    # Test common MQTT broker addresses
    test_addresses = [
        ('localhost', 1883),
        ('127.0.0.1', 1883),
        ('192.168.1.100', 1883),
        ('172.20.10.8', 1883)
    ]
    
    reachable_brokers = []
    
    for host, port in test_addresses:
        try:
            logger.info(f"🔍 Testing connection to {host}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.info(f"✅ {host}:{port} is reachable")
                reachable_brokers.append((host, port))
            else:
                logger.warning(f"❌ {host}:{port} is not reachable")
        except Exception as e:
            logger.warning(f"❌ Error testing {host}:{port}: {e}")
    
    logger.info(f"📊 Found {len(reachable_brokers)} reachable MQTT brokers")
    return reachable_brokers

def check_mqtt_configuration():
    """Check MQTT configuration settings."""
    logger.info("=== MQTT Configuration Check ===")
    
    try:
        from central_system.utils.config_manager import get_config
        
        broker_host = get_config('mqtt.broker_host', 'localhost')
        broker_port = get_config('mqtt.broker_port', 1883)
        username = get_config('mqtt.username')
        password = get_config('mqtt.password')
        
        logger.info(f"🔧 Configured MQTT broker: {broker_host}:{broker_port}")
        logger.info(f"🔐 Authentication: {'Yes' if username else 'No'}")
        if username:
            logger.info(f"👤 Username: {username}")
            logger.info(f"🔑 Password: {'***' if password else 'Not set'}")
        
        return broker_host, broker_port, username, password
        
    except Exception as e:
        logger.error(f"❌ Error checking MQTT configuration: {e}")
        return None, None, None, None

def test_mqtt_service():
    """Test the MQTT service initialization and connection."""
    logger.info("=== MQTT Service Test ===")
    
    try:
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        
        # Get MQTT service
        mqtt_service = get_async_mqtt_service()
        logger.info(f"✅ MQTT service created: {mqtt_service}")
        logger.info(f"🏠 Broker: {mqtt_service.broker_host}:{mqtt_service.broker_port}")
        logger.info(f"🔐 Auth: {mqtt_service.username is not None}")
        
        # Check initial state
        logger.info(f"🔌 Connected: {mqtt_service.is_connected}")
        logger.info(f"🏃 Running: {mqtt_service.running}")
        
        # Start the service
        logger.info("🚀 Starting MQTT service...")
        mqtt_service.start()
        
        # Wait a bit for connection
        logger.info("⏳ Waiting for connection...")
        for i in range(10):
            time.sleep(1)
            if mqtt_service.is_connected:
                logger.info(f"✅ MQTT connected after {i+1} seconds")
                break
            logger.info(f"⏳ Still connecting... ({i+1}/10)")
        
        # Final status
        logger.info(f"🔌 Final connection status: {mqtt_service.is_connected}")
        logger.info(f"🏃 Final running status: {mqtt_service.running}")
        
        # Get stats
        stats = mqtt_service.get_stats()
        logger.info(f"📊 MQTT stats: {stats}")
        
        return mqtt_service.is_connected
        
    except Exception as e:
        logger.error(f"❌ Error testing MQTT service: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_faculty_controller_subscriptions():
    """Test faculty controller MQTT subscriptions."""
    logger.info("=== Faculty Controller Subscriptions Test ===")
    
    try:
        from central_system.controllers.faculty_controller import FacultyController
        
        # Create and start faculty controller
        faculty_controller = FacultyController()
        logger.info(f"✅ Faculty controller created: {faculty_controller}")
        
        # Start the controller (this should register MQTT subscriptions)
        logger.info("🚀 Starting faculty controller...")
        faculty_controller.start()
        
        # Check if subscriptions were registered
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        mqtt_service = get_async_mqtt_service()
        
        logger.info(f"📝 Total MQTT handlers registered: {len(mqtt_service.message_handlers)}")
        for topic, handler in mqtt_service.message_handlers.items():
            handler_name = handler.__name__ if hasattr(handler, '__name__') else str(handler)
            logger.info(f"   📌 {topic} -> {handler_name}")
        
        return len(mqtt_service.message_handlers) > 0
        
    except Exception as e:
        logger.error(f"❌ Error testing faculty controller subscriptions: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def check_environment_variables():
    """Check relevant environment variables."""
    logger.info("=== Environment Variables Check ===")
    
    env_vars = [
        'MQTT_BROKER_HOST',
        'MQTT_BROKER_PORT', 
        'MQTT_USERNAME',
        'MQTT_PASSWORD',
        'CONSULTEASE_MQTT_HOST',
        'CONSULTEASE_MQTT_PORT',
        'CONSULTEASE_MQTT_USERNAME',
        'CONSULTEASE_MQTT_PASSWORD'
    ]
    
    found_vars = {}
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            if 'PASSWORD' in var:
                logger.info(f"🔑 {var}: ***")
            else:
                logger.info(f"📝 {var}: {value}")
            found_vars[var] = value
        else:
            logger.info(f"❌ {var}: Not set")
    
    return found_vars

def main():
    """Run all diagnostics."""
    logger.info("🔍 Starting MQTT Connection Diagnostic")
    logger.info(f"⏰ Timestamp: {datetime.now()}")
    logger.info("=" * 60)
    
    # Check environment variables
    env_vars = check_environment_variables()
    
    # Check network connectivity
    reachable_brokers = check_network_connectivity()
    
    # Check MQTT configuration
    broker_host, broker_port, username, password = check_mqtt_configuration()
    
    # Test MQTT service
    mqtt_connected = test_mqtt_service()
    
    # Test faculty controller subscriptions
    subscriptions_ok = test_faculty_controller_subscriptions()
    
    # Summary
    logger.info("=" * 60)
    logger.info("🏁 DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"🌐 Network connectivity: {'✅' if reachable_brokers else '❌'}")
    logger.info(f"🔧 MQTT configuration: {'✅' if broker_host else '❌'}")
    logger.info(f"📡 MQTT service connection: {'✅' if mqtt_connected else '❌'}")
    logger.info(f"📝 Faculty subscriptions: {'✅' if subscriptions_ok else '❌'}")
    
    if reachable_brokers:
        logger.info("🔍 Reachable MQTT brokers:")
        for host, port in reachable_brokers:
            logger.info(f"   📍 {host}:{port}")
    
    # Recommendations
    logger.info("=" * 60)
    logger.info("💡 RECOMMENDATIONS")
    logger.info("=" * 60)
    
    if not reachable_brokers:
        logger.info("❌ No MQTT brokers are reachable!")
        logger.info("   🔧 Install and start an MQTT broker (e.g., mosquitto)")
        logger.info("   🔧 Check firewall settings")
        logger.info("   🔧 Verify network configuration")
    
    if broker_host and not mqtt_connected:
        logger.info(f"❌ MQTT service cannot connect to {broker_host}:{broker_port}")
        logger.info("   🔧 Check if MQTT broker is running")
        logger.info("   🔧 Verify broker address and port")
        logger.info("   🔧 Check authentication credentials")
    
    if not subscriptions_ok:
        logger.info("❌ Faculty controller subscriptions failed")
        logger.info("   🔧 Check faculty controller initialization")
        logger.info("   🔧 Verify MQTT service is running")
    
    # Overall status
    all_ok = reachable_brokers and mqtt_connected and subscriptions_ok
    status = "ALL SYSTEMS OPERATIONAL" if all_ok else "ISSUES DETECTED"
    icon = "🎉" if all_ok else "⚠️"
    
    logger.info("=" * 60)
    logger.info(f"{icon} OVERALL STATUS: {status}")
    logger.info("=" * 60)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
