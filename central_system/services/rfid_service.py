import logging
import threading
import time
import os
import sys
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RFIDService(QObject):
    """
    RFID Service for reading RFID cards via USB RFID reader.

    This service uses evdev to read input from a USB RFID reader
    which typically behaves like a keyboard.

    For Windows systems, a simulation mode is available for testing.
    """
    # Signal to emit when a card is read
    card_read_signal = pyqtSignal(str)

    def __init__(self):
        super(RFIDService, self).__init__()
        self.os_platform = sys.platform
        self.device_path = os.environ.get('RFID_DEVICE_PATH', None)
        self.simulation_mode = os.environ.get('RFID_SIMULATION_MODE', 'false').lower() == 'true'

        # Target RFID reader VID/PID
        self.target_vid = "ffff"
        self.target_pid = "0035"

        # Events and callbacks
        self.callbacks = []
        self.running = False
        self.read_thread = None

        # Connect the signal to the notification method to ensure thread safety
        self.card_read_signal.connect(self._notify_callbacks_safe)

        # Try to auto-detect RFID reader on initialization
        if not self.device_path and self.os_platform.startswith('linux'):
            # First try to find the target device by VID/PID
            if not self._find_device_by_vid_pid():
                # If not found by VID/PID, try generic detection
                self._detect_rfid_device()

        logger.info(f"RFID Service initialized (OS: {self.os_platform}, Simulation: {self.simulation_mode}, Device: {self.device_path})")

    def _find_device_by_vid_pid(self):
        """
        Find a USB device by VID/PID and determine its input device path.
        """
        try:
            # Use lsusb to find the device
            logger.info(f"Looking for USB device with VID:{self.target_vid} PID:{self.target_pid}")
            lsusb_output = subprocess.check_output(['lsusb'], universal_newlines=True)
            logger.info(f"Available USB devices:\n{lsusb_output}")

            # Look for our target device in lsusb output
            target_line = None
            for line in lsusb_output.split('\n'):
                if f"ID {self.target_vid}:{self.target_pid}" in line:
                    target_line = line
                    logger.info(f"Found target USB device: {line}")
                    break

            if not target_line:
                logger.warning(f"USB device with VID:{self.target_vid} PID:{self.target_pid} not found")
                return False

            # Attempt to find the corresponding input device
            try:
                import evdev
                devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

                # First try checking if any device's physical path contains the VID/PID
                for device in devices:
                    device_info = f"Device: {device.name} ({device.path})"
                    try:
                        phys = device.phys
                        if phys and (self.target_vid in phys.lower() and self.target_pid in phys.lower()):
                            logger.info(f"Found matching device by physical path: {device_info}")
                            self.device_path = device.path
                            return True
                    except Exception as e:
                        logger.debug(f"Error checking device physical path: {e}")

                    # Also log all device info for debugging
                    try:
                        info = f" - phys: {device.phys}"
                        if hasattr(device, 'info') and device.info:
                            info += f" - info: {device.info}"
                        logger.info(f"{device_info} {info}")
                    except Exception:
                        pass

                # If we haven't found it by physical path, try another approach
                # Let's check if there's a device that looks like an HID keyboard
                for device in devices:
                    if (evdev.ecodes.EV_KEY in device.capabilities() and
                        len(device.capabilities().get(evdev.ecodes.EV_KEY, [])) > 10):

                        # Check if this device behaves like a RFID reader
                        # RFID readers typically don't have modifiers like shift/control
                        key_caps = device.capabilities().get(evdev.ecodes.EV_KEY, [])
                        has_numerics = any(k in key_caps for k in range(evdev.ecodes.KEY_0, evdev.ecodes.KEY_9 + 1))
                        has_enter = evdev.ecodes.KEY_ENTER in key_caps

                        if has_numerics and has_enter:
                            logger.info(f"Found potential RFID reader: {device.name} ({device.path})")
                            self.device_path = device.path
                            return True

                logger.warning("No input device matching the target RFID reader found")
                return False

            except ImportError:
                logger.error("evdev library not installed. Please install it with: pip install evdev")
                return False

        except Exception as e:
            logger.error(f"Error finding device by VID/PID: {str(e)}")
            return False

    def _detect_rfid_device(self):
        """
        Auto-detect RFID device on Linux systems.
        """
        try:
            import evdev
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

            # Check all input devices
            for device in devices:
                # Log available devices to help debug
                device_info = f"Found input device: {device.name} ({device.path})"
                capabilities = []

                # Check device capabilities
                if evdev.ecodes.EV_KEY in device.capabilities():
                    capabilities.append("Keyboard")
                if evdev.ecodes.EV_ABS in device.capabilities():
                    capabilities.append("Touchscreen/Pad")
                if evdev.ecodes.EV_REL in device.capabilities():
                    capabilities.append("Mouse/Pointer")

                device_info += f" - Capabilities: {', '.join(capabilities)}"
                logger.info(device_info)

                # Look for devices that might be RFID readers
                # Many RFID readers present as HID keyboard devices
                if (
                    "rfid" in device.name.lower() or
                    "card" in device.name.lower() or
                    "reader" in device.name.lower() or
                    "hid" in device.name.lower() or
                    "usb" in device.name.lower()
                ):
                    # Check if it has keyboard capabilities
                    if evdev.ecodes.EV_KEY in device.capabilities():
                        key_caps = device.capabilities().get(evdev.ecodes.EV_KEY, [])
                        # RFID readers typically have number keys at minimum
                        key_count = len(key_caps)

                        if key_count > 10:  # It should have at least digit keys
                            self.device_path = device.path
                            logger.info(f"Auto-detected RFID reader: {device.name} ({device.path})")
                            return True

            logger.warning("No RFID reader device auto-detected. Will use simulation mode.")
            return False

        except ImportError:
            logger.error("evdev library not installed. Please install it with: pip install evdev")
            return False
        except Exception as e:
            logger.error(f"Error detecting RFID devices: {str(e)}")
            return False

    def start(self):
        """
        Start the RFID reading service.
        """
        if self.running:
            logger.warning("RFID Service is already running")
            return

        self.running = True

        # If we're not in simulation mode and on Linux, try one more time to detect the device
        if not self.simulation_mode and self.os_platform.startswith('linux') and not self.device_path:
            if not self._find_device_by_vid_pid() and not self._detect_rfid_device():
                logger.warning("No RFID device detected, falling back to simulation mode")
                self.simulation_mode = True

        if self.simulation_mode:
            logger.info("Starting RFID Service in simulation mode")
            self.read_thread = threading.Thread(target=self._simulate_rfid_reading)
        else:
            if self.os_platform.startswith('linux'):
                logger.info(f"Starting RFID Service in Linux mode with device: {self.device_path}")
                self.read_thread = threading.Thread(target=self._read_linux_rfid)
            else:
                logger.warning(f"RFID hardware mode not supported on {self.os_platform}, falling back to simulation")
                self.read_thread = threading.Thread(target=self._simulate_rfid_reading)

        self.read_thread.daemon = True
        self.read_thread.start()
        logger.info("RFID Service started")

    def stop(self):
        """
        Stop the RFID reading service.
        """
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
        logger.info("RFID Service stopped")

    def register_callback(self, callback):
        """
        Register a callback function to be called when an RFID card is read.

        Args:
            callback (callable): Function that takes an RFID UID string as argument
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            callback_name = getattr(callback, '__name__', str(callback))
            logger.info(f"Registered RFID callback: {callback_name}")

    def unregister_callback(self, callback):
        """
        Unregister a previously registered callback.

        Args:
            callback (callable): Function to unregister
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            callback_name = getattr(callback, '__name__', str(callback))
            logger.info(f"Unregistered RFID callback: {callback_name}")

    def _notify_callbacks_safe(self, rfid_uid):
        """
        Thread-safe notification of callbacks via Qt signals.
        Also attempts to look up the student based on the RFID UID.

        Args:
            rfid_uid (str): The RFID UID that was read
        """
        logger.info(f"RFID Service notifying callbacks for UID: {rfid_uid}")

        # CRITICAL: Force a database session refresh to ensure we have the latest data
        try:
            from ..models import get_db
            db = get_db()
            # Force SQLAlchemy to create a new session
            db.close()
            db = get_db(force_new=True)
            logger.info("Forced database session refresh to ensure latest student data")
        except Exception as e:
            logger.error(f"Error refreshing database session: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # Attempt to verify the student immediately
        student = None
        try:
            from ..models import Student, get_db  # Lazy import to avoid circular dependencies
            db = get_db()

            # Log the query we're about to execute
            logger.info(f"Looking up student with RFID UID: {rfid_uid}")

            # Try an exact match first
            student = db.query(Student).filter(Student.rfid_uid == rfid_uid).first()

            # If no exact match, try case-insensitive match
            if not student:
                logger.info(f"No exact match found, trying case-insensitive match for RFID: {rfid_uid}")
                # For PostgreSQL
                try:
                    student = db.query(Student).filter(Student.rfid_uid.ilike(rfid_uid)).first()
                except:
                    # For SQLite
                    student = db.query(Student).filter(Student.rfid_uid.lower() == rfid_uid.lower()).first()

            if student:
                logger.info(f"Student verified by RFIDService: {student.name} with ID: {student.id}")
                # Log the student details for debugging
                logger.info(f"Student details - Name: {student.name}, Department: {student.department}, RFID: {student.rfid_uid}")
            else:
                # Log all students in the database for debugging
                all_students = db.query(Student).all()
                logger.warning(f"No student found for RFID {rfid_uid} by RFIDService")
                logger.info(f"Available students in database: {len(all_students)}")
                for s in all_students:
                    logger.info(f"  - ID: {s.id}, Name: {s.name}, RFID: {s.rfid_uid}")
        except Exception as e:
            logger.error(f"Error verifying student in RFIDService: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            student = None  # Ensure student is None if lookup fails

        # Make a copy of callbacks to avoid issues if callbacks are modified during iteration
        callbacks_to_notify = list(self.callbacks)
        logger.info(f"Number of callbacks to notify: {len(callbacks_to_notify)}")

        # Notify all registered callbacks
        for callback in callbacks_to_notify:
            try:
                if callback is None:
                    logger.warning("Skipping None callback")
                    continue

                callback_name = getattr(callback, '__name__', str(callback))
                logger.info(f"Calling callback: {callback_name} with student: {student is not None}, rfid_uid: {rfid_uid}")
                callback(student, rfid_uid)
            except Exception as e:
                logger.error(f"Error in RFID callback {getattr(callback, '__name__', str(callback))}: {str(e)}")
                import traceback
                logger.error(f"Callback error traceback: {traceback.format_exc()}")

    def _notify_callbacks(self, rfid_uid):
        """
        Emit signal to notify callbacks in a thread-safe way.

        Args:
            rfid_uid (str): The RFID UID that was read
        """
        # Use signal to ensure thread safety
        self.card_read_signal.emit(rfid_uid)

    def _read_linux_rfid(self):
        """
        Read RFID input using evdev on Linux.
        """
        try:
            import evdev
            from evdev import categorize, ecodes

            # Verify device path is available
            if not self.device_path:
                logger.error("No RFID device path specified. Falling back to simulation mode.")
                self.simulation_mode = True
                self._simulate_rfid_reading()
                return

            try:
                # Open the device
                device = evdev.InputDevice(self.device_path)
                logger.info(f"Reading RFID from device: {device.name} ({device.device_path if hasattr(device, 'device_path') else self.device_path})")

                # Let's take exclusive control of the device to prevent keyboard input in other apps
                try:
                    device.grab()
                    logger.info("Grabbed exclusive access to the RFID reader")
                except Exception as grab_err:
                    logger.warning(f"Could not grab exclusive access to RFID reader: {grab_err}")

            except Exception as e:
                logger.error(f"Error opening RFID device {self.device_path}: {str(e)}")
                self._handle_device_failure("Failed to open RFID device", e)
                return

            # Mapping from key codes to characters (extend to support more characters)
            key_map = {
                evdev.ecodes.KEY_0: "0", evdev.ecodes.KEY_1: "1",
                evdev.ecodes.KEY_2: "2", evdev.ecodes.KEY_3: "3",
                evdev.ecodes.KEY_4: "4", evdev.ecodes.KEY_5: "5",
                evdev.ecodes.KEY_6: "6", evdev.ecodes.KEY_7: "7",
                evdev.ecodes.KEY_8: "8", evdev.ecodes.KEY_9: "9",
                evdev.ecodes.KEY_A: "A", evdev.ecodes.KEY_B: "B",
                evdev.ecodes.KEY_C: "C", evdev.ecodes.KEY_D: "D",
                evdev.ecodes.KEY_E: "E", evdev.ecodes.KEY_F: "F",
                # Add common special characters that might be used in 13.56 MHz cards
                evdev.ecodes.KEY_MINUS: "-", evdev.ecodes.KEY_SPACE: " ",
                evdev.ecodes.KEY_DOT: ".", evdev.ecodes.KEY_COMMA: ",",
                evdev.ecodes.KEY_SEMICOLON: ";", evdev.ecodes.KEY_APOSTROPHE: "'",
                # Add all digit and letter keys to be safe
                evdev.ecodes.KEY_G: "G", evdev.ecodes.KEY_H: "H",
                evdev.ecodes.KEY_I: "I", evdev.ecodes.KEY_J: "J",
                evdev.ecodes.KEY_K: "K", evdev.ecodes.KEY_L: "L",
                evdev.ecodes.KEY_M: "M", evdev.ecodes.KEY_N: "N",
                evdev.ecodes.KEY_O: "O", evdev.ecodes.KEY_P: "P",
                evdev.ecodes.KEY_Q: "Q", evdev.ecodes.KEY_R: "R",
                evdev.ecodes.KEY_S: "S", evdev.ecodes.KEY_T: "T",
                evdev.ecodes.KEY_U: "U", evdev.ecodes.KEY_V: "V",
                evdev.ecodes.KEY_W: "W", evdev.ecodes.KEY_X: "X",
                evdev.ecodes.KEY_Y: "Y", evdev.ecodes.KEY_Z: "Z"
            }

            # Read input events
            current_rfid = ""
            last_event_time = 0

            logger.info("RFID reader is active and waiting for cards (supports 13.56 MHz)")

            while self.running:
                try:
                    # Enhanced debugging - log all events for debugging
                    logger.info("Waiting for RFID card events...")

                    for event in device.read_loop():
                        if not self.running:
                            break

                        # Enhanced logging for all events
                        if event.type == evdev.ecodes.EV_KEY:
                            logger.debug(f"RFID Key event: type={event.type}, code={event.code}, value={event.value}")

                        # Reset the RFID string if there's a pause between key events
                        current_time = time.time()
                        if current_time - last_event_time > 1.0 and current_rfid:
                            logger.debug(f"Timeout reset for partial RFID: {current_rfid}")
                            current_rfid = ""

                        last_event_time = current_time

                        if event.type == evdev.ecodes.EV_KEY and event.value == 1:  # Key pressed
                            logger.debug(f"Key event: {event.code}")
                            if event.code in key_map:
                                current_rfid += key_map[event.code]
                                logger.debug(f"Building RFID: {current_rfid}")
                            # Handle Enter key to finalize RFID input
                            elif event.code == evdev.ecodes.KEY_ENTER or event.code == evdev.ecodes.KEY_KPENTER:
                                if current_rfid:
                                    logger.info(f"RFID read complete: {current_rfid}")
                                    # Use thread-safe notification
                                    self._notify_callbacks(current_rfid)
                                    current_rfid = ""
                            # If we get a character we don't recognize, log it for debugging
                            else:
                                key_name = "UNKNOWN"
                                for name, code in vars(evdev.ecodes).items():
                                    if name.startswith('KEY_') and code == event.code:
                                        key_name = name
                                        break
                                logger.info(f"Unhandled key in RFID input: {key_name} ({event.code})")

                except OSError as e:
                    logger.error(f"Device read error (device may have been disconnected): {str(e)}")
                    # Try to reconnect with retry mechanism
                    if self._attempt_device_reconnection(device):
                        continue  # Successfully reconnected, continue reading
                    else:
                        # Failed to reconnect, handle device failure
                        self._handle_device_failure("RFID device disconnected and reconnection failed", e)
                        break

            # Make sure to ungrab the device when we're done
            try:
                device.ungrab()
                logger.info("Released exclusive access to RFID reader")
            except:
                pass

        except ImportError:
            logger.error("evdev library not installed. Please install it with: pip install evdev")
            self._handle_device_failure("evdev library not available", None)
        except Exception as e:
            logger.error(f"Error reading RFID: {str(e)}")
            self._handle_device_failure("Unexpected RFID service error", e)

    def _simulate_rfid_reading(self):
        """
        Simulate RFID reading for development and testing.
        """
        logger.info("RFID simulation mode active. Use simulate_card_read() to trigger simulated reads.")

        while self.running:
            time.sleep(1)  # Just keep the thread alive

    def refresh_student_data(self):
        """
        Refresh the student data cache.
        This should be called when students are added, updated, or deleted.
        """
        logger.info("Refreshing RFID service student data cache")
        try:
            from ..models import Student, get_db

            # Force a new database session to ensure we get fresh data
            db = get_db(force_new=True)

            # Explicitly expire all objects to force a refresh from the database
            db.expire_all()

            # Query all students
            students = db.query(Student).all()
            logger.info(f"Refreshed student data cache, found {len(students)} students")

            # Log all students for debugging
            for student in students:
                logger.info(f"  - ID: {student.id}, Name: {student.name}, RFID: {student.rfid_uid}")

            # Close the database session to ensure it's not kept open
            db.close()

            return True
        except Exception as e:
            logger.error(f"Error refreshing student data cache: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def simulate_card_read(self, rfid_uid=None):
        """
        Simulate an RFID card read with a specified or random UID.

        Args:
            rfid_uid (str, optional): RFID UID to simulate. If None, a random UID is generated.
        """
        if not rfid_uid:
            # Generate a random RFID UID (10 characters hexadecimal - more like 13.56 MHz cards)
            import random
            rfid_uid = ''.join(random.choices('0123456789ABCDEF', k=10))

        logger.info(f"Simulating RFID read (13.56 MHz format): {rfid_uid}")

        # Use the signal method to ensure consistent processing path with real reads
        self._notify_callbacks(rfid_uid)

        return rfid_uid

    def _handle_device_failure(self, error_message, exception):
        """
        Handle RFID device failures with proper user notification and fallback.

        Args:
            error_message (str): Human-readable error message
            exception (Exception): The exception that caused the failure (can be None)
        """
        logger.error(f"RFID Device Failure: {error_message}")
        if exception:
            logger.error(f"Exception details: {str(exception)}")

        # Emit signal to notify UI components about the device failure
        self.device_status_changed.emit("disconnected", error_message)

        # Set simulation mode as fallback
        self.simulation_mode = True
        logger.warning("⚠️  RFID device failure - switching to simulation mode")
        logger.info("📋 Use the 'Simulate Card Read' button in the admin interface for testing")

        # Start simulation mode
        self._simulate_rfid_reading()

        # Schedule retry attempts
        self._schedule_device_reconnection()

    def _attempt_device_reconnection(self, device):
        """
        Attempt to reconnect to the RFID device with retry logic.

        Args:
            device: Current device object (may be invalid)

        Returns:
            bool: True if reconnection successful, False otherwise
        """
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting RFID device reconnection (attempt {attempt + 1}/{max_retries})")

                # First try to ungrab if we had grabbed it
                try:
                    device.ungrab()
                except:
                    pass

                # Wait before retry
                time.sleep(retry_delay)

                # Try to reopen the device
                import evdev
                device = evdev.InputDevice(self.device_path)
                logger.info(f"Reconnected to RFID device: {device.name}")

                # Try to grab it again
                try:
                    device.grab()
                    logger.info("Regained exclusive access to RFID reader")
                except:
                    logger.warning("Could not regain exclusive access, but device is connected")

                # Test the device with a simple operation
                device.capabilities()  # This will raise an exception if device is not working

                logger.info("✅ RFID device reconnection successful")
                self.device_status_changed.emit("connected", "RFID device reconnected successfully")
                return True

            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {str(e)}")
                retry_delay *= 2  # Exponential backoff

        logger.error("❌ All RFID device reconnection attempts failed")
        return False

    def _schedule_device_reconnection(self):
        """
        Schedule periodic attempts to reconnect to the RFID device.
        """
        # This could be enhanced with a timer-based retry mechanism
        # For now, we'll rely on manual retry through the UI
        logger.info("📅 Device reconnection can be attempted manually through the admin interface")
        logger.info("💡 Check device connection and use 'Refresh RFID Service' if available")

    def retry_device_connection(self):
        """
        Public method to manually retry RFID device connection.
        Can be called from UI components.

        Returns:
            bool: True if reconnection successful, False otherwise
        """
        if self.simulation_mode:
            logger.info("Attempting to exit simulation mode and reconnect to RFID device...")

            # Try to detect and connect to device
            if self._detect_rfid_device():
                self.simulation_mode = False
                logger.info("✅ Successfully reconnected to RFID device")
                self.device_status_changed.emit("connected", "RFID device reconnected")

                # Restart the reading thread
                if hasattr(self, 'read_thread') and self.read_thread.is_alive():
                    self.stop()
                    time.sleep(1)

                self.start()
                return True
            else:
                logger.warning("❌ Could not detect RFID device")
                self.device_status_changed.emit("disconnected", "RFID device not detected")
                return False
        else:
            logger.info("RFID service is not in simulation mode")
            return True

    def get_device_status(self):
        """
        Get current RFID device status.

        Returns:
            dict: Device status information
        """
        return {
            'simulation_mode': self.simulation_mode,
            'device_path': self.device_path,
            'running': self.running,
            'thread_alive': hasattr(self, 'read_thread') and self.read_thread.is_alive() if hasattr(self, 'read_thread') else False,
            'status': 'simulation' if self.simulation_mode else 'connected' if self.running else 'disconnected'
        }

# Singleton instance
rfid_service = None

def get_rfid_service():
    """
    Get the singleton RFID service instance.
    """
    global rfid_service
    if rfid_service is None:
        rfid_service = RFIDService()
    return rfid_service