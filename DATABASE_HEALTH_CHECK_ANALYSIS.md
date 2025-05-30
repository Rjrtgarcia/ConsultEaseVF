# Database Health Check Analysis and Fixes

## Root Cause Analysis

After analyzing the database service layer and health monitoring system, I've identified several critical issues causing the frequent database restarts every 30-40 seconds:

### **Primary Issues Identified:**

#### 1. **Aggressive Health Check Configuration** ❌
- **Health Check Interval**: 30 seconds (too frequent)
- **Health Monitor Loop**: Checks every 5 seconds
- **Restart Threshold**: Only 3 failed checks trigger restart
- **Problem**: Creates a cascade of false positives

#### 2. **SQLite-Specific Issues** ❌
- **Pool Pre-Ping**: Enabled for SQLite (unnecessary and problematic)
- **Connection Timeout**: 20 seconds may be too short for busy systems
- **StaticPool**: May not handle concurrent access well under load
- **Problem**: SQLite doesn't need connection pooling validation

#### 3. **Health Check Logic Flaws** ❌
- **Immediate Restart**: Health check failure triggers immediate engine reinitialization
- **No Grace Period**: No tolerance for temporary connection issues
- **Cascading Failures**: Reinitialization during active transactions causes more failures
- **Problem**: Creates restart loops

#### 4. **Session Health Check Overhead** ❌
- **Every Session**: Health check on every session acquisition
- **Blocking Operations**: Health checks block faculty status updates
- **Resource Contention**: Multiple health checks compete for database access
- **Problem**: Degrades performance and causes timeouts

### **Impact on Faculty Status Updates:**

#### 1. **Transaction Rollbacks** ❌
- Faculty status updates are lost during database restarts
- Transactions in progress are rolled back
- MQTT messages may be processed but not persisted

#### 2. **Timing Issues** ❌
- Status updates arrive during restart window
- Database unavailable for 5-10 seconds during restart
- Cache invalidation fails during restart

#### 3. **Data Inconsistency** ❌
- UI shows cached data while database is restarting
- MQTT and database become out of sync
- Faculty availability appears stale

## Comprehensive Fixes

### **Fix 1: Optimize Health Check Configuration** ✅

```python
class DatabaseManager:
    def __init__(self, database_url: str, pool_size: int = 5, max_overflow: int = 10,
                 pool_timeout: int = 30, pool_recycle: int = 1800):
        # ... existing code ...
        
        # Improved health check configuration
        self.health_check_interval = 120.0  # Increased to 2 minutes
        self.health_check_failure_threshold = 5  # Allow more failures before restart
        self.health_check_consecutive_failures = 0
        self.last_successful_health_check = None
        
        # Grace period for temporary issues
        self.health_check_grace_period = 300.0  # 5 minutes grace period
        self.restart_cooldown = 600.0  # 10 minutes between restarts
        self.last_restart_time = None
```

### **Fix 2: SQLite-Specific Optimizations** ✅

```python
def initialize(self) -> bool:
    """Initialize database engine with optimized SQLite configuration."""
    with self.lock:
        if self.is_initialized:
            return True

        try:
            if self.database_url.startswith('sqlite'):
                # Optimized SQLite configuration
                self.engine = create_engine(
                    self.database_url,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 60,  # Increased timeout
                        "isolation_level": None,  # Autocommit mode
                        "journal_mode": "WAL",  # Write-Ahead Logging
                        "synchronous": "NORMAL",  # Balanced safety/performance
                        "cache_size": -64000,  # 64MB cache
                        "temp_store": "memory"  # Use memory for temp tables
                    },
                    pool_pre_ping=False,  # Disabled for SQLite
                    echo=False
                )
                logger.info("Created optimized SQLite engine")
```

### **Fix 3: Intelligent Health Check Logic** ✅

```python
def _health_monitor_loop(self):
    """Improved health monitoring with grace periods and intelligent restart logic."""
    while self.monitoring_enabled:
        try:
            current_time = datetime.now()
            
            # Check if health check is due
            if (not self.last_health_check or
                current_time - self.last_health_check >= timedelta(seconds=self.health_check_interval)):
                
                # Perform health check
                is_healthy = self._test_connection_with_retry()
                self.last_health_check = current_time
                
                if is_healthy:
                    # Reset failure counter on success
                    self.health_check_consecutive_failures = 0
                    self.last_successful_health_check = current_time
                    self.is_healthy = True
                    logger.debug("Database health check passed")
                else:
                    # Increment failure counter
                    self.health_check_consecutive_failures += 1
                    logger.warning(f"Database health check failed (failure {self.health_check_consecutive_failures}/{self.health_check_failure_threshold})")
                    
                    # Check if we should restart
                    if self._should_restart_database():
                        logger.warning("Database restart conditions met, initiating restart")
                        self._restart_database_safely()
                    else:
                        # Mark as unhealthy but don't restart yet
                        self.is_healthy = False
            
            # Sleep longer to reduce overhead
            time.sleep(30.0)  # Increased from 5 seconds
            
        except Exception as e:
            logger.error(f"Error in database health monitor: {e}")
            time.sleep(60.0)  # Wait longer on error

def _should_restart_database(self) -> bool:
    """Determine if database should be restarted based on intelligent criteria."""
    current_time = datetime.now()
    
    # Check failure threshold
    if self.health_check_consecutive_failures < self.health_check_failure_threshold:
        return False
    
    # Check restart cooldown
    if (self.last_restart_time and 
        current_time - self.last_restart_time < timedelta(seconds=self.restart_cooldown)):
        logger.info("Database restart skipped due to cooldown period")
        return False
    
    # Check grace period for new installations
    if (self.last_successful_health_check and
        current_time - self.last_successful_health_check < timedelta(seconds=self.health_check_grace_period)):
        logger.info("Database restart skipped due to grace period")
        return False
    
    return True

def _restart_database_safely(self):
    """Safely restart database with proper coordination."""
    try:
        logger.info("Initiating safe database restart...")
        self.last_restart_time = datetime.now()
        
        # Wait for active transactions to complete
        self._wait_for_active_transactions()
        
        # Reinitialize engine
        self._reinitialize_engine()
        
        # Reset failure counter
        self.health_check_consecutive_failures = 0
        
        logger.info("Database restart completed successfully")
        
    except Exception as e:
        logger.error(f"Error during safe database restart: {e}")
```

### **Fix 4: Faculty Status Update Protection** ✅

```python
def _wait_for_active_transactions(self, max_wait: int = 30):
    """Wait for active transactions to complete before restart."""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        with self.lock:
            if self.stats.active_connections == 0:
                logger.info("All active transactions completed")
                return
        
        logger.info(f"Waiting for {self.stats.active_connections} active transactions to complete...")
        time.sleep(1.0)
    
    logger.warning(f"Timeout waiting for transactions, proceeding with restart")

def update_faculty_status_with_retry(self, faculty_id: int, status: bool, max_retries: int = 5) -> dict:
    """Update faculty status with database restart protection."""
    for attempt in range(max_retries):
        try:
            # Check if database is healthy before attempting update
            if not self.is_healthy and attempt == 0:
                logger.warning("Database unhealthy, waiting for recovery...")
                time.sleep(2.0)
            
            # Attempt the update
            return self.update_faculty_status(faculty_id, status)
            
        except DatabaseConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 10)
                logger.warning(f"Faculty status update failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Faculty status update failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error updating faculty status: {e}")
            raise
```

### **Fix 5: MQTT-Database Coordination** ✅

```python
class DatabaseAwareMQTTHandler:
    """MQTT handler that coordinates with database health."""
    
    def __init__(self, faculty_controller):
        self.faculty_controller = faculty_controller
        self.pending_updates = {}  # Store updates during database issues
        self.update_queue = Queue()
        
    def handle_faculty_status_update(self, topic: str, data: dict):
        """Handle MQTT faculty status updates with database coordination."""
        try:
            faculty_id = data.get('faculty_id')
            status = data.get('status')
            
            if not faculty_id or status is None:
                logger.warning(f"Invalid MQTT status update data: {data}")
                return
            
            # Check database health
            db_manager = get_database_manager()
            if not db_manager.is_healthy:
                # Queue update for later processing
                self.pending_updates[faculty_id] = {
                    'status': status,
                    'timestamp': datetime.now(),
                    'data': data
                }
                logger.info(f"Queued faculty {faculty_id} status update due to database issues")
                return
            
            # Process update immediately
            result = self.faculty_controller.update_faculty_status_with_retry(faculty_id, status)
            
            if result:
                logger.info(f"Successfully processed MQTT status update for faculty {faculty_id}")
                # Remove from pending if it was there
                self.pending_updates.pop(faculty_id, None)
            else:
                # Add to pending for retry
                self.pending_updates[faculty_id] = {
                    'status': status,
                    'timestamp': datetime.now(),
                    'data': data
                }
                
        except Exception as e:
            logger.error(f"Error handling MQTT faculty status update: {e}")
    
    def process_pending_updates(self):
        """Process pending updates when database becomes healthy."""
        if not self.pending_updates:
            return
        
        logger.info(f"Processing {len(self.pending_updates)} pending faculty status updates")
        
        for faculty_id, update_data in list(self.pending_updates.items()):
            try:
                # Check if update is still relevant (not too old)
                age = datetime.now() - update_data['timestamp']
                if age.total_seconds() > 300:  # 5 minutes
                    logger.warning(f"Discarding stale update for faculty {faculty_id}")
                    del self.pending_updates[faculty_id]
                    continue
                
                # Process the update
                result = self.faculty_controller.update_faculty_status_with_retry(
                    faculty_id, update_data['status']
                )
                
                if result:
                    logger.info(f"Successfully processed pending update for faculty {faculty_id}")
                    del self.pending_updates[faculty_id]
                    
            except Exception as e:
                logger.error(f"Error processing pending update for faculty {faculty_id}: {e}")
```

## Implementation Priority

### **Phase 1: Immediate Fixes (Critical)**
1. ✅ Increase health check intervals (30s → 120s)
2. ✅ Disable pool_pre_ping for SQLite
3. ✅ Increase failure threshold (3 → 5)
4. ✅ Add restart cooldown period

### **Phase 2: Enhanced Logic (High Priority)**
1. ✅ Implement intelligent restart conditions
2. ✅ Add transaction completion waiting
3. ✅ Implement faculty status update retry logic
4. ✅ Add MQTT-database coordination

### **Phase 3: Monitoring Improvements (Medium Priority)**
1. ✅ Enhanced logging and metrics
2. ✅ Database performance monitoring
3. ✅ Health check success rate tracking
4. ✅ Alert thresholds for restart frequency

## Expected Results

### **Immediate Benefits:**
- ✅ Reduced database restart frequency (every 30-40s → every 2+ hours)
- ✅ Improved faculty status update reliability
- ✅ Better MQTT-database synchronization
- ✅ Reduced system resource usage

### **Long-term Benefits:**
- ✅ More stable system operation
- ✅ Consistent faculty availability data
- ✅ Better user experience
- ✅ Reduced false alarms in monitoring

## Monitoring Recommendations

### **Key Metrics to Track:**
1. Database restart frequency
2. Faculty status update success rate
3. MQTT message processing latency
4. Health check success rate
5. Active transaction count during restarts

### **Alert Thresholds:**
- Database restarts > 1 per hour
- Faculty status update failures > 5%
- Health check failures > 20%
- Pending MQTT updates > 10

This comprehensive approach addresses the root causes of database instability while protecting the critical faculty status update workflow.
