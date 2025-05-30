#!/usr/bin/env python3
"""
MQTT Broker Status Checker for ConsultEase
Quick script to check if MQTT broker is running and accessible.
"""

import socket
import subprocess
import sys
import time
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_mqtt_broker_service():
    """Check if MQTT broker service is running."""
    logger.info("🔍 Checking MQTT broker service status...")
    
    try:
        # Check mosquitto service status
        result = subprocess.run(['systemctl', 'is-active', 'mosquitto'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip() == 'active':
            logger.info("✅ Mosquitto MQTT broker service is running")
            return True
        else:
            logger.warning("⚠️ Mosquitto MQTT broker service is not active")
            
            # Try to get more details
            status_result = subprocess.run(['systemctl', 'status', 'mosquitto'], 
                                         capture_output=True, text=True)
            logger.info(f"Service status: {status_result.stdout}")
            return False
            
    except FileNotFoundError:
        logger.warning("⚠️ systemctl not found - cannot check service status")
        return None
    except Exception as e:
        logger.error(f"❌ Error checking service status: {e}")
        return None


def check_mqtt_broker_connectivity():
    """Check MQTT broker network connectivity."""
    logger.info("🌐 Checking MQTT broker connectivity...")
    
    # Common MQTT broker addresses to test
    test_addresses = [
        ('localhost', 1883),
        ('127.0.0.1', 1883),
        ('192.168.1.100', 1883),  # Common Pi address
        ('172.20.10.8', 1883),    # From config templates
    ]
    
    accessible_brokers = []
    
    for host, port in test_addresses:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.info(f"✅ MQTT broker accessible at {host}:{port}")
                accessible_brokers.append((host, port))
            else:
                logger.info(f"❌ Cannot connect to {host}:{port}")
                
        except Exception as e:
            logger.info(f"❌ Error testing {host}:{port}: {e}")
            
    return accessible_brokers


def test_mqtt_with_paho():
    """Test MQTT connection using paho-mqtt client."""
    logger.info("📡 Testing MQTT connection with paho-mqtt...")
    
    try:
        import paho.mqtt.client as mqtt
        
        # Test connection to localhost
        client = mqtt.Client("mqtt_broker_checker")
        connection_result = {'connected': False, 'error': None}
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                connection_result['connected'] = True
                logger.info("✅ MQTT connection successful")
            else:
                connection_result['error'] = f"Connection failed with code {rc}"
                logger.error(f"❌ MQTT connection failed: {rc}")
                
        def on_disconnect(client, userdata, rc):
            logger.info(f"🔌 Disconnected from MQTT broker: {rc}")
            
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        
        # Try to connect
        client.connect("localhost", 1883, 10)
        client.loop_start()
        
        # Wait for connection result
        timeout = 10
        start_time = time.time()
        while time.time() - start_time < timeout:
            if connection_result['connected'] or connection_result['error']:
                break
            time.sleep(0.1)
            
        client.loop_stop()
        client.disconnect()
        
        return connection_result['connected']
        
    except ImportError:
        logger.warning("⚠️ paho-mqtt not installed - cannot test MQTT connection")
        logger.info("Install with: pip install paho-mqtt")
        return None
    except Exception as e:
        logger.error(f"❌ Error testing MQTT connection: {e}")
        return False


def check_mqtt_configuration():
    """Check MQTT configuration files."""
    logger.info("📋 Checking MQTT configuration...")
    
    # Common mosquitto config locations
    config_paths = [
        '/etc/mosquitto/mosquitto.conf',
        '/usr/local/etc/mosquitto/mosquitto.conf',
        '/opt/homebrew/etc/mosquitto/mosquitto.conf'
    ]
    
    for config_path in config_paths:
        try:
            with open(config_path, 'r') as f:
                config_content = f.read()
                logger.info(f"✅ Found mosquitto config at {config_path}")
                
                # Check for important settings
                if 'listener 1883' in config_content or 'port 1883' in config_content:
                    logger.info("  📡 Port 1883 configured")
                if 'allow_anonymous true' in config_content:
                    logger.info("  🔓 Anonymous access allowed")
                elif 'allow_anonymous false' in config_content:
                    logger.info("  🔒 Authentication required")
                    
                return True
                
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.warning(f"⚠️ Error reading {config_path}: {e}")
            
    logger.warning("⚠️ No mosquitto configuration file found")
    return False


def check_mqtt_logs():
    """Check MQTT broker logs."""
    logger.info("📝 Checking MQTT broker logs...")
    
    try:
        # Get recent mosquitto logs
        result = subprocess.run(['journalctl', '-u', 'mosquitto', '--no-pager', '-n', '20'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("📋 Recent mosquitto logs:")
            for line in result.stdout.split('\n')[-10:]:  # Show last 10 lines
                if line.strip():
                    logger.info(f"  {line}")
        else:
            logger.warning("⚠️ Could not retrieve mosquitto logs")
            
    except FileNotFoundError:
        logger.warning("⚠️ journalctl not found - cannot check logs")
    except Exception as e:
        logger.error(f"❌ Error checking logs: {e}")


def install_mosquitto_if_missing():
    """Suggest installing mosquitto if it's missing."""
    logger.info("🔧 Checking if mosquitto is installed...")
    
    try:
        result = subprocess.run(['which', 'mosquitto'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Mosquitto is installed")
            return True
        else:
            logger.warning("⚠️ Mosquitto is not installed")
            logger.info("📦 To install mosquitto:")
            logger.info("  Ubuntu/Debian: sudo apt-get install mosquitto mosquitto-clients")
            logger.info("  CentOS/RHEL: sudo yum install mosquitto mosquitto-clients")
            logger.info("  macOS: brew install mosquitto")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking mosquitto installation: {e}")
        return False


def main():
    """Main function to run all checks."""
    print("🔍 MQTT Broker Status Checker for ConsultEase")
    print("=" * 50)
    
    results = {}
    
    # Check 1: Mosquitto installation
    results['installed'] = install_mosquitto_if_missing()
    
    # Check 2: Service status
    results['service_running'] = check_mqtt_broker_service()
    
    # Check 3: Network connectivity
    accessible_brokers = check_mqtt_broker_connectivity()
    results['network_accessible'] = len(accessible_brokers) > 0
    
    # Check 4: MQTT client connection
    results['mqtt_connection'] = test_mqtt_with_paho()
    
    # Check 5: Configuration
    results['config_found'] = check_mqtt_configuration()
    
    # Check 6: Logs
    check_mqtt_logs()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 MQTT BROKER STATUS SUMMARY")
    print("=" * 50)
    
    for check, result in results.items():
        if result is True:
            status = "✅ OK"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️ UNKNOWN"
            
        print(f"{check.replace('_', ' ').title()}: {status}")
        
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    if not results.get('installed'):
        print("  1. Install mosquitto MQTT broker")
        print("  2. Start the mosquitto service")
    elif not results.get('service_running'):
        print("  1. Start mosquitto service: sudo systemctl start mosquitto")
        print("  2. Enable mosquitto service: sudo systemctl enable mosquitto")
    elif not results.get('network_accessible'):
        print("  1. Check mosquitto configuration")
        print("  2. Check firewall settings")
        print("  3. Verify mosquitto is listening on port 1883")
    elif not results.get('mqtt_connection'):
        print("  1. Check mosquitto authentication settings")
        print("  2. Check mosquitto access control")
    else:
        print("  ✅ MQTT broker appears to be working correctly!")
        
    print("\n🔧 TROUBLESHOOTING COMMANDS:")
    print("  Check service: sudo systemctl status mosquitto")
    print("  Start service: sudo systemctl start mosquitto")
    print("  View logs: sudo journalctl -u mosquitto -f")
    print("  Test subscribe: mosquitto_sub -h localhost -t 'test/topic'")
    print("  Test publish: mosquitto_pub -h localhost -t 'test/topic' -m 'hello'")


if __name__ == "__main__":
    main()
