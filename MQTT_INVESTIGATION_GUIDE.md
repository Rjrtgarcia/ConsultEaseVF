# MQTT Communication Investigation Guide for ConsultEase

## Overview
This guide provides comprehensive steps to investigate and resolve MQTT communication issues between faculty desk units (ESP32) and the central ConsultEase system on Raspberry Pi.

## Problem Description
The ConsultEase central system is not receiving MQTT faculty status updates from the faculty desk units, causing the dashboard to not reflect real-time faculty availability changes.

## Investigation Tools Created

### 1. Standalone MQTT Investigation Script
**File:** `mqtt_investigation.py`
**Purpose:** Independent MQTT communication testing without ConsultEase dependencies
**Usage:**
```bash
python mqtt_investigation.py
```

### 2. ConsultEase MQTT Diagnostics Runner
**File:** `run_mqtt_diagnostics.py`
**Purpose:** Run diagnostics from within the ConsultEase environment
**Usage:**
```bash
python run_mqtt_diagnostics.py
```

### 3. MQTT Broker Status Checker
**File:** `check_mqtt_broker.py`
**Purpose:** Quick check of MQTT broker installation and status
**Usage:**
```bash
python check_mqtt_broker.py
```

## Step-by-Step Investigation Process

### Step 1: Check MQTT Broker Status
```bash
# Run the broker status checker
python check_mqtt_broker.py

# Manual checks
sudo systemctl status mosquitto
sudo systemctl start mosquitto  # if not running
sudo systemctl enable mosquitto  # to start on boot
```

### Step 2: Verify Network Connectivity
```bash
# Test network connection to MQTT broker
telnet localhost 1883
# or
nc -zv localhost 1883

# Check if broker is listening
sudo netstat -tlnp | grep 1883
```

### Step 3: Test MQTT Communication
```bash
# Terminal 1 - Subscribe to faculty topics
mosquitto_sub -h localhost -t 'consultease/faculty/+/status' -v

# Terminal 2 - Publish test message
mosquitto_pub -h localhost -t 'consultease/faculty/1/status' -m '{"present": true, "faculty_id": 1}'
```

### Step 4: Run Comprehensive Diagnostics
```bash
# Run standalone investigation
python mqtt_investigation.py

# Run ConsultEase-integrated diagnostics
python run_mqtt_diagnostics.py
```

### Step 5: Check ConsultEase MQTT Configuration

#### Current Configuration (from config.py):
- **Broker Host:** localhost (default)
- **Broker Port:** 1883 (default)
- **Username:** "" (empty - anonymous)
- **Password:** "" (empty - no authentication)

#### Environment Variable Overrides:
```bash
export MQTT_BROKER_HOST="192.168.1.100"  # if broker is on different host
export MQTT_BROKER_PORT="1883"
export MQTT_USERNAME="your_username"     # if authentication required
export MQTT_PASSWORD="your_password"     # if authentication required
```

### Step 6: Verify Faculty Desk Unit Configuration

#### Expected ESP32 MQTT Topics:
- `consultease/faculty/1/status` (primary)
- `consultease/faculty/1/mac_status` (MAC detection)
- `professor/status` (legacy compatibility)

#### ESP32 Configuration Check:
1. **MQTT Server IP:** Should match Raspberry Pi IP
2. **MQTT Port:** Should be 1883
3. **Faculty ID:** Should match database faculty ID
4. **Topic Format:** Should use `consultease/faculty/{ID}/status`

## Common Issues and Solutions

### Issue 1: MQTT Broker Not Running
**Symptoms:** Connection refused errors
**Solution:**
```bash
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

### Issue 2: Network Connectivity Problems
**Symptoms:** Cannot connect to broker IP
**Solutions:**
- Check firewall settings: `sudo ufw status`
- Verify IP address: `ip addr show`
- Test ping: `ping <broker_ip>`

### Issue 3: Wrong MQTT Topics
**Symptoms:** Messages published but not received by ConsultEase
**Solutions:**
- Verify ESP32 uses correct topic format
- Check topic subscriptions in ConsultEase logs
- Use mosquitto_sub to monitor all topics: `mosquitto_sub -h localhost -t '#' -v`

### Issue 4: Authentication Issues
**Symptoms:** Connection rejected by broker
**Solutions:**
- Check mosquitto.conf for authentication settings
- Verify username/password in both ESP32 and ConsultEase
- Test with mosquitto_pub/sub using same credentials

### Issue 5: Message Format Issues
**Symptoms:** Messages received but not processed correctly
**Solutions:**
- Check message JSON format
- Verify required fields (present, faculty_id, status)
- Review ConsultEase logs for parsing errors

## Expected Message Formats

### Faculty Status Message (ESP32 → Central System):
```json
{
  "present": true,
  "faculty_id": 1,
  "faculty_name": "Dr. John Smith",
  "timestamp": 1640995200,
  "ntp_sync_status": "SYNCED",
  "in_grace_period": false
}
```

### Legacy Format Support:
```json
{
  "status": "available",
  "faculty_id": 1
}
```

## Monitoring and Debugging

### Real-time MQTT Monitoring:
```bash
# Monitor all ConsultEase topics
mosquitto_sub -h localhost -t 'consultease/#' -v

# Monitor specific faculty
mosquitto_sub -h localhost -t 'consultease/faculty/1/status' -v

# Monitor legacy topics
mosquitto_sub -h localhost -t 'professor/status' -v
```

### ConsultEase Logs:
```bash
# View application logs
tail -f consultease.log

# View MQTT service logs
sudo journalctl -u mosquitto -f

# View system logs
sudo journalctl -f
```

## Testing Faculty Status Updates

### Manual Test from ESP32 Side:
1. Connect to ESP32 serial console
2. Look for MQTT connection messages
3. Verify status publishing messages
4. Check for any error messages

### Manual Test from Central System:
1. Run diagnostics: `python run_mqtt_diagnostics.py`
2. Publish test message: `mosquitto_pub -h localhost -t 'consultease/faculty/1/status' -m '{"present": true, "faculty_id": 1}'`
3. Check ConsultEase logs for message processing

## Verification Steps

### 1. MQTT Broker Working:
- [ ] Mosquitto service running
- [ ] Port 1883 accessible
- [ ] Can publish/subscribe with mosquitto_pub/sub

### 2. Network Communication:
- [ ] ESP32 can reach Raspberry Pi IP
- [ ] No firewall blocking port 1883
- [ ] Correct IP configuration on both sides

### 3. Topic Configuration:
- [ ] ESP32 publishing to correct topics
- [ ] ConsultEase subscribed to correct topics
- [ ] Topic patterns match (wildcards working)

### 4. Message Format:
- [ ] JSON format valid
- [ ] Required fields present
- [ ] Data types correct (boolean for present, integer for faculty_id)

### 5. ConsultEase Integration:
- [ ] MQTT service connected
- [ ] Faculty controller callbacks registered
- [ ] Dashboard real-time updates enabled

## Next Steps After Investigation

1. **Run all diagnostic scripts** to identify the specific issue
2. **Check logs** for error messages and connection attempts
3. **Verify configuration** on both ESP32 and Raspberry Pi
4. **Test step-by-step** from basic connectivity to full integration
5. **Monitor in real-time** during ESP32 status changes

## Support Files

- `mqtt_investigation.py` - Standalone MQTT testing
- `run_mqtt_diagnostics.py` - ConsultEase-integrated diagnostics  
- `check_mqtt_broker.py` - MQTT broker status checker
- `central_system/utils/mqtt_diagnostics.py` - Enhanced diagnostics module

## Contact and Further Help

If issues persist after following this guide:
1. Collect logs from all diagnostic scripts
2. Capture network traffic with tcpdump/wireshark
3. Check ESP32 serial output during connection attempts
4. Verify all configuration files match expected values
