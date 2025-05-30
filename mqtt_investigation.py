#!/usr/bin/env python3
"""
MQTT Communication Investigation Script for ConsultEase
Standalone script to diagnose MQTT communication issues between faculty desk units and central system.
"""

import sys
import os
import time
import json
import logging
import socket
import threading
from datetime import datetime
import paho.mqtt.client as mqtt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mqtt_investigation.log')
    ]
)
logger = logging.getLogger(__name__)


class MQTTInvestigator:
    """Comprehensive MQTT communication investigator."""
    
    def __init__(self):
        self.received_messages = []
        self.connection_attempts = 0
        self.connection_successful = False
        self.broker_host = 'localhost'
        self.broker_port = 1883
        self.client = None
        self.monitoring = False
        
    def investigate_mqtt_communication(self):
        """Run comprehensive MQTT communication investigation."""
        logger.info("🔍 Starting MQTT Communication Investigation")
        logger.info("=" * 60)
        
        # Step 1: Check network connectivity
        self._check_network_connectivity()
        
        # Step 2: Test MQTT broker connection
        self._test_mqtt_broker_connection()
        
        # Step 3: Test topic subscriptions
        self._test_topic_subscriptions()
        
        # Step 4: Monitor for faculty messages
        self._monitor_faculty_messages()
        
        # Step 5: Test message publishing
        self._test_message_publishing()
        
        # Step 6: Generate investigation report
        self._generate_investigation_report()
        
    def _check_network_connectivity(self):
        """Check network connectivity to MQTT broker."""
        logger.info("🌐 Checking network connectivity...")
        
        # Test different possible broker addresses
        possible_hosts = [
            'localhost',
            '127.0.0.1',
            '192.168.1.100',  # Common Pi address
            '172.20.10.8',    # From config templates
            '192.168.1.1',    # Router address
        ]
        
        for host in possible_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, self.broker_port))
                sock.close()
                
                if result == 0:
                    logger.info(f"✅ Network connection successful to {host}:{self.broker_port}")
                    self.broker_host = host
                    return True
                else:
                    logger.warning(f"❌ Cannot connect to {host}:{self.broker_port}")
                    
            except Exception as e:
                logger.warning(f"❌ Network test failed for {host}: {e}")
                
        logger.error("❌ No MQTT broker found on any tested address")
        return False
        
    def _test_mqtt_broker_connection(self):
        """Test MQTT broker connection."""
        logger.info(f"🔌 Testing MQTT broker connection to {self.broker_host}:{self.broker_port}...")
        
        try:
            self.client = mqtt.Client("mqtt_investigator")
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Attempt connection
            self.connection_attempts += 1
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connection_successful and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            if self.connection_successful:
                logger.info("✅ MQTT broker connection successful")
                return True
            else:
                logger.error("❌ MQTT broker connection failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT connection error: {e}")
            return False
            
    def _test_topic_subscriptions(self):
        """Test MQTT topic subscriptions."""
        logger.info("📡 Testing MQTT topic subscriptions...")
        
        if not self.connection_successful:
            logger.error("❌ Cannot test subscriptions - not connected to broker")
            return False
            
        # Faculty status topics to test
        test_topics = [
            "consultease/faculty/+/status",
            "consultease/faculty/+/mac_status", 
            "consultease/faculty/1/status",
            "faculty/+/status",
            "faculty/1/status",
            "professor/status",
            "professor/messages"
        ]
        
        for topic in test_topics:
            try:
                result = self.client.subscribe(topic, 1)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"✅ Subscribed to {topic}")
                else:
                    logger.error(f"❌ Failed to subscribe to {topic}: {result}")
            except Exception as e:
                logger.error(f"❌ Subscription error for {topic}: {e}")
                
        return True
        
    def _monitor_faculty_messages(self):
        """Monitor for faculty status messages."""
        logger.info("👂 Monitoring for faculty status messages...")
        logger.info("⏰ Listening for 30 seconds...")
        
        if not self.connection_successful:
            logger.error("❌ Cannot monitor - not connected to broker")
            return
            
        self.monitoring = True
        start_time = time.time()
        
        # Monitor for 30 seconds
        while time.time() - start_time < 30 and self.monitoring:
            time.sleep(1)
            
        self.monitoring = False
        logger.info(f"📊 Monitoring complete. Received {len(self.received_messages)} messages")
        
    def _test_message_publishing(self):
        """Test publishing messages to faculty topics."""
        logger.info("📤 Testing message publishing...")
        
        if not self.connection_successful:
            logger.error("❌ Cannot test publishing - not connected to broker")
            return
            
        # Test publishing to faculty status topic
        test_topic = "consultease/faculty/1/status"
        test_message = {
            "type": "test_message",
            "timestamp": time.time(),
            "source": "mqtt_investigator",
            "present": True,
            "faculty_id": 1
        }
        
        try:
            result = self.client.publish(test_topic, json.dumps(test_message), 1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Test message published to {test_topic}")
            else:
                logger.error(f"❌ Failed to publish test message: {result.rc}")
        except Exception as e:
            logger.error(f"❌ Publishing error: {e}")
            
    def _generate_investigation_report(self):
        """Generate comprehensive investigation report."""
        logger.info("📋 Generating investigation report...")
        
        print("\n" + "=" * 80)
        print("🔍 MQTT COMMUNICATION INVESTIGATION REPORT")
        print("=" * 80)
        print(f"📅 Investigation time: {datetime.now().isoformat()}")
        print(f"🔌 Broker: {self.broker_host}:{self.broker_port}")
        print(f"🔗 Connection attempts: {self.connection_attempts}")
        print(f"✅ Connection successful: {self.connection_successful}")
        print(f"📨 Messages received: {len(self.received_messages)}")
        print()
        
        # Show received messages
        if self.received_messages:
            print("📨 RECEIVED MESSAGES:")
            for i, msg in enumerate(self.received_messages[-10:], 1):  # Show last 10
                print(f"  {i}. Topic: {msg['topic']}")
                print(f"     Time: {msg['timestamp']}")
                print(f"     Data: {msg['payload']}")
                print()
        else:
            print("⚠️ NO MESSAGES RECEIVED")
            print()
            print("💡 POSSIBLE CAUSES:")
            print("  1. ESP32 faculty desk units are not connected")
            print("  2. ESP32 units are not publishing messages")
            print("  3. ESP32 units are using different MQTT topics")
            print("  4. ESP32 units are connected to different MQTT broker")
            print("  5. Network connectivity issues")
            print()
            
        # Recommendations
        print("🔧 TROUBLESHOOTING STEPS:")
        print("  1. Check if MQTT broker (mosquitto) is running:")
        print("     sudo systemctl status mosquitto")
        print("  2. Check MQTT broker logs:")
        print("     sudo journalctl -u mosquitto -f")
        print("  3. Test MQTT broker with mosquitto clients:")
        print("     mosquitto_sub -h localhost -t 'consultease/faculty/+/status'")
        print("  4. Check ESP32 serial output for connection status")
        print("  5. Verify ESP32 MQTT configuration matches broker settings")
        print("=" * 80)
        
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            self.connection_successful = True
            logger.info(f"✅ Connected to MQTT broker with result code {rc}")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker with result code {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        logger.info(f"🔌 Disconnected from MQTT broker with result code {rc}")
        self.connection_successful = False
        
    def _on_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            payload = msg.payload.decode('utf-8')
            timestamp = datetime.now().isoformat()
            
            message_info = {
                'topic': msg.topic,
                'payload': payload,
                'timestamp': timestamp,
                'qos': msg.qos
            }
            
            self.received_messages.append(message_info)
            
            logger.info(f"📨 MQTT Message received:")
            logger.info(f"  📍 Topic: {msg.topic}")
            logger.info(f"  📄 Payload: {payload}")
            logger.info(f"  🏷️ QoS: {msg.qos}")
            
            # Try to parse as JSON
            try:
                data = json.loads(payload)
                logger.info(f"  📊 Parsed JSON: {data}")
            except json.JSONDecodeError:
                logger.info(f"  📝 Raw string data: {payload}")
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")


def main():
    """Main investigation function."""
    print("🔍 MQTT Communication Investigation for ConsultEase")
    print("This script will test MQTT communication between faculty desk units and central system")
    print()
    
    investigator = MQTTInvestigator()
    
    try:
        investigator.investigate_mqtt_communication()
    except KeyboardInterrupt:
        logger.info("🛑 Investigation interrupted by user")
    except Exception as e:
        logger.error(f"❌ Investigation error: {e}")
    finally:
        if investigator.client:
            investigator.client.loop_stop()
            investigator.client.disconnect()
            
    print("\n🔍 Investigation complete. Check mqtt_investigation.log for detailed logs.")


if __name__ == "__main__":
    main()
