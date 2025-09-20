#!/usr/bin/env python
"""
Security utilities for Google Sheets MCP Server
"""

import logging
import time
from typing import Dict, Any, Optional
from functools import wraps
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 100, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
    
    def is_allowed(self) -> bool:
        """Check if a call is allowed within rate limits"""
        now = time.time()
        
        # Remove old calls outside the time window
        while self.calls and self.calls[0] <= now - self.time_window:
            self.calls.popleft()
        
        # Check if we're under the limit
        if len(self.calls) >= self.max_calls:
            return False
        
        # Add current call
        self.calls.append(now)
        return True
    
    def remaining_calls(self) -> int:
        """Get remaining calls in current window"""
        now = time.time()
        
        # Remove old calls
        while self.calls and self.calls[0] <= now - self.time_window:
            self.calls.popleft()
        
        return max(0, self.max_calls - len(self.calls))

# Global rate limiter
rate_limiter = RateLimiter(max_calls=100, time_window=60)

def rate_limit(max_calls: int = 10, time_window: int = 60):
    """Decorator for rate limiting function calls"""
    def decorator(func):
        func_rate_limiter = RateLimiter(max_calls, time_window)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not func_rate_limiter.is_allowed():
                raise Exception(f"Rate limit exceeded: {max_calls} calls per {time_window} seconds")
            return func(*args, **kwargs)
        return wrapper
    return decorator

class SecurityAuditor:
    """Audit logging for security events"""
    
    def __init__(self):
        self.events = []
    
    def log_event(self, event_type: str, details: Dict[str, Any], user_id: Optional[str] = None):
        """Log a security event"""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "details": details,
            "user_id": user_id
        }
        self.events.append(event)
        
        # Log to application logger
        logger.info(f"Security event: {event_type}", extra={"event": event})
    
    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> list:
        """Get recent security events"""
        events = self.events
        
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        
        return events[-limit:]

# Global security auditor
security_auditor = SecurityAuditor()

def audit_log(event_type: str):
    """Decorator for audit logging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract relevant information
            details = {
                "function": func.__name__,
                "args": str(args)[:200],  # Limit length
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
            }
            
            try:
                result = func(*args, **kwargs)
                security_auditor.log_event(event_type, {
                    **details,
                    "success": True
                })
                return result
            except Exception as e:
                security_auditor.log_event(event_type, {
                    **details,
                    "success": False,
                    "error": str(e)
                })
                raise
        return wrapper
    return decorator

class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_spreadsheet_id(spreadsheet_id: str) -> bool:
        """Validate Google Spreadsheet ID format"""
        if not spreadsheet_id or not isinstance(spreadsheet_id, str):
            return False
        
        # Google Spreadsheet IDs are typically 44 characters long
        # and contain alphanumeric characters, hyphens, and underscores
        if len(spreadsheet_id) < 20 or len(spreadsheet_id) > 100:
            return False
        
        # Check for potentially malicious characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        if any(char in spreadsheet_id for char in dangerous_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_sheet_name(sheet_name: str) -> bool:
        """Validate Google Sheet name"""
        if not sheet_name or not isinstance(sheet_name, str):
            return False
        
        # Sheet names have length limits
        if len(sheet_name) < 1 or len(sheet_name) > 100:
            return False
        
        # Check for invalid characters
        invalid_chars = ['[', ']', '*', '?', ':', '\\', '/', '\x00']
        if any(char in sheet_name for char in invalid_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_range(range_str: str) -> bool:
        """Validate A1 notation range"""
        if not range_str or not isinstance(range_str, str):
            return False
        
        # Basic A1 notation validation
        import re
        # Simple regex for A1 notation (e.g., A1, A1:B2, Sheet1!A1:B2)
        pattern = r'^[A-Za-z0-9_]+!?[A-Z]+\d+(:[A-Z]+\d+)?$'
        return bool(re.match(pattern, range_str))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format"""
        if not email or not isinstance(email, str):
            return False
        
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

def validate_inputs(**validations):
    """Decorator for input validation"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            validator = InputValidator()
            
            for param_name, validation_type in validations.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    
                    if validation_type == "spreadsheet_id":
                        if not validator.validate_spreadsheet_id(value):
                            raise ValueError(f"Invalid spreadsheet_id: {value}")
                    elif validation_type == "sheet_name":
                        if not validator.validate_sheet_name(value):
                            raise ValueError(f"Invalid sheet_name: {value}")
                    elif validation_type == "range":
                        if not validator.validate_range(value):
                            raise ValueError(f"Invalid range: {value}")
                    elif validation_type == "email":
                        if not validator.validate_email(value):
                            raise ValueError(f"Invalid email: {value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def sanitize_data(data: Any) -> Any:
    """Sanitize data for safe storage/transmission"""
    if isinstance(data, str):
        # Remove null bytes and other potentially dangerous characters
        data = data.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        # Limit length
        if len(data) > 10000:
            data = data[:10000] + "... [truncated]"
        return data
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data[:100]]  # Limit list size
    elif isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in list(data.items())[:50]}  # Limit dict size
    else:
        return data

class ErrorHandler:
    """Centralized error handling with security considerations"""
    
    @staticmethod
    def handle_google_api_error(error: Exception) -> Dict[str, Any]:
        """Handle Google API errors securely"""
        error_details = {
            "error_type": "google_api_error",
            "message": "An error occurred while communicating with Google APIs"
        }
        
        # Log the full error for debugging (but don't expose to client)
        logger.error(f"Google API error: {error}")
        
        # Check for specific error types
        error_str = str(error).lower()
        
        if "quota" in error_str or "limit" in error_str:
            error_details["message"] = "API quota exceeded. Please try again later."
            error_details["retry_after"] = 60
        elif "permission" in error_str or "forbidden" in error_str:
            error_details["message"] = "Insufficient permissions for this operation."
        elif "not found" in error_str:
            error_details["message"] = "The requested resource was not found."
        elif "invalid" in error_str:
            error_details["message"] = "Invalid request parameters."
        else:
            # Generic error message for unknown errors
            error_details["message"] = "An unexpected error occurred."
        
        return error_details
    
    @staticmethod
    def handle_validation_error(error: Exception) -> Dict[str, Any]:
        """Handle validation errors"""
        return {
            "error_type": "validation_error",
            "message": str(error)
        }
    
    @staticmethod
    def handle_rate_limit_error(error: Exception) -> Dict[str, Any]:
        """Handle rate limit errors"""
        return {
            "error_type": "rate_limit_error",
            "message": "Too many requests. Please slow down.",
            "retry_after": 60
        }
