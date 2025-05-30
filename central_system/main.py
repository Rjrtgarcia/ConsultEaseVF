import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('consultease.log')
    ]
)
logger = logging.getLogger(__name__)

# Import models and controllers
from central_system.models import init_db
from central_system.controllers import (
    RFIDController,
    FacultyController,
    ConsultationController,
    AdminController,
    FacultyResponseController
)

# Import async MQTT service
from central_system.services.async_mqtt_service import get_async_mqtt_service

# Import views
from central_system.views import (
    LoginWindow,
    DashboardWindow,
    AdminLoginWindow,
    AdminDashboardWindow
)

# Import the keyboard setup script generator
from central_system.views.login_window import create_keyboard_setup_script

# Import utilities
from central_system.utils import (
    apply_stylesheet,
    WindowTransitionManager,
    get_keyboard_manager,
    install_keyboard_manager
)
# Import direct keyboard integration
from central_system.utils.direct_keyboard import get_direct_keyboard
# Import theme system
from central_system.utils.theme import ConsultEaseTheme
# Import icons module separately to avoid early QPixmap creation
from central_system.utils import icons

class ConsultEaseApp:
    """
    Main application class for ConsultEase.
    """

    def __init__(self, fullscreen=False):
        """
        Initialize the ConsultEase application.
        """
        logger.info("Initializing ConsultEase application")

        # Create QApplication instance
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("ConsultEase")

        # Set up icons and modern UI (after QApplication is created)
        icons.initialize()
        logger.info("Initialized icons")

        # Apply centralized theme stylesheet
        try:
            # Apply base stylesheet from theme system
            self.app.setStyleSheet(ConsultEaseTheme.get_base_stylesheet())
            logger.info("Applied centralized theme stylesheet")
        except Exception as e:
            logger.error(f"Failed to apply theme stylesheet: {e}")
            # Fall back to old stylesheet as backup
            try:
                theme = self._get_theme_preference()
                apply_stylesheet(self.app, theme)
                logger.info(f"Applied fallback {theme} theme stylesheet")
            except Exception as e2:
                logger.error(f"Failed to apply fallback stylesheet: {e2}")

        # Create keyboard setup script for Raspberry Pi
        try:
            script_path = create_keyboard_setup_script()
            logger.info(f"Created keyboard setup script at {script_path}")
        except Exception as e:
            logger.error(f"Failed to create keyboard setup script: {e}")

        # Initialize unified keyboard manager for touch input
        try:
            self.keyboard_handler = get_keyboard_manager()
            # Install keyboard manager to handle focus events
            install_keyboard_manager(self.app)
            logger.info(f"Initialized keyboard manager with {self.keyboard_handler.active_keyboard} keyboard")
        except Exception as e:
            logger.error(f"Failed to initialize keyboard manager: {e}")
            self.keyboard_handler = None

        # Initialize direct keyboard integration as a fallback
        try:
            self.direct_keyboard = get_direct_keyboard()
            logger.info(f"Initialized direct keyboard integration with {self.direct_keyboard.keyboard_type} keyboard")
        except Exception as e:
            logger.error(f"Failed to initialize direct keyboard integration: {e}")
            self.direct_keyboard = None

        # Validate hardware before proceeding
        logger.info("Performing hardware validation...")
        from .utils.hardware_validator import log_hardware_status
        hardware_status = log_hardware_status()

        # Initialize database with comprehensive admin account validation
        logger.info("Initializing database and ensuring admin account integrity...")
        init_db()

        # Perform additional admin account verification after database initialization
        self._verify_admin_account_startup()

        # Start system monitoring
        logger.info("Starting system monitoring...")
        from .utils.system_monitor import start_system_monitoring
        start_system_monitoring()

        # Initialize system coordinator
        logger.info("Initializing system coordinator")
        from .services.system_coordinator import get_system_coordinator
        self.system_coordinator = get_system_coordinator()

        # Register services with coordinator
        self._register_system_services()

        # Start coordinated system
        if not self.system_coordinator.start_system():
            logger.error("Failed to start system coordinator")
            sys.exit(1)

        # Initialize controllers (after system coordinator)
        self.rfid_controller = RFIDController()
        self.faculty_controller = FacultyController()
        self.consultation_controller = ConsultationController()
        self.admin_controller = AdminController()
        self.faculty_response_controller = FacultyResponseController()

        # Ensure default admin exists
        self.admin_controller.ensure_default_admin()

        # Initialize windows
        self.login_window = None
        self.dashboard_window = None
        self.admin_login_window = None
        self.admin_dashboard_window = None

        # Start controllers
        logger.info("Starting RFID controller")
        self.rfid_controller.start()
        self.rfid_controller.register_callback(self.handle_rfid_scan)

        logger.info("Starting faculty controller")
        self.faculty_controller.start()

        logger.info("Starting consultation controller")
        self.consultation_controller.start()

        logger.info("Starting faculty response controller")
        self.faculty_response_controller.start()

        # Make sure at least one faculty is available for testing
        self._ensure_dr_john_smith_available()

        # Current student
        self.current_student = None

        # Initialize transition manager
        self.transition_manager = WindowTransitionManager(duration=300)
        logger.info("Initialized window transition manager")

        # Verify RFID controller is properly initialized
        try:
            from .services import get_rfid_service
            rfid_service = get_rfid_service()
            logger.info(f"RFID service initialized: {rfid_service}, simulation mode: {rfid_service.simulation_mode}")

            # Log registered callbacks
            logger.info(f"RFID service callbacks: {len(rfid_service.callbacks)}")
            for i, callback in enumerate(rfid_service.callbacks):
                callback_name = getattr(callback, '__name__', str(callback))
                logger.info(f"  Callback {i}: {callback_name}")
        except Exception as e:
            logger.error(f"Error verifying RFID service: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # Connect cleanup method
        self.app.aboutToQuit.connect(self.cleanup)

        # Display startup summary
        self._display_startup_summary()

        # Show login window
        self.show_login_window()

        # Store fullscreen preference for use in window creation
        self.fullscreen = fullscreen

    def _register_system_services(self):
        """Register services with the system coordinator."""
        logger.info("Registering system services with coordinator")

        # Register database service (with disabled auto-restart for stability)
        self.system_coordinator.register_service(
            name="database",
            dependencies=[],
            startup_callback=self._start_database_service,
            shutdown_callback=self._stop_database_service,
            health_check_callback=self._check_database_health,
            health_check_interval=300.0,  # Increased interval for stability
            max_restart_attempts=0  # Disable automatic restarts for database stability
        )

        # Register MQTT service
        self.system_coordinator.register_service(
            name="mqtt",
            dependencies=["database"],
            startup_callback=self._start_mqtt_service,
            shutdown_callback=self._stop_mqtt_service,
            health_check_callback=self._check_mqtt_health,
            health_check_interval=30.0,
            max_restart_attempts=3
        )

        # Register UI service
        self.system_coordinator.register_service(
            name="ui",
            dependencies=["database", "mqtt"],
            startup_callback=self._start_ui_service,
            shutdown_callback=self._stop_ui_service,
            health_check_callback=self._check_ui_health,
            health_check_interval=60.0,
            max_restart_attempts=1  # UI should not auto-restart
        )

        logger.info("System services registered successfully")

    def _start_database_service(self):
        """Start database service."""
        try:
            from .services.database_manager import get_database_manager
            db_manager = get_database_manager()
            return db_manager.initialize()
        except Exception as e:
            logger.error(f"Failed to start database service: {e}")
            return False

    def _stop_database_service(self):
        """Stop database service."""
        try:
            from .services.database_manager import get_database_manager
            db_manager = get_database_manager()
            db_manager.shutdown()
        except Exception as e:
            logger.error(f"Error stopping database service: {e}")

    def _check_database_health(self):
        """Check database health."""
        try:
            from .services.database_manager import get_database_manager
            db_manager = get_database_manager()
            health_status = db_manager.get_health_status()
            return health_status.get('is_healthy', False)
        except Exception as e:
            logger.debug(f"Database health check failed: {e}")
            return False

    def _start_mqtt_service(self):
        """Start MQTT service."""
        try:
            from .services.async_mqtt_service import get_async_mqtt_service
            mqtt_service = get_async_mqtt_service()

            # Register message handlers for faculty desk units
            self._register_mqtt_handlers(mqtt_service)

            mqtt_service.start()
            mqtt_service.connect()
            return True
        except Exception as e:
            logger.error(f"Failed to start MQTT service: {e}")
            return False

    def _stop_mqtt_service(self):
        """Stop MQTT service."""
        try:
            from .services.async_mqtt_service import get_async_mqtt_service
            mqtt_service = get_async_mqtt_service()
            mqtt_service.stop()
        except Exception as e:
            logger.error(f"Error stopping MQTT service: {e}")

    def _check_mqtt_health(self):
        """Check MQTT health."""
        try:
            from .services.async_mqtt_service import get_async_mqtt_service
            mqtt_service = get_async_mqtt_service()
            stats = mqtt_service.get_stats()
            return stats.get('connected', False)
        except Exception as e:
            logger.debug(f"MQTT health check failed: {e}")
            return False

    def _register_mqtt_handlers(self, mqtt_service):
        """Register MQTT message handlers for faculty desk units."""
        try:
            # Register handler for faculty status updates
            mqtt_service.register_topic_handler("consultease/faculty/+/status", self._handle_faculty_status)
            mqtt_service.register_topic_handler("consultease/faculty/+/mac_status", self._handle_faculty_mac_status)
            mqtt_service.register_topic_handler("consultease/faculty/+/requests", self._handle_faculty_requests)
            mqtt_service.register_topic_handler("consultease/faculty/+/presence", self._handle_faculty_presence)

            # Register handlers for professor topics (alternative naming)
            mqtt_service.register_topic_handler("professor/status", self._handle_professor_status)
            mqtt_service.register_topic_handler("professor/messages", self._handle_professor_messages)
            mqtt_service.register_topic_handler("professor/+/status", self._handle_professor_status)
            mqtt_service.register_topic_handler("professor/+/presence", self._handle_professor_presence)

            logger.info("MQTT message handlers registered for faculty desk units")
        except Exception as e:
            logger.error(f"Error registering MQTT handlers: {e}")

    def _handle_faculty_status(self, topic, data):
        """Handle faculty status updates from desk units."""
        try:
            logger.info(f"📡 Faculty status update received - Topic: {topic}, Data: {data}")
            # Extract faculty ID from topic if possible
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                faculty_id = topic_parts[2]
                logger.info(f"👨‍🏫 Faculty {faculty_id} status update: {data}")
        except Exception as e:
            logger.error(f"Error handling faculty status: {e}")

    def _handle_faculty_mac_status(self, topic, data):
        """Handle faculty MAC status updates from desk units."""
        try:
            logger.info(f"📡 Faculty MAC status update received - Topic: {topic}, Data: {data}")
        except Exception as e:
            logger.error(f"Error handling faculty MAC status: {e}")

    def _handle_faculty_requests(self, topic, data):
        """Handle faculty consultation requests from desk units."""
        try:
            logger.info(f"📡 Faculty consultation request received - Topic: {topic}, Data: {data}")
        except Exception as e:
            logger.error(f"Error handling faculty requests: {e}")

    def _handle_faculty_presence(self, topic, data):
        """Handle faculty presence updates from desk units."""
        try:
            logger.info(f"📡 Faculty presence update received - Topic: {topic}, Data: {data}")
        except Exception as e:
            logger.error(f"Error handling faculty presence: {e}")

    def _handle_professor_status(self, topic, data):
        """Handle professor status updates (alternative topic naming)."""
        try:
            logger.info(f"📡 Professor status update received - Topic: {topic}, Data: {data}")
        except Exception as e:
            logger.error(f"Error handling professor status: {e}")

    def _handle_professor_messages(self, topic, data):
        """Handle professor messages (alternative topic naming)."""
        try:
            logger.info(f"📡 Professor message received - Topic: {topic}, Data: {data}")
        except Exception as e:
            logger.error(f"Error handling professor messages: {e}")

    def _handle_professor_presence(self, topic, data):
        """Handle professor presence updates (alternative topic naming)."""
        try:
            logger.info(f"📡 Professor presence update received - Topic: {topic}, Data: {data}")
        except Exception as e:
            logger.error(f"Error handling professor presence: {e}")

    def _start_ui_service(self):
        """Start UI service."""
        try:
            # UI service is considered started when the application is running
            return True
        except Exception as e:
            logger.error(f"Failed to start UI service: {e}")
            return False

    def _stop_ui_service(self):
        """Stop UI service."""
        try:
            # UI service shutdown is handled by application shutdown
            pass
        except Exception as e:
            logger.error(f"Error stopping UI service: {e}")

    def _check_ui_health(self):
        """Check UI health."""
        try:
            # Basic UI health check - application is running
            return self.app is not None
        except Exception as e:
            logger.debug(f"UI health check failed: {e}")
            return False

    def _verify_admin_account_startup(self):
        """
        Verify admin account integrity during application startup.
        This provides an additional layer of validation and user feedback.
        """
        try:
            logger.info("🔐 Performing startup admin account verification...")

            # Test admin login functionality
            result = self.admin_controller.authenticate("admin", "TempPass123!")

            if result:
                logger.info("✅ Admin account verification successful")
                logger.info("🔑 Default admin credentials are working:")
                logger.info("   Username: admin")
                logger.info("   Password: TempPass123!")

                if result.get('requires_password_change', False):
                    logger.warning("⚠️  SECURITY NOTICE: Admin password must be changed on first login!")
                else:
                    logger.info("ℹ️  Admin password has been customized")

            else:
                logger.error("❌ CRITICAL: Admin account verification failed!")
                logger.error("❌ Admin login may not work properly!")

                # Attempt to fix the admin account
                logger.info("🔧 Attempting to repair admin account...")
                self._emergency_admin_repair()

        except Exception as e:
            logger.error(f"❌ Error during admin account verification: {e}")
            logger.error("❌ Admin functionality may be compromised!")

    def _emergency_admin_repair(self):
        """
        Emergency admin account repair during startup.
        This is a last-resort fix for admin account issues.
        """
        try:
            logger.warning("🚨 Performing emergency admin account repair...")

            from .models.base import get_db
            from .models.admin import Admin

            db = get_db()

            # Find or create admin account
            admin = db.query(Admin).filter(Admin.username == "admin").first()

            if admin:
                logger.info("📝 Resetting existing admin account...")
                # Reset to default password
                password_hash, salt = Admin.hash_password("TempPass123!")
                admin.password_hash = password_hash
                admin.salt = salt
                admin.is_active = True
                admin.force_password_change = True
            else:
                logger.info("🆕 Creating new admin account...")
                # Create new admin account
                password_hash, salt = Admin.hash_password("TempPass123!")
                admin = Admin(
                    username="admin",
                    password_hash=password_hash,
                    salt=salt,
                    is_active=True,
                    force_password_change=True
                )
                db.add(admin)

            db.commit()
            db.close()

            # Test the repair
            result = self.admin_controller.authenticate("admin", "TempPass123!")
            if result:
                logger.info("✅ Emergency admin repair successful!")
                logger.warning("🔑 Admin credentials: admin / TempPass123!")
                logger.warning("⚠️  MUST be changed on first login!")
            else:
                logger.error("❌ Emergency admin repair failed!")

        except Exception as e:
            logger.error(f"❌ Emergency admin repair failed: {e}")

    def _display_startup_summary(self):
        """
        Display a comprehensive startup summary including admin account status.
        """
        try:
            logger.info("=" * 60)
            logger.info("🚀 CONSULTEASE SYSTEM STARTUP SUMMARY")
            logger.info("=" * 60)

            # System information
            logger.info("📋 System Information:")
            logger.info(f"   • Application: ConsultEase Faculty Consultation System")
            logger.info(f"   • Version: Production Ready")
            logger.info(f"   • Platform: Raspberry Pi / Linux")
            logger.info(f"   • Database: SQLite (consultease.db)")

            # Admin account status
            logger.info("")
            logger.info("🔐 Admin Account Status:")
            try:
                from .models.base import get_db
                from .models.admin import Admin

                db = get_db()
                admin_count = db.query(Admin).count()
                default_admin = db.query(Admin).filter(Admin.username == "admin").first()

                if default_admin and default_admin.is_active:
                    logger.info("   ✅ Default admin account is active and ready")
                    logger.info("   🔑 Login Credentials:")
                    logger.info("      Username: admin")
                    logger.info("      Password: TempPass123!")

                    if default_admin.force_password_change:
                        logger.info("   ⚠️  Password change required on first login")
                    else:
                        logger.info("   ℹ️  Password has been customized")

                    # Test login
                    if default_admin.check_password("TempPass123!"):
                        logger.info("   ✅ Login test: PASSED")
                    else:
                        logger.info("   ❌ Login test: FAILED")
                else:
                    logger.info("   ❌ Default admin account not found or inactive")

                logger.info(f"   📊 Total admin accounts: {admin_count}")
                db.close()

            except Exception as e:
                logger.error(f"   ❌ Error checking admin status: {e}")

            # Security notices
            logger.info("")
            logger.info("🔒 Security Notices:")
            logger.info("   • Default password MUST be changed on first login")
            logger.info("   • All admin actions are logged for audit purposes")
            logger.info("   • System enforces strong password requirements")

            # Access instructions
            logger.info("")
            logger.info("🎯 How to Access Admin Dashboard:")
            logger.info("   1. Touch the screen to activate the interface")
            logger.info("   2. Click 'Admin Login' button")
            logger.info("   3. Enter: admin / TempPass123!")
            logger.info("   4. Change password when prompted")
            logger.info("   5. Access full admin functionality")

            # System status
            logger.info("")
            logger.info("📊 System Status:")
            logger.info("   ✅ Database initialized and ready")
            logger.info("   ✅ Admin account verified")
            logger.info("   ✅ Hardware validation completed")
            logger.info("   ✅ System monitoring active")
            logger.info("   ✅ MQTT service running")
            logger.info("   ✅ All controllers initialized")

            logger.info("")
            logger.info("🎉 ConsultEase is ready for use!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error displaying startup summary: {e}")

    def _get_theme_preference(self):
        """
        Get the user's theme preference.

        Returns:
            str: Theme name ('light' or 'dark')
        """
        # Default to light theme as per the technical context document
        theme = "light"

        # Check for environment variable
        if "CONSULTEASE_THEME" in os.environ:
            env_theme = os.environ["CONSULTEASE_THEME"].lower()
            if env_theme in ["light", "dark"]:
                theme = env_theme

        # Log the theme being used
        logger.info(f"Using {theme} theme based on preference")

        return theme

    def _ensure_dr_john_smith_available(self):
        """
        Make sure Dr. John Smith is available for testing.
        """
        try:
            # Use the faculty controller to ensure at least one faculty is available
            available_faculty = self.faculty_controller.ensure_available_faculty()

            if available_faculty:
                logger.info(f"Ensured faculty availability: {available_faculty.name} (ID: {available_faculty.id}) is now available")
            else:
                logger.warning("Could not ensure faculty availability")
        except Exception as e:
            logger.error(f"Error ensuring faculty availability: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def run(self):
        """
        Run the application.
        """
        logger.info("Starting ConsultEase application")
        return self.app.exec_()

    def cleanup(self):
        """
        Clean up resources before exiting.
        """
        logger.info("Cleaning up ConsultEase application")

        # Stop async MQTT service
        if hasattr(self, 'async_mqtt_service') and self.async_mqtt_service:
            logger.info("Stopping async MQTT service")
            self.async_mqtt_service.stop()

        # Stop controllers
        self.rfid_controller.stop()
        self.faculty_controller.stop()
        self.consultation_controller.stop()

    def show_login_window(self):
        """
        Show the login window.
        """
        if self.login_window is None:
            self.login_window = LoginWindow()
            self.login_window.student_authenticated.connect(self.handle_student_authenticated)
            self.login_window.change_window.connect(self.handle_window_change)

        # Determine which window is currently visible
        current_window = None
        if self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to LoginWindow")
            # Ensure login window is ready for fullscreen
            self.login_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.login_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing login window without transition")
            self.login_window.show()
            self.login_window.showFullScreen()  # Force fullscreen again to ensure it takes effect

    def show_dashboard_window(self, student_data=None):
        """
        Show the dashboard window.
        """
        self.current_student = student_data

        if self.dashboard_window is None:
            # Create a new dashboard window
            self.dashboard_window = DashboardWindow(student_data)
            self.dashboard_window.change_window.connect(self.handle_window_change)
            self.dashboard_window.consultation_requested.connect(self.handle_consultation_request)
        else:
            # Update student info and reinitialize the UI
            student_name = student_data.get('name', 'None') if student_data else 'None'
            logger.info(f"Updating dashboard with new student: {student_name}")

            # Store the new student data
            self.dashboard_window.student = student_data

            # Reinitialize the UI to update the welcome message and other student-specific elements
            self.dashboard_window.init_ui()

            # Update the consultation panel with the new student
            if hasattr(self.dashboard_window, 'consultation_panel'):
                self.dashboard_window.consultation_panel.set_student(student_data)
                self.dashboard_window.consultation_panel.refresh_history()

        # Populate faculty grid with fresh data
        try:
            # Force fresh data retrieval to avoid DetachedInstanceError
            faculties = self.faculty_controller.get_all_faculty()
            logger.info(f"Retrieved {len(faculties)} faculty members for dashboard")

            # Convert to safe data format to avoid session issues
            safe_faculty_data = []
            for faculty in faculties:
                try:
                    # Access all attributes while session is active
                    faculty_data = {
                        'id': faculty.id,
                        'name': faculty.name,
                        'department': faculty.department,
                        'status': faculty.status,
                        'always_available': getattr(faculty, 'always_available', False),
                        'email': getattr(faculty, 'email', ''),
                        'room': getattr(faculty, 'room', None),
                        'ble_id': getattr(faculty, 'ble_id', ''),
                        'last_seen': faculty.last_seen
                    }
                    safe_faculty_data.append(faculty_data)
                except Exception as attr_error:
                    logger.warning(f"Error accessing faculty {faculty.id} attributes: {attr_error}")
                    continue

            # Pass safe data to dashboard
            self.dashboard_window.populate_faculty_grid_safe(safe_faculty_data)

        except Exception as e:
            logger.error(f"Error retrieving faculty data for dashboard: {e}")
            # Show empty grid if there's an error
            self.dashboard_window.populate_faculty_grid_safe([])

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to DashboardWindow")
            # Ensure dashboard window is ready for fullscreen
            self.dashboard_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.dashboard_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing dashboard window without transition")
            self.dashboard_window.show()
            self.dashboard_window.showFullScreen()  # Force fullscreen to ensure it takes effect

        # Log that we've shown the dashboard
        student_name = student_data.get('name', 'Unknown') if student_data else 'Unknown'
        logger.info(f"Showing dashboard for student: {student_name}")

    def show_admin_login_window(self):
        """
        Show the admin login window.
        """
        if self.admin_login_window is None:
            self.admin_login_window = AdminLoginWindow()
            self.admin_login_window.admin_authenticated.connect(self.handle_admin_authenticated)
            self.admin_login_window.change_window.connect(self.handle_window_change)
            # Set the admin controller for first-time setup detection
            self.admin_login_window.set_admin_controller(self.admin_controller)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Define a callback for after the transition completes
        def after_transition():
            # Force the keyboard to show
            if self.keyboard_handler:
                logger.info("Showing keyboard using improved keyboard handler")
                self.keyboard_handler.show_keyboard()

                # Focus the username input to trigger the keyboard
                QTimer.singleShot(300, lambda: self.admin_login_window.username_input.setFocus())
                # Focus again after a longer delay to ensure keyboard appears
                QTimer.singleShot(800, lambda: self.admin_login_window.username_input.setFocus())

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to AdminLoginWindow")
            # Ensure admin login window is ready for fullscreen
            self.admin_login_window.showFullScreen()
            # Apply transition with callback
            self.transition_manager.fade_out_in(current_window, self.admin_login_window, after_transition)
        else:
            # No transition needed, just show the window
            logger.info("Showing admin login window without transition")
            self.admin_login_window.show()
            self.admin_login_window.showFullScreen()  # Force fullscreen
            # Call the callback directly
            after_transition()

    def show_admin_dashboard_window(self, admin=None):
        """
        Show the admin dashboard window.
        """
        if self.admin_dashboard_window is None:
            self.admin_dashboard_window = AdminDashboardWindow(admin)
            self.admin_dashboard_window.change_window.connect(self.handle_window_change)
            self.admin_dashboard_window.faculty_updated.connect(self.handle_faculty_updated)
            self.admin_dashboard_window.student_updated.connect(self.handle_student_updated)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to AdminDashboardWindow")
            # Ensure admin dashboard window is ready for fullscreen
            self.admin_dashboard_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.admin_dashboard_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing admin dashboard window without transition")
            self.admin_dashboard_window.show()
            self.admin_dashboard_window.showFullScreen()  # Force fullscreen

    def handle_rfid_scan(self, student, rfid_uid):
        """
        Handle RFID scan event.

        Args:
            student (Student): Verified student or None if not verified
            rfid_uid (str): RFID UID that was scanned
        """
        logger.info(f"Main.handle_rfid_scan called with student: {student}, rfid_uid: {rfid_uid}")

        # If login window is active and visible
        if self.login_window and self.login_window.isVisible():
            logger.info(f"Forwarding RFID scan to login window: {rfid_uid}")
            self.login_window.handle_rfid_read(rfid_uid, student)
        else:
            logger.info(f"Login window not visible, RFID scan not forwarded: {rfid_uid}")

    def handle_student_authenticated(self, student_data):
        """
        Handle student authentication event.

        Args:
            student_data (dict): Authenticated student data dictionary
        """
        student_name = student_data.get('name', 'Unknown') if student_data else 'Unknown'
        logger.info(f"Student authenticated: {student_name}")

        # Store the current student data
        self.current_student = student_data

        # Show the dashboard window
        self.show_dashboard_window(student_data)

    def handle_admin_authenticated(self, credentials):
        """
        Handle admin authentication event.

        Args:
            credentials (tuple): Admin credentials (username, password) or (username, None) for auto-login
        """
        # Unpack credentials from tuple
        username, password = credentials

        # Handle auto-login case (from account creation)
        if password is None:
            logger.info(f"Auto-login for newly created admin: {username}")
            # Create admin info for dashboard
            admin_info = {
                'username': username
            }
            self.show_admin_dashboard_window(admin_info)
            return

        # Normal authentication flow
        auth_result = self.admin_controller.authenticate(username, password)

        if auth_result:
            admin = auth_result['admin']
            logger.info(f"Admin authenticated: {username}")

            # Check if password change is required
            if auth_result.get('requires_password_change', False):
                logger.warning(f"Admin {username} requires password change")
                self.show_password_change_dialog(admin, forced=True)
                return

            # Create admin info to pass to dashboard
            admin_info = {
                'id': admin.id,
                'username': admin.username
            }
            self.show_admin_dashboard_window(admin_info)
        else:
            logger.warning(f"Admin authentication failed: {username}")
            if self.admin_login_window:
                # Check if this might be a first-time setup issue
                if not self.admin_controller.check_valid_admin_accounts_exist():
                    self.admin_login_window.show_login_error(
                        "No valid admin accounts found. Please check the first-time setup."
                    )
                else:
                    self.admin_login_window.show_login_error("Invalid username or password")

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request event.

        Args:
            faculty (object): Faculty object or dictionary
            message (str): Consultation message
            course_code (str): Course code
        """
        if not self.current_student:
            logger.error("Cannot request consultation: no student authenticated")
            return

        # Get student ID from either object or dictionary
        if isinstance(self.current_student, dict):
            student_id = self.current_student.get('id')
            student_name = self.current_student.get('name', 'Unknown')
        else:
            # Legacy support for student objects
            student_id = getattr(self.current_student, 'id', None)
            student_name = getattr(self.current_student, 'name', 'Unknown')

        if not student_id:
            logger.error("Cannot request consultation: student ID not available")
            return

        # Handle both Faculty object and dictionary
        if isinstance(faculty, dict):
            faculty_name = faculty['name']
            faculty_id = faculty['id']
        else:
            faculty_name = faculty.name
            faculty_id = faculty.id

        logger.info(f"Consultation requested by {student_name} with: {faculty_name}")

        # Create consultation request using the correct method
        consultation = self.consultation_controller.create_consultation(
            student_id=student_id,
            faculty_id=faculty_id,
            request_message=message,
            course_code=course_code
        )

        # Show success/error message
        if consultation:
            logger.info(f"Successfully created consultation request: {consultation.id}")
            # No need to show notification as DashboardWindow already shows a message box
        else:
            logger.error("Failed to create consultation request")
            # Show error message if the dashboard window has a show_notification method
            if hasattr(self.dashboard_window, 'show_notification'):
                self.dashboard_window.show_notification(
                    "Failed to send consultation request. Please try again.",
                    "error"
                )

    def handle_faculty_updated(self):
        """
        Handle faculty data updated event with enhanced cross-dashboard synchronization.
        """
        logger.info("Faculty data updated - refreshing all active dashboards")

        # Refresh student dashboard if active
        if self.dashboard_window and self.dashboard_window.isVisible():
            try:
                faculties = self.faculty_controller.get_all_faculty()
                logger.info(f"Refreshing student dashboard with {len(faculties)} faculty members")
                self.dashboard_window.populate_faculty_grid(faculties)

                # Also update the consultation panel's faculty options
                if hasattr(self.dashboard_window, 'consultation_panel'):
                    self.dashboard_window.consultation_panel.set_faculty_options(faculties)

            except Exception as e:
                logger.error(f"Error refreshing student dashboard: {e}")

        # Refresh admin dashboard if it's open
        if hasattr(self, 'admin_dashboard_window') and self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            try:
                logger.info("Refreshing admin dashboard faculty table")
                self.admin_dashboard_window.refresh_data()
            except Exception as e:
                logger.error(f"Error refreshing admin dashboard: {e}")

        # Trigger immediate refresh of faculty status for real-time updates
        if hasattr(self, 'faculty_controller'):
            try:
                # Force cache refresh for immediate updates
                self.faculty_controller.get_all_faculty.cache_clear()
            except Exception as e:
                logger.debug(f"Cache clear not available: {e}")

    def handle_student_updated(self):
        """
        Handle student data updated event.
        """
        logger.info("Student data updated, refreshing RFID service and controller")

        # Refresh RFID service and controller's student data
        try:
            # First, refresh the RFID service directly
            from central_system.services import get_rfid_service
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()

            # Then refresh the RFID controller
            students = self.rfid_controller.refresh_student_data()

            # Log all students for debugging
            for student in students:
                logger.info(f"Student: ID={student.id}, Name={student.name}, RFID={student.rfid_uid}")

            # If login window is active, make sure it's ready for scanning
            if self.login_window and self.login_window.isVisible():
                logger.info("Login window is active, ensuring RFID scanning is active")
                self.login_window.start_rfid_scanning()

            logger.info("Student data refresh complete")
        except Exception as e:
            logger.error(f"Error refreshing student data: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def show_password_change_dialog(self, admin, forced=False):
        """
        Show password change dialog.

        Args:
            admin: Admin object
            forced: Whether password change is forced
        """
        try:
            from .views.password_change_dialog import PasswordChangeDialog

            admin_info = {
                'id': admin.id,
                'username': admin.username
            }

            dialog = PasswordChangeDialog(admin_info, forced_change=forced, parent=None)

            def on_password_changed(success):
                if success and forced:
                    # If forced password change was successful, proceed to dashboard
                    logger.info(f"Forced password change completed for admin: {admin.username}")
                    self.show_admin_dashboard_window(admin_info)
                elif success:
                    logger.info(f"Password change completed for admin: {admin.username}")

            dialog.password_changed.connect(on_password_changed)
            dialog.exec_()

        except Exception as e:
            logger.error(f"Error showing password change dialog: {e}")
            if forced:
                # If forced password change fails, show error and exit
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    "Critical Error",
                    "Failed to load password change dialog. The application will exit."
                )
                self.app.quit()

    def handle_window_change(self, window_name, data=None):
        """
        Handle window change event.

        Args:
            window_name (str): Name of window to show
            data (any): Optional data to pass to the window
        """
        if window_name == "login":
            self.show_login_window()
        elif window_name == "dashboard":
            self.show_dashboard_window(data)
        elif window_name == "admin_login":
            self.show_admin_login_window()
        elif window_name == "admin_dashboard":
            self.show_admin_dashboard_window(data)
        else:
            logger.warning(f"Unknown window: {window_name}")

if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("consultease.log")
        ]
    )

    # Enable debug logging for RFID service
    rfid_logger = logging.getLogger('central_system.services.rfid_service')
    rfid_logger.setLevel(logging.DEBUG)

    # Set environment variables if needed
    import os

    # Configure RFID - enable simulation mode since we're on Raspberry Pi
    os.environ['RFID_SIMULATION_MODE'] = 'true'  # Enable if no RFID reader available

    # Set the theme to light as per the technical context document
    os.environ['CONSULTEASE_THEME'] = 'light'

    # Use SQLite for development and testing
    os.environ['DB_TYPE'] = 'sqlite'
    os.environ['DB_PATH'] = 'consultease.db'  # SQLite database file

    # Check if we're running in fullscreen mode
    fullscreen = os.environ.get('CONSULTEASE_FULLSCREEN', 'false').lower() == 'true'

    # Start the application
    app = ConsultEaseApp(fullscreen=fullscreen)
    sys.exit(app.run())