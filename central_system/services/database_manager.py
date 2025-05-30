"""
Enhanced Database Manager for ConsultEase.
Provides connection pooling, health monitoring, and resilient database operations.
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Database connection statistics."""
    total_connections: int = 0
    active_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    last_connection_time: Optional[datetime] = None
    last_error: Optional[str] = None


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass


class DatabaseManager:
    """
    Enhanced database manager with connection pooling and health monitoring.
    """

    def __init__(self, database_url: str, pool_size: int = 5, max_overflow: int = 10,
                 pool_timeout: int = 30, pool_recycle: int = 1800):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Time to recycle connections (seconds)
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle

        # Connection management
        self.engine = None
        self.SessionLocal = None
        self.is_initialized = False

        # Statistics and monitoring
        self.stats = ConnectionStats()
        self.health_check_interval = 120.0  # Increased to 2 minutes to reduce false positives
        self.last_health_check = None
        self.is_healthy = False

        # Enhanced health check configuration
        self.health_check_failure_threshold = 5  # Allow more failures before restart
        self.health_check_consecutive_failures = 0
        self.last_successful_health_check = None

        # Grace period and restart cooldown
        self.health_check_grace_period = 300.0  # 5 minutes grace period
        self.restart_cooldown = 600.0  # 10 minutes between restarts
        self.last_restart_time = None

        # Thread safety
        self.lock = threading.RLock()

        # Health monitoring
        self.health_monitor_thread = None
        self.monitoring_enabled = False

        logger.info("Database manager initialized")

    def initialize(self) -> bool:
        """
        Initialize database engine and connection pool.

        Returns:
            bool: True if initialization successful
        """
        with self.lock:
            if self.is_initialized:
                logger.debug("Database manager already initialized")
                return True

            try:
                # Create engine with appropriate configuration for database type
                if self.database_url.startswith('sqlite'):
                    # Optimized SQLite configuration for stability
                    self.engine = create_engine(
                        self.database_url,
                        poolclass=StaticPool,  # Use StaticPool for SQLite
                        connect_args={
                            "check_same_thread": False,  # Allow SQLite to be used across threads
                            "timeout": 60,  # Increased timeout to reduce false failures
                            "isolation_level": None,  # Autocommit mode for better concurrency
                            "journal_mode": "WAL",  # Write-Ahead Logging for better concurrency
                            "synchronous": "NORMAL",  # Balanced safety/performance
                            "cache_size": -64000,  # 64MB cache for better performance
                            "temp_store": "memory"  # Use memory for temp tables
                        },
                        pool_pre_ping=False,  # Disabled for SQLite - causes unnecessary overhead
                        echo=False  # Set to True for SQL debugging
                    )
                    logger.info("Created optimized SQLite engine with enhanced configuration")
                else:
                    # PostgreSQL configuration - full connection pooling
                    self.engine = create_engine(
                        self.database_url,
                        poolclass=QueuePool,
                        pool_size=self.pool_size,
                        max_overflow=self.max_overflow,
                        pool_timeout=self.pool_timeout,
                        pool_recycle=self.pool_recycle,
                        pool_pre_ping=True,  # Validate connections before use
                        echo=False  # Set to True for SQL debugging
                    )
                    logger.info("Created PostgreSQL engine with QueuePool")

                # Setup event listeners for monitoring
                self._setup_event_listeners()

                # Create session factory
                self.SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )

                # Test initial connection
                if self._test_connection():
                    self.is_initialized = True
                    self.is_healthy = True
                    logger.info("Database manager initialized successfully")

                    # Start health monitoring
                    self.start_health_monitoring()
                    return True
                else:
                    logger.error("Failed to establish initial database connection")
                    return False

            except Exception as e:
                logger.error(f"Error initializing database manager: {e}")
                self.stats.last_error = str(e)
                return False

    def get_session(self, force_new: bool = False, max_retries: int = 3) -> Session:
        """
        Get database session with retry logic.

        Args:
            force_new: Force creation of new session
            max_retries: Maximum retry attempts

        Returns:
            Session: Database session

        Raises:
            DatabaseConnectionError: If unable to get session
        """
        if not self.is_initialized:
            if not self.initialize():
                raise DatabaseConnectionError("Database manager not initialized")

        last_error = None

        for attempt in range(max_retries):
            try:
                with self.lock:
                    # Create session
                    session = self.SessionLocal()

                    # Test session with health check
                    if self._test_session_health(session):
                        self.stats.total_connections += 1
                        self.stats.active_connections += 1
                        self.stats.last_connection_time = datetime.now()

                        if force_new:
                            session.expire_all()

                        logger.debug(f"Database session acquired (attempt {attempt + 1})")
                        return session
                    else:
                        session.close()
                        raise DatabaseConnectionError("Session health check failed")

            except Exception as e:
                last_error = e
                self.stats.failed_connections += 1
                logger.warning(f"Database session attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff
                    logger.info(f"Retrying database connection in {wait_time} seconds...")
                    time.sleep(wait_time)

                    # Try to reinitialize if connection is completely lost
                    if isinstance(e, (DisconnectionError, OperationalError)):
                        self._reinitialize_engine()

        # All attempts failed
        self.stats.last_error = str(last_error)
        raise DatabaseConnectionError(f"Unable to get database session after {max_retries} attempts: {last_error}")

    @contextmanager
    def get_session_context(self, force_new: bool = False, max_retries: int = 3):
        """
        Context manager for database sessions with automatic cleanup.

        Args:
            force_new: Force creation of new session
            max_retries: Maximum retry attempts

        Yields:
            Session: Database session
        """
        session = None
        try:
            session = self.get_session(force_new=force_new, max_retries=max_retries)
            yield session
            session.commit()
        except Exception as e:
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()
                with self.lock:
                    self.stats.active_connections = max(0, self.stats.active_connections - 1)

    def execute_query(self, query: str, params: Dict = None, max_retries: int = 3) -> Any:
        """
        Execute a query with retry logic.

        Args:
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum retry attempts

        Returns:
            Query result
        """
        start_time = time.time()

        try:
            with self.get_session_context(max_retries=max_retries) as session:
                result = session.execute(text(query), params or {})

                # Update statistics
                query_time = time.time() - start_time
                self.stats.total_queries += 1
                self._update_avg_query_time(query_time)

                return result

        except Exception as e:
            self.stats.failed_queries += 1
            logger.error(f"Query execution failed: {e}")
            raise

    def start_health_monitoring(self):
        """Start health monitoring thread."""
        if self.monitoring_enabled:
            return

        self.monitoring_enabled = True
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            name="DatabaseHealthMonitor",
            daemon=True
        )
        self.health_monitor_thread.start()
        logger.info("Database health monitoring started")

    def stop_health_monitoring(self):
        """Stop health monitoring thread."""
        self.monitoring_enabled = False
        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=5.0)
        logger.info("Database health monitoring stopped")

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get database health status.

        Returns:
            dict: Health status information
        """
        with self.lock:
            pool_status = {}
            if self.engine and hasattr(self.engine.pool, 'status'):
                pool = self.engine.pool
                pool_status = {
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid()
                }

            return {
                'is_healthy': self.is_healthy,
                'is_initialized': self.is_initialized,
                'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
                'stats': {
                    'total_connections': self.stats.total_connections,
                    'active_connections': self.stats.active_connections,
                    'failed_connections': self.stats.failed_connections,
                    'total_queries': self.stats.total_queries,
                    'failed_queries': self.stats.failed_queries,
                    'avg_query_time': self.stats.avg_query_time,
                    'last_connection_time': self.stats.last_connection_time.isoformat() if self.stats.last_connection_time else None,
                    'last_error': self.stats.last_error
                },
                'pool_status': pool_status
            }

    def _test_connection(self) -> bool:
        """Test database connection with improved error handling."""
        try:
            # Use a timeout for the connection test
            with self.engine.connect() as conn:
                # Set a statement timeout for the health check
                if self.database_url.startswith('postgresql'):
                    conn.execute(text("SET statement_timeout = '5s'"))

                result = conn.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                success = row and row[0] == 1

                if success:
                    logger.debug("Database health check passed")
                else:
                    logger.warning("Database health check returned unexpected result")

                return success
        except Exception as e:
            logger.debug(f"Database connection test failed: {e}")
            return False

    def _test_connection_with_retry(self, max_retries: int = 3) -> bool:
        """Test database connection with retry logic for transient failures."""
        for attempt in range(max_retries):
            try:
                if self._test_connection():
                    return True

                if attempt < max_retries - 1:
                    # Short wait between retries for transient issues
                    time.sleep(1.0)
                    logger.debug(f"Health check retry {attempt + 1}/{max_retries}")

            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1.0)

        return False

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

    def _test_session_health(self, session: Session) -> bool:
        """Test session health."""
        try:
            result = session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            return row and row[0] == 1
        except Exception as e:
            logger.debug(f"Session health check failed: {e}")
            return False

    def _health_monitor_loop(self):
        """Improved health monitoring with grace periods and intelligent restart logic."""
        while self.monitoring_enabled:
            try:
                current_time = datetime.now()

                # Check if health check is due
                if (not self.last_health_check or
                    current_time - self.last_health_check >= timedelta(seconds=self.health_check_interval)):

                    # Perform health check with retry
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
                            logger.warning("Database restart conditions met, initiating safe restart")
                            self._restart_database_safely()
                        else:
                            # Mark as unhealthy but don't restart yet
                            self.is_healthy = False

                # Sleep longer to reduce overhead
                time.sleep(30.0)  # Increased from 5 seconds to reduce system load

            except Exception as e:
                logger.error(f"Error in database health monitor: {e}")
                time.sleep(60.0)  # Wait longer on error

    def _reinitialize_engine(self):
        """Reinitialize database engine."""
        try:
            logger.info("Reinitializing database engine...")

            with self.lock:
                # Dispose of old engine
                if self.engine:
                    self.engine.dispose()

                # Reset state
                self.is_initialized = False
                self.is_healthy = False

                # Reinitialize
                self.initialize()

        except Exception as e:
            logger.error(f"Error reinitializing database engine: {e}")

    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring."""
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            logger.debug("Database connection established")

        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Database connection checked out from pool")

        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Database connection checked in to pool")

    def _update_avg_query_time(self, query_time: float):
        """Update average query time."""
        if self.stats.total_queries == 1:
            self.stats.avg_query_time = query_time
        else:
            # Running average
            self.stats.avg_query_time = (
                (self.stats.avg_query_time * (self.stats.total_queries - 1) + query_time) /
                self.stats.total_queries
            )

    def shutdown(self):
        """Shutdown database manager."""
        logger.info("Shutting down database manager...")

        # Stop health monitoring
        self.stop_health_monitoring()

        # Dispose of engine
        with self.lock:
            if self.engine:
                self.engine.dispose()
                self.engine = None

            self.SessionLocal = None
            self.is_initialized = False
            self.is_healthy = False

        logger.info("Database manager shutdown complete")


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _database_manager
    if _database_manager is None:
        from ..utils.config_manager import get_config

        # Get database configuration
        db_config = get_config('database', {})
        database_url = _build_database_url(db_config)

        _database_manager = DatabaseManager(
            database_url=database_url,
            pool_size=db_config.get('pool_size', 5),
            max_overflow=db_config.get('max_overflow', 10),
            pool_timeout=db_config.get('pool_timeout', 30),
            pool_recycle=db_config.get('pool_recycle', 1800)
        )

        # Initialize the manager
        _database_manager.initialize()

    return _database_manager


def _build_database_url(db_config: Dict[str, Any]) -> str:
    """Build database URL from configuration."""
    db_type = db_config.get('type', 'sqlite')

    if db_type == 'sqlite':
        db_name = db_config.get('name', 'consultease.db')
        return f"sqlite:///{db_name}"
    elif db_type == 'postgresql':
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        name = db_config.get('name', 'consultease')
        user = db_config.get('user', '')
        password = db_config.get('password', '')

        if user and password:
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        else:
            return f"postgresql://{host}:{port}/{name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def set_database_manager(manager: DatabaseManager):
    """Set global database manager instance."""
    global _database_manager
    _database_manager = manager
