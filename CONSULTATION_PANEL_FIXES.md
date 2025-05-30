# Consultation Panel and Faculty Card Fixes

## Overview

Based on the error logs showing consultation panel issues and faculty card callback problems, I have implemented comprehensive fixes to resolve the AttributeError issues and improve the consultation workflow.

## Issues Identified from Logs

### 1. **Consultation Panel AttributeError** ❌
```
AttributeError: 'dict' object has no attribute 'name'
File "/home/tripleajr/ConsultEaseVF/central_system/views/consultation_panel.py", line 302
self.faculty_combo.addItem(f"{faculty.name} ({faculty.department})", faculty.id)
```

### 2. **Faculty Card Callback Error** ❌
```
AttributeError: 'int' object has no attribute 'get'
File "/home/tripleajr/ConsultEaseVF/central_system/views/dashboard_window.py", line 1456
if not faculty_data.get('available', False):
```

### 3. **Qt Threading Issues** ⚠️
```
QObject::startTimer: Timers can only be used with threads started with QThread
```

### 4. **Faculty Status Updates Working** ✅
```
2025-05-30 19:11:02,644 - central_system.views.dashboard_window - INFO - Successfully populated faculty grid with 1 faculty cards (safe mode)
```

## Fixes Implemented

### 1. **Enhanced Consultation Panel Compatibility** ✅

#### **Problem**: Consultation panel expected faculty objects but received dictionaries
#### **Solution**: Enhanced `set_faculty_options` to handle both objects and dictionaries

```python
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
```

**Impact**: Eliminates AttributeError when populating faculty dropdown with dictionary data.

### 2. **Added Safe Methods to Consultation Panel** ✅

#### **Problem**: Missing safe methods for handling dictionary data
#### **Solution**: Added `set_faculty_safe` and `set_faculty_options_safe` methods

```python
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
```

**Impact**: Provides safe methods for handling dictionary data without breaking existing object-based code.

### 3. **Enhanced Faculty Card Callback Handling** ✅

#### **Problem**: Faculty card was passing faculty ID (integer) instead of faculty data
#### **Solution**: Enhanced callback to pass full faculty data when available

```python
def _on_consult_clicked(self):
    """Handle consultation button click."""
    if not self.faculty_id:
        logger.warning("Consultation requested but no faculty ID set")
        return

    # Emit signal with faculty ID
    self.consultation_requested.emit(self.faculty_id)

    # Call callback if provided
    if self.consultation_callback:
        try:
            # Pass the full faculty data if available, otherwise just the ID
            if hasattr(self, 'faculty_data') and self.faculty_data:
                self.consultation_callback(self.faculty_data)
            else:
                self.consultation_callback(self.faculty_id)
        except Exception as e:
            logger.error(f"Error in consultation callback: {e}")
```

**Impact**: Ensures consultation callbacks receive proper faculty data instead of just IDs.

### 4. **Robust Faculty Data Handling in Dashboard** ✅

#### **Problem**: `show_consultation_form_safe` couldn't handle integer faculty IDs
#### **Solution**: Enhanced method to handle both dictionaries and integers

```python
def show_consultation_form_safe(self, faculty_data):
    """
    Show the consultation request form for a specific faculty using safe dictionary data.

    Args:
        faculty_data (dict or int): Faculty data dictionary or faculty ID
    """
    # Handle case where faculty_data is passed as an integer (faculty ID)
    if isinstance(faculty_data, int):
        logger.debug(f"Faculty data passed as integer {faculty_data}, attempting to fetch faculty data")
        # Try to get faculty data from controller
        try:
            from ..controllers import FacultyController
            faculty_controller = FacultyController()
            faculty = faculty_controller.get_faculty_by_id(faculty_data)
            if faculty:
                # Convert to dictionary format
                faculty_data = {
                    'id': faculty.id,
                    'name': faculty.name,
                    'department': faculty.department,
                    'status': faculty.status,
                    'available': faculty.status or getattr(faculty, 'always_available', False),
                    'email': getattr(faculty, 'email', ''),
                    'room': getattr(faculty, 'room', None)
                }
            else:
                logger.error(f"Faculty with ID {faculty_data} not found")
                self.show_notification(f"Faculty with ID {faculty_data} not found", "error")
                return
        except Exception as e:
            logger.error(f"Error fetching faculty data for ID {faculty_data}: {e}")
            self.show_notification("Error loading faculty information", "error")
            return

    # Validate that faculty_data is now a dictionary
    if not isinstance(faculty_data, dict):
        logger.error(f"Invalid faculty data type: {type(faculty_data)}, expected dict")
        self.show_notification("Invalid faculty data", "error")
        return
```

**Impact**: Handles both dictionary data and integer IDs gracefully, preventing AttributeError crashes.

## System Status After Fixes

### **✅ Working Correctly**:
1. **Faculty Grid Population**: Successfully populating with 1 faculty member in safe mode
2. **Faculty Card Creation**: Cards are being created and displayed properly
3. **Safe Mode Operation**: No more SQLAlchemy session binding errors
4. **MQTT Subscriptions**: Successfully subscribing to all topics

### **🔧 Fixed Issues**:
1. **Consultation Panel**: Now handles both objects and dictionaries
2. **Faculty Card Callbacks**: Pass proper data instead of just IDs
3. **Dashboard Consultation Form**: Handles both data types gracefully
4. **Data Type Compatibility**: Robust handling of mixed data types

### **⚠️ Remaining Issues**:
1. **Qt Threading Warnings**: Still occurring but not causing crashes
2. **Database Health Checks**: Continuous restarts but system remains functional

## Expected Improvements

### **Immediate Benefits**:
- ✅ No more AttributeError crashes in consultation panel
- ✅ Faculty consultation requests work properly
- ✅ Robust data handling across the system
- ✅ Better error messages and user feedback

### **User Experience Benefits**:
- ✅ Consultation requests can be initiated successfully
- ✅ Faculty dropdown populates correctly
- ✅ Better error handling with informative messages
- ✅ Consistent behavior across different data sources

## Testing Recommendations

### **Immediate Testing**:
1. **Click on faculty cards** to test consultation request functionality
2. **Check consultation panel** for proper faculty dropdown population
3. **Verify error handling** when faculty is unavailable
4. **Monitor logs** for AttributeError elimination

### **Functional Testing**:
1. **Test consultation workflow** end-to-end
2. **Verify faculty selection** in dropdown works correctly
3. **Test with different faculty statuses** (available/unavailable)
4. **Check consultation form submission** works properly

## Monitoring Points

### **Success Indicators**:
- No more "AttributeError: 'dict' object has no attribute 'name'" errors
- No more "AttributeError: 'int' object has no attribute 'get'" errors
- Successful consultation request submissions
- Proper faculty dropdown population

### **Log Messages to Watch For**:
- `"Configured faculty card for: [Faculty Name]"` - Card configuration working
- `"Faculty data passed as integer [ID], attempting to fetch faculty data"` - ID handling working
- `"Successfully populated faculty grid with X faculty cards (safe mode)"` - Grid population working

## Conclusion

The implemented fixes address the critical consultation panel and faculty card issues:

1. **Data Type Compatibility**: Enhanced methods handle both objects and dictionaries
2. **Robust Error Handling**: Better validation and error messages
3. **Callback Improvements**: Faculty cards pass proper data to callbacks
4. **Safe Mode Integration**: Consistent use of safe dictionary data

The consultation workflow should now function properly without AttributeError crashes, allowing users to successfully request consultations with faculty members.

**Next Steps**: Test the consultation functionality thoroughly to ensure all workflows operate correctly.
