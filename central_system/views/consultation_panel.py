"""
Consultation panel module.
Contains the consultation request form and consultation history panel.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QFrame, QLineEdit, QTextEdit,
                            QComboBox, QMessageBox, QTabWidget, QTableWidget,
                            QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
                            QSizePolicy, QProgressBar, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QColor

import logging

# Set up logging
logger = logging.getLogger(__name__)

class ConsultationRequestForm(QFrame):
    """
    Form to request a consultation with a faculty member.
    """
    request_submitted = pyqtSignal(object, str, str)

    def __init__(self, faculty=None, parent=None):
        super().__init__(parent)
        self.faculty = faculty
        self.faculty_options = []
        self.init_ui()

    def init_ui(self):
        """
        Initialize the consultation request form UI.
        """
        # Import theme system
        from ..utils.theme import ConsultEaseTheme

        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("consultation_request_form")

        # Apply theme-based stylesheet with further improved readability
        self.setStyleSheet('''
            QFrame#consultation_request_form {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                font-size: 16pt;
                color: #212529;
                font-weight: 500;
                margin-bottom: 5px;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 2px solid #4dabf7;
                border-radius: 5px;
                padding: 15px;
                background-color: white;
                font-size: 16pt;
                color: #212529;
                margin: 5px 0;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #228be6;
                background-color: #f1f3f5;
            }
            QPushButton {
                border-radius: 5px;
                padding: 15px 25px;
                font-size: 16pt;
                font-weight: bold;
                color: white;
                margin: 10px 0;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        ''')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Form title
        title_label = QLabel("Request Consultation")
        title_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title_label)

        # Faculty selection
        faculty_layout = QHBoxLayout()
        faculty_label = QLabel("Faculty:")
        faculty_label.setFixedWidth(120)
        faculty_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2c3e50;")
        self.faculty_combo = QComboBox()
        self.faculty_combo.setMinimumWidth(300)
        self.faculty_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                font-size: 12pt;
            }
            QComboBox:focus {
                border: 2px solid #2980b9;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #3498db;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #3498db;
                selection-background-color: #3498db;
                selection-color: white;
                background-color: white;
                font-size: 12pt;
            }
        """)
        faculty_layout.addWidget(faculty_label)
        faculty_layout.addWidget(self.faculty_combo)
        main_layout.addLayout(faculty_layout)

        # Course code input
        course_layout = QHBoxLayout()
        course_label = QLabel("Course Code:")
        course_label.setFixedWidth(120)
        course_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2c3e50;")
        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("e.g., CS101 (optional)")
        self.course_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                font-size: 12pt;
            }
            QLineEdit:focus {
                border: 2px solid #2980b9;
            }
        """)
        course_layout.addWidget(course_label)
        course_layout.addWidget(self.course_input)
        main_layout.addLayout(course_layout)

        # Message input
        message_layout = QVBoxLayout()
        message_label = QLabel("Consultation Details:")
        message_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2c3e50;")
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Describe what you'd like to discuss...")
        self.message_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                font-size: 12pt;
            }
            QTextEdit:focus {
                border: 2px solid #2980b9;
            }
        """)
        self.message_input.setMinimumHeight(150)
        message_layout.addWidget(message_label)
        message_layout.addWidget(self.message_input)
        main_layout.addLayout(message_layout)

        # Character count with visual indicator
        char_count_frame = QFrame()
        char_count_layout = QVBoxLayout(char_count_frame)
        char_count_layout.setContentsMargins(0, 0, 0, 0)
        char_count_layout.setSpacing(2)

        # Label and progress bar in a horizontal layout
        count_indicator_layout = QHBoxLayout()
        count_indicator_layout.setContentsMargins(0, 0, 0, 0)

        self.char_count_label = QLabel("0/500 characters")
        self.char_count_label.setAlignment(Qt.AlignLeft)
        self.char_count_label.setStyleSheet("color: #2c3e50; font-size: 11pt; font-weight: bold;")

        # Add a small info label about the limit
        char_limit_info = QLabel("(500 character limit)")
        char_limit_info.setStyleSheet("color: #2c3e50; font-size: 10pt; font-weight: bold;")
        char_limit_info.setAlignment(Qt.AlignRight)

        count_indicator_layout.addWidget(self.char_count_label)
        count_indicator_layout.addStretch()
        count_indicator_layout.addWidget(char_limit_info)

        char_count_layout.addLayout(count_indicator_layout)

        # Add progress bar for visual feedback
        self.char_count_progress = QProgressBar()
        self.char_count_progress.setRange(0, 500)
        self.char_count_progress.setValue(0)
        self.char_count_progress.setTextVisible(False)
        self.char_count_progress.setFixedHeight(10)
        self.char_count_progress.setStyleSheet("""
            QProgressBar {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 5px;
            }
        """)

        char_count_layout.addWidget(self.char_count_progress)
        main_layout.addWidget(char_count_frame)

        # Connect text changed signal to update character count
        self.message_input.textChanged.connect(self.update_char_count)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet('''
            QPushButton {
                background-color: #e74c3c;
                min-width: 120px;
            }
        ''')
        cancel_button.clicked.connect(self.cancel_request)

        submit_button = QPushButton("Submit Request")
        submit_button.setStyleSheet('''
            QPushButton {
                background-color: #2ecc71;
                min-width: 120px;
            }
        ''')
        submit_button.clicked.connect(self.submit_request)

        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(submit_button)

        main_layout.addLayout(button_layout)

    def update_char_count(self):
        """
        Update the character count label and progress bar.
        """
        count = len(self.message_input.toPlainText())
        color = "#2c3e50"  # Default dark blue
        progress_color = "#3498db"  # Default blue

        if count > 400:
            color = "#f39c12"  # Warning yellow
            progress_color = "#f39c12"
        if count > 500:
            color = "#e74c3c"  # Error red
            progress_color = "#e74c3c"

        self.char_count_label.setText(f"{count}/500 characters")
        self.char_count_label.setStyleSheet(f"color: {color}; font-size: 11pt; font-weight: bold;")

        # Update progress bar
        self.char_count_progress.setValue(count)
        self.char_count_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background-color: {progress_color};
                border-radius: 5px;
            }}
        """)

    def set_faculty(self, faculty):
        """
        Set the faculty for the consultation request.
        """
        self.faculty = faculty

        # Update the combo box
        if self.faculty and self.faculty_combo.count() > 0:
            for i in range(self.faculty_combo.count()):
                faculty_id = self.faculty_combo.itemData(i)
                if faculty_id == self.faculty.id:
                    self.faculty_combo.setCurrentIndex(i)
                    break

    def set_faculty_options(self, faculty_list):
        """
        Set the available faculty options in the dropdown.
        Handles both faculty objects and dictionaries.
        """
        self.faculty_options = faculty_list
        self.faculty_combo.clear()

        for faculty in faculty_list:
            # Handle both faculty objects and dictionaries
            if isinstance(faculty, dict):
                faculty_name = faculty.get('name', 'Unknown')
                faculty_department = faculty.get('department', 'Unknown')
                faculty_id = faculty.get('id')
            else:
                # Legacy support for faculty objects
                faculty_name = faculty.name
                faculty_department = faculty.department
                faculty_id = faculty.id

            self.faculty_combo.addItem(f"{faculty_name} ({faculty_department})", faculty_id)

        # If we have a selected faculty, select it in the dropdown
        if self.faculty:
            faculty_id_to_find = self.faculty.id if hasattr(self.faculty, 'id') else self.faculty.get('id')
            for i in range(self.faculty_combo.count()):
                combo_faculty_id = self.faculty_combo.itemData(i)
                if combo_faculty_id == faculty_id_to_find:
                    self.faculty_combo.setCurrentIndex(i)
                    break

    def get_selected_faculty(self):
        """
        Get the selected faculty from the dropdown.
        """
        if self.faculty_combo.count() == 0:
            return self.faculty

        faculty_id = self.faculty_combo.currentData()

        for faculty in self.faculty_options:
            if faculty.id == faculty_id:
                return faculty

        return None

    def submit_request(self):
        """
        Handle the submission of the consultation request with enhanced validation.
        """
        # Validate faculty selection
        faculty = self.get_selected_faculty()
        if not faculty:
            self.show_validation_error("Faculty Selection", "Please select a faculty member.")
            self.faculty_combo.setFocus()
            return

        # Check if faculty is available
        if hasattr(faculty, 'status') and not faculty.status:
            self.show_validation_error("Faculty Availability",
                f"Faculty {faculty.name} is currently unavailable. Please select an available faculty member.")
            self.faculty_combo.setFocus()
            return

        # Validate message content
        message = self.message_input.toPlainText().strip()
        if not message:
            self.show_validation_error("Consultation Details", "Please enter consultation details.")
            self.message_input.setFocus()
            return

        # Check message length
        if len(message) > 500:
            self.show_validation_error("Message Length",
                "Consultation details are too long. Please limit to 500 characters.")
            self.message_input.setFocus()
            return

        # Check message minimum length for meaningful content
        if len(message) < 10:
            self.show_validation_error("Message Content",
                "Please provide more details about your consultation request (minimum 10 characters).")
            self.message_input.setFocus()
            return

        # Validate course code format if provided
        course_code = self.course_input.text().strip()
        if course_code and not self.is_valid_course_code(course_code):
            self.show_validation_error("Course Code Format",
                "Please enter a valid course code (e.g., CS101, MATH202).")
            self.course_input.setFocus()
            return

        # All validation passed, emit signal with the request details
        self.request_submitted.emit(faculty, message, course_code)

    def show_validation_error(self, title, message):
        """
        Show a validation error message using the standardized notification system.

        Args:
            title (str): Error title
            message (str): Error message
        """
        try:
            # Try to use the notification manager
            from ..utils.notification import NotificationManager
            NotificationManager.show_message(
                self,
                title,
                message,
                NotificationManager.WARNING
            )
        except ImportError:
            # Fallback to basic implementation
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Validation Error")
            error_dialog.setIcon(QMessageBox.Warning)
            error_dialog.setText(f"<b>{title}</b>")
            error_dialog.setInformativeText(message)
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.setDefaultButton(QMessageBox.Ok)
            error_dialog.setStyleSheet("""
                QMessageBox {
                    background-color: #f8f9fa;
                }
                QLabel {
                    color: #212529;
                    font-size: 12pt;
                }
                QPushButton {
                    background-color: #0d3b66;
                    color: white;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #0a2f52;
                }
            """)
            error_dialog.exec_()

    def is_valid_course_code(self, course_code):
        """
        Validate course code format.

        Args:
            course_code (str): Course code to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Basic validation: 2-4 letters followed by 3-4 numbers, optionally followed by a letter
        import re
        pattern = r'^[A-Za-z]{2,4}\d{3,4}[A-Za-z]?$'

        # Allow common formats like CS101, MATH202, ENG101A
        return bool(re.match(pattern, course_code))

    def cancel_request(self):
        """
        Cancel the consultation request.
        """
        self.message_input.clear()
        self.course_input.clear()
        self.setVisible(False)

class ConsultationHistoryPanel(QFrame):
    """
    Panel to display consultation history.
    """
    consultation_selected = pyqtSignal(object)
    consultation_cancelled = pyqtSignal(int)

    def __init__(self, student=None, parent=None):
        super().__init__(parent)
        self.student = student
        self.consultations = []
        self.init_ui()

    def init_ui(self):
        """
        Initialize the consultation history panel UI.
        """
        # Import theme system
        from ..utils.theme import ConsultEaseTheme

        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("consultation_history_panel")

        # Apply theme-based stylesheet with further improved readability
        self.setStyleSheet('''
            QFrame#consultation_history_panel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 20px;
            }
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 5px;
                background-color: white;
                alternate-background-color: #f1f3f5;
                gridline-color: #dee2e6;
                font-size: 16pt;
                color: #212529;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #e9ecef;
            }
            QHeaderView::section {
                background-color: #228be6;
                color: white;
                padding: 15px;
                border: none;
                font-size: 16pt;
                font-weight: bold;
            }
            QHeaderView::section:first {
                border-top-left-radius: 5px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 5px;
            }
            /* Improve scrollbar visibility */
            QScrollBar:vertical {
                background: #f1f3f5;
                width: 15px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #868e96;
            }
            QPushButton {
                border-radius: 5px;
                padding: 12px 20px;
                font-size: 15pt;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        ''')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("My Consultation History")
        title_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title_label)

        # Consultation table
        self.consultation_table = QTableWidget()
        self.consultation_table.setColumnCount(5)
        self.consultation_table.setHorizontalHeaderLabels(["Faculty", "Course", "Status", "Date", "Actions"])
        self.consultation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.consultation_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.consultation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.consultation_table.setSelectionMode(QTableWidget.SingleSelection)
        self.consultation_table.setAlternatingRowColors(True)

        main_layout.addWidget(self.consultation_table)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet('''
            QPushButton {
                background-color: #3498db;
                min-width: 120px;
            }
        ''')
        refresh_button.clicked.connect(self.refresh_consultations)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(refresh_button)

        main_layout.addLayout(button_layout)

    def set_student(self, student):
        """
        Set the student for the consultation history.
        """
        self.student = student
        self.refresh_consultations()

    def refresh_consultations(self):
        """
        Refresh the consultation history from the database with loading indicator.
        """
        if not self.student:
            return

        # Get student ID from either object or dictionary
        if isinstance(self.student, dict):
            student_id = self.student.get('id')
        else:
            # Legacy support for student objects
            student_id = getattr(self.student, 'id', None)

        if not student_id:
            return

        try:
            # Import notification utilities
            from ..utils.notification import LoadingDialog, NotificationManager

            # Define the operation to run with progress updates
            def load_consultations(progress_callback):
                # Import consultation controller
                from ..controllers import ConsultationController

                # Update progress
                progress_callback(10, "Connecting to database...")

                # Get consultation controller
                consultation_controller = ConsultationController()

                # Update progress
                progress_callback(30, "Fetching consultation data...")

                # Get consultations for this student
                consultations = consultation_controller.get_consultations(student_id=student_id)

                # Update progress
                progress_callback(80, "Processing results...")

                # Simulate a short delay for better UX
                import time
                time.sleep(0.5)

                # Update progress
                progress_callback(100, "Complete!")

                return consultations

            # Show loading dialog while fetching consultations
            self.consultations = LoadingDialog.show_loading(
                self,
                load_consultations,
                title="Refreshing Consultations",
                message="Loading your consultation history...",
                cancelable=True
            )

            # Update the table with the results
            self.update_consultation_table()

        except Exception as e:
            logger.error(f"Error refreshing consultations: {str(e)}")

            try:
                # Use notification manager if available
                from ..utils.notification import NotificationManager
                NotificationManager.show_message(
                    self,
                    "Error",
                    f"Failed to refresh consultation history: {str(e)}",
                    NotificationManager.ERROR
                )
            except ImportError:
                # Fallback to basic message box
                QMessageBox.warning(self, "Error", f"Failed to refresh consultation history: {str(e)}")

    def update_consultation_table(self):
        """
        Update the consultation table with the current consultations.
        """
        # Clear the table
        self.consultation_table.setRowCount(0)

        # Add consultations to the table
        for consultation in self.consultations:
            row_position = self.consultation_table.rowCount()
            self.consultation_table.insertRow(row_position)

            # Faculty name
            faculty_item = QTableWidgetItem(consultation.faculty.name)
            self.consultation_table.setItem(row_position, 0, faculty_item)

            # Course code
            course_item = QTableWidgetItem(consultation.course_code if consultation.course_code else "N/A")
            self.consultation_table.setItem(row_position, 1, course_item)

            # Status with enhanced color coding and improved contrast
            status_item = QTableWidgetItem(consultation.status.value.capitalize())

            # Define status colors with better contrast and accessibility
            status_colors = {
                "pending": {
                    "bg": QColor(255, 193, 7),    # Amber (darker yellow)
                    "fg": QColor(0, 0, 0),        # Black text for contrast
                    "border": "#f08c00"           # Darker border for definition
                },
                "accepted": {
                    "bg": QColor(40, 167, 69),    # Enhanced green
                    "fg": QColor(255, 255, 255),  # White text for contrast
                    "border": "#2b8a3e"           # Darker border for definition
                },
                "completed": {
                    "bg": QColor(0, 123, 255),    # Enhanced blue
                    "fg": QColor(255, 255, 255),  # White text for contrast
                    "border": "#1864ab"           # Darker border for definition
                },
                "cancelled": {
                    "bg": QColor(220, 53, 69),    # Enhanced red
                    "fg": QColor(255, 255, 255),  # White text for contrast
                    "border": "#a61e4d"           # Darker border for definition
                }
            }

            # Apply the appropriate color scheme
            status_value = consultation.status.value
            if status_value in status_colors:
                colors = status_colors[status_value]
                status_item.setBackground(colors["bg"])
                status_item.setForeground(colors["fg"])

                # Apply custom styling with border for better definition
                status_item.setData(
                    Qt.UserRole,
                    f"border: 2px solid {colors['border']}; border-radius: 4px; padding: 4px;"
                )

            # Make text bold and slightly larger for better readability
            font = status_item.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            status_item.setFont(font)
            self.consultation_table.setItem(row_position, 2, status_item)

            # Date
            date_str = consultation.requested_at.strftime("%Y-%m-%d %H:%M")
            date_item = QTableWidgetItem(date_str)
            self.consultation_table.setItem(row_position, 3, date_item)

            # Actions
            actions_cell = QWidget()
            actions_layout = QHBoxLayout(actions_cell)
            actions_layout.setContentsMargins(2, 2, 2, 2)

            # View details button
            view_button = QPushButton("View")
            view_button.setStyleSheet("background-color: #3498db; color: white;")
            # Use a better lambda that ignores the checked parameter
            view_button.clicked.connect(lambda _, c=consultation: self.view_consultation_details(c))
            actions_layout.addWidget(view_button)

            # Cancel button (only for pending consultations)
            if consultation.status.value == "pending":
                cancel_button = QPushButton("Cancel")
                cancel_button.setStyleSheet("background-color: #e74c3c; color: white;")
                # Use a better lambda that ignores the checked parameter
                cancel_button.clicked.connect(lambda _, c=consultation: self.cancel_consultation(c))
                actions_layout.addWidget(cancel_button)

            self.consultation_table.setCellWidget(row_position, 4, actions_cell)

    def view_consultation_details(self, consultation):
        """
        Show consultation details in a dialog.
        """
        dialog = ConsultationDetailsDialog(consultation, self)
        dialog.exec_()

    def cancel_consultation(self, consultation):
        """
        Cancel a pending consultation with improved confirmation dialog.
        """
        try:
            # Try to use the notification manager for confirmation
            from ..utils.notification import NotificationManager

            # Show confirmation dialog
            if NotificationManager.show_confirmation(
                self,
                "Cancel Consultation",
                f"Are you sure you want to cancel your consultation request with {consultation.faculty.name}?",
                "Yes, Cancel",
                "No, Keep It"
            ):
                # Emit signal to cancel the consultation
                self.consultation_cancelled.emit(consultation.id)

        except ImportError:
            # Fallback to basic confirmation dialog
            reply = QMessageBox.question(
                self,
                "Cancel Consultation",
                f"Are you sure you want to cancel your consultation request with {consultation.faculty.name}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Emit signal to cancel the consultation
                self.consultation_cancelled.emit(consultation.id)

class ConsultationDetailsDialog(QDialog):
    """
    Dialog to display consultation details.
    """
    def __init__(self, consultation, parent=None):
        super().__init__(parent)
        self.consultation = consultation
        self.init_ui()

    def init_ui(self):
        """
        Initialize the dialog UI.
        """
        # Import theme system
        from ..utils.theme import ConsultEaseTheme

        self.setWindowTitle("Consultation Details")
        self.setMinimumWidth(650)
        self.setMinimumHeight(550)
        self.setObjectName("consultation_details_dialog")

        # Apply theme-based stylesheet with improved readability
        self.setStyleSheet('''
            QDialog#consultation_details_dialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 15pt;
                color: #212529;
            }
            QLabel[heading="true"] {
                font-size: 20pt;
                font-weight: bold;
                color: #228be6;
                margin-bottom: 10px;
            }
            QFrame {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: white;
                padding: 20px;
                margin: 5px 0;
            }
            QPushButton {
                border-radius: 5px;
                padding: 12px 20px;
                font-size: 15pt;
                font-weight: bold;
                color: white;
                background-color: #228be6;
            }
            QPushButton:hover {
                background-color: #1971c2;
            }
        ''')

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Consultation Details")
        title_label.setProperty("heading", "true")
        layout.addWidget(title_label)

        # Details frame
        details_frame = QFrame()
        details_layout = QFormLayout(details_frame)
        details_layout.setSpacing(10)

        # Faculty
        faculty_label = QLabel("Faculty:")
        faculty_value = QLabel(self.consultation.faculty.name)
        faculty_value.setStyleSheet("font-weight: bold;")
        details_layout.addRow(faculty_label, faculty_value)

        # Department
        dept_label = QLabel("Department:")
        dept_value = QLabel(self.consultation.faculty.department)
        details_layout.addRow(dept_label, dept_value)

        # Course
        course_label = QLabel("Course:")
        course_value = QLabel(self.consultation.course_code if self.consultation.course_code else "N/A")
        details_layout.addRow(course_label, course_value)

        # Status with enhanced visual styling
        status_label = QLabel("Status:")
        status_value = QLabel(self.consultation.status.value.capitalize())

        # Define status colors with better contrast and accessibility
        status_styles = {
            "pending": {
                "color": "#000000",                # Black text
                "background": "#ffd43b",           # Bright yellow background
                "border": "2px solid #f08c00",     # Orange border
                "padding": "8px 12px",
                "border-radius": "6px"
            },
            "accepted": {
                "color": "#ffffff",                # White text
                "background": "#40c057",           # Bright green background
                "border": "2px solid #2b8a3e",     # Dark green border
                "padding": "8px 12px",
                "border-radius": "6px"
            },
            "completed": {
                "color": "#ffffff",                # White text
                "background": "#339af0",           # Bright blue background
                "border": "2px solid #1864ab",     # Dark blue border
                "padding": "8px 12px",
                "border-radius": "6px"
            },
            "cancelled": {
                "color": "#ffffff",                # White text
                "background": "#fa5252",           # Bright red background
                "border": "2px solid #c92a2a",     # Dark red border
                "padding": "8px 12px",
                "border-radius": "6px"
            }
        }

        # Apply the appropriate style
        status_value.setStyleSheet(f"""
            font-weight: bold;
            font-size: 16pt;
            color: {status_styles.get(self.consultation.status.value, {}).get("color", "#212529")};
            background-color: {status_styles.get(self.consultation.status.value, {}).get("background", "#e9ecef")};
            border: {status_styles.get(self.consultation.status.value, {}).get("border", "2px solid #adb5bd")};
            padding: {status_styles.get(self.consultation.status.value, {}).get("padding", "8px 12px")};
            border-radius: {status_styles.get(self.consultation.status.value, {}).get("border-radius", "6px")};
        """)
        details_layout.addRow(status_label, status_value)

        # Requested date
        requested_label = QLabel("Requested:")
        requested_value = QLabel(self.consultation.requested_at.strftime("%Y-%m-%d %H:%M"))
        details_layout.addRow(requested_label, requested_value)

        # Accepted date (if applicable)
        if self.consultation.accepted_at:
            accepted_label = QLabel("Accepted:")
            accepted_value = QLabel(self.consultation.accepted_at.strftime("%Y-%m-%d %H:%M"))
            details_layout.addRow(accepted_label, accepted_value)

        # Completed date (if applicable)
        if self.consultation.completed_at:
            completed_label = QLabel("Completed:")
            completed_value = QLabel(self.consultation.completed_at.strftime("%Y-%m-%d %H:%M"))
            details_layout.addRow(completed_label, completed_value)

        layout.addWidget(details_frame)

        # Message
        message_label = QLabel("Consultation Details:")
        message_label.setProperty("heading", "true")
        layout.addWidget(message_label)

        message_frame = QFrame()
        message_layout = QVBoxLayout(message_frame)

        message_text = QLabel(self.consultation.request_message)
        message_text.setWordWrap(True)
        message_layout.addWidget(message_text)

        layout.addWidget(message_frame)

        # Close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

class ConsultationPanel(QTabWidget):
    """
    Main consultation panel with request form and history tabs.
    Improved with better transitions and user feedback.
    """
    consultation_requested = pyqtSignal(object, str, str)
    consultation_cancelled = pyqtSignal(int)

    def __init__(self, student=None, parent=None):
        super().__init__(parent)
        self.student = student
        self.init_ui()

        # Set up auto-refresh timer for history panel
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_refresh_history)
        self.refresh_timer.start(60000)  # Refresh every minute

        # Connect tab change signal
        self.currentChanged.connect(self.on_tab_changed)

    def init_ui(self):
        """
        Initialize the consultation panel UI with improved styling and responsiveness.
        """
        # Import theme system
        from ..utils.theme import ConsultEaseTheme

        # Set object name for theme-based styling
        self.setObjectName("consultation_panel")

        # Create an enhanced stylesheet for the consultation panel
        enhanced_stylesheet = """
            QTabWidget#consultation_panel {
                background-color: #f8f9fa;
                border: none;
            }

            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: #f8f9fa;
                padding: 5px;
            }

            QTabBar::tab {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 12px 20px;
                margin-right: 4px;
                font-size: 15pt;
                font-weight: bold;
                min-width: 200px;
            }

            QTabBar::tab:selected {
                background-color: #228be6;
                color: white;
                border: 1px solid #1971c2;
                border-bottom: none;
            }

            QTabBar::tab:hover:!selected {
                background-color: #dee2e6;
            }

            QTabWidget::tab-bar {
                alignment: center;
            }
        """

        # Apply the enhanced stylesheet
        self.setStyleSheet(enhanced_stylesheet)

        # Request form tab with improved icon and text
        self.request_form = ConsultationRequestForm()
        self.request_form.request_submitted.connect(self.handle_consultation_request)
        self.addTab(self.request_form, "Request Consultation")

        # Set tab icon if available
        try:
            from PyQt5.QtGui import QIcon
            self.setTabIcon(0, QIcon("central_system/resources/icons/request.png"))
        except:
            # If icon not available, just use text
            pass

        # History tab with improved icon and text
        self.history_panel = ConsultationHistoryPanel(self.student)
        self.history_panel.consultation_cancelled.connect(self.handle_consultation_cancel)
        self.addTab(self.history_panel, "Consultation History")

        # Set tab icon if available
        try:
            from PyQt5.QtGui import QIcon
            self.setTabIcon(1, QIcon("central_system/resources/icons/history.png"))
        except:
            # If icon not available, just use text
            pass

        # Calculate responsive minimum size based on screen dimensions
        screen_width = QApplication.desktop().screenGeometry().width()
        screen_height = QApplication.desktop().screenGeometry().height()

        # Calculate responsive minimum size (smaller on small screens, larger on big screens)
        min_width = min(900, max(500, int(screen_width * 0.5)))
        min_height = min(700, max(400, int(screen_height * 0.6)))

        self.setMinimumSize(min_width, min_height)

        # Set size policy for better responsiveness
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add smooth transition animation for tab changes
        self.setTabPosition(QTabWidget.North)
        self.tabBar().setDrawBase(False)

    def set_student(self, student):
        """
        Set the student for the consultation panel.
        """
        self.student = student
        self.history_panel.set_student(student)

        # Update window title with student name
        if student and hasattr(self.parent(), 'setWindowTitle'):
            # Handle both student object and student data dictionary
            if isinstance(student, dict):
                student_name = student.get('name', 'Student')
            else:
                # Legacy support for student objects
                student_name = getattr(student, 'name', 'Student')
            self.parent().setWindowTitle(f"ConsultEase - {student_name}")

    def set_faculty(self, faculty):
        """
        Set the faculty for the consultation request.
        """
        self.request_form.set_faculty(faculty)

        # Animate transition to request form tab
        self.animate_tab_change(0)

    def set_faculty_options(self, faculty_list):
        """
        Set the available faculty options in the dropdown.
        """
        self.request_form.set_faculty_options(faculty_list)

        # Update status message if no faculty available
        if not faculty_list:
            QMessageBox.information(
                self,
                "No Faculty Available",
                "There are no faculty members available at this time. Please try again later."
            )

    def set_faculty_safe(self, faculty_data):
        """
        Set the faculty for the consultation request using safe dictionary data.

        Args:
            faculty_data (dict): Faculty data dictionary
        """
        # Create a mock faculty object for compatibility
        class MockFaculty:
            def __init__(self, data):
                self.id = data.get('id')
                self.name = data.get('name', 'Unknown')
                self.department = data.get('department', 'Unknown')
                self.status = data.get('status', False)
                self.email = data.get('email', '')

        mock_faculty = MockFaculty(faculty_data)
        self.set_faculty(mock_faculty)

    def set_faculty_options_safe(self, faculty_list):
        """
        Set the available faculty options using safe dictionary data.

        Args:
            faculty_list (list): List of faculty data dictionaries
        """
        self.set_faculty_options(faculty_list)

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request submission with improved feedback.
        """
        try:
            # Try to import notification manager
            try:
                from ..utils.notification import NotificationManager, LoadingDialog
                use_notification_manager = True
            except ImportError:
                use_notification_manager = False

            # Define the operation to run with progress updates
            def submit_request(progress_callback=None):
                if progress_callback:
                    progress_callback(20, "Submitting request...")

                # Emit signal to controller
                self.consultation_requested.emit(faculty, message, course_code)

                if progress_callback:
                    progress_callback(60, "Processing submission...")

                # Clear form fields
                self.request_form.message_input.clear()
                self.request_form.course_input.clear()

                if progress_callback:
                    progress_callback(80, "Refreshing history...")

                # Refresh history
                self.history_panel.refresh_consultations()

                if progress_callback:
                    progress_callback(100, "Complete!")

                return True

            # Use loading dialog if available
            if use_notification_manager:
                # Show loading dialog while submitting
                LoadingDialog.show_loading(
                    self,
                    submit_request,
                    title="Submitting Request",
                    message="Submitting your consultation request...",
                    cancelable=False
                )

                # Show success message
                NotificationManager.show_message(
                    self,
                    "Request Submitted",
                    f"Your consultation request with {faculty.name} has been submitted successfully.",
                    NotificationManager.SUCCESS
                )
            else:
                # Fallback to basic implementation
                submit_request()

                # Show success message
                QMessageBox.information(
                    self,
                    "Consultation Request Submitted",
                    f"Your consultation request with {faculty.name} has been submitted successfully."
                )

            # Animate transition to history tab
            self.animate_tab_change(1)

        except Exception as e:
            logger.error(f"Error submitting consultation request: {str(e)}")

            # Show error message
            try:
                from ..utils.notification import NotificationManager
                NotificationManager.show_message(
                    self,
                    "Submission Error",
                    f"Failed to submit consultation request: {str(e)}",
                    NotificationManager.ERROR
                )
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to submit consultation request: {str(e)}"
                )

    def handle_consultation_cancel(self, consultation_id):
        """
        Handle consultation cancellation with improved feedback.
        """
        try:
            # Try to import notification manager
            try:
                from ..utils.notification import NotificationManager, LoadingDialog
                use_notification_manager = True
            except ImportError:
                use_notification_manager = False

            # Define the operation to run with progress updates
            def cancel_consultation(progress_callback=None):
                if progress_callback:
                    progress_callback(30, "Cancelling request...")

                # Emit signal to controller
                self.consultation_cancelled.emit(consultation_id)

                if progress_callback:
                    progress_callback(70, "Updating records...")

                # Refresh history
                self.history_panel.refresh_consultations()

                if progress_callback:
                    progress_callback(100, "Complete!")

                return True

            # Use loading dialog if available
            if use_notification_manager:
                # Show confirmation dialog first
                if NotificationManager.show_confirmation(
                    self,
                    "Cancel Consultation",
                    "Are you sure you want to cancel this consultation request?",
                    "Yes, Cancel",
                    "No, Keep It"
                ):
                    # Show loading dialog while cancelling
                    LoadingDialog.show_loading(
                        self,
                        cancel_consultation,
                        title="Cancelling Request",
                        message="Cancelling your consultation request...",
                        cancelable=False
                    )

                    # Show success message
                    NotificationManager.show_message(
                        self,
                        "Request Cancelled",
                        "Your consultation request has been cancelled successfully.",
                        NotificationManager.SUCCESS
                    )
            else:
                # Fallback to basic implementation
                reply = QMessageBox.question(
                    self,
                    "Cancel Consultation",
                    "Are you sure you want to cancel this consultation request?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # Cancel the consultation
                    cancel_consultation()

                    # Show success message
                    QMessageBox.information(
                        self,
                        "Consultation Cancelled",
                        "Your consultation request has been cancelled successfully."
                    )

        except Exception as e:
            logger.error(f"Error cancelling consultation: {str(e)}")

            # Show error message
            try:
                from ..utils.notification import NotificationManager
                NotificationManager.show_message(
                    self,
                    "Cancellation Error",
                    f"Failed to cancel consultation: {str(e)}",
                    NotificationManager.ERROR
                )
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to cancel consultation: {str(e)}"
                )

    def animate_tab_change(self, tab_index):
        """
        Animate the transition to a different tab with enhanced visual effects.

        Args:
            tab_index (int): The index of the tab to switch to
        """
        # Import animation classes if available
        try:
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup

            # Create a property animation for the tab widget
            pos_animation = QPropertyAnimation(self, b"pos")
            pos_animation.setDuration(300)  # 300ms animation
            pos_animation.setStartValue(self.pos() + QPoint(10, 0))  # Slight offset
            pos_animation.setEndValue(self.pos())  # Original position
            pos_animation.setEasingCurve(QEasingCurve.OutCubic)  # Smooth curve

            # Create a parallel animation group
            animation_group = QParallelAnimationGroup()
            animation_group.addAnimation(pos_animation)

            # Start the animation
            animation_group.start()

            # Set the current tab
            self.setCurrentIndex(tab_index)

        except ImportError:
            # If animation classes are not available, use simpler animation
            # Set the current tab
            self.setCurrentIndex(tab_index)

            # Flash the tab briefly to draw attention
            try:
                current_style = self.tabBar().tabTextColor(tab_index)

                # Create a timer to reset the color after a brief flash
                def reset_color():
                    self.tabBar().setTabTextColor(tab_index, current_style)

                # Set highlight color
                self.tabBar().setTabTextColor(tab_index, QColor("#228be6"))

                # Reset after a short delay
                QTimer.singleShot(500, reset_color)
            except:
                # If even this fails, just change the tab without animation
                pass

    def on_tab_changed(self, index):
        """
        Handle tab change events.

        Args:
            index (int): The index of the newly selected tab
        """
        # Refresh history when switching to history tab
        if index == 1:  # History tab
            self.history_panel.refresh_consultations()

    def auto_refresh_history(self):
        """
        Automatically refresh the history panel periodically.
        """
        # Only refresh if the history tab is visible
        if self.currentIndex() == 1:
            self.history_panel.refresh_consultations()

    def refresh_history(self):
        """
        Refresh the consultation history.
        """
        self.history_panel.refresh_consultations()
