# File: orbs/keyword/locator.py
"""
Locator utilities for element finding and management
Provides consistent locator handling across different automation types
"""

import os
import xml.etree.ElementTree as ET
from typing import Union, Dict, Any, List, Tuple
from selenium.webdriver.common.by import By
from pathlib import Path


class Locator:
    """Generic locator management for web and mobile automation"""
    
    def __init__(self, strategy: str, value: str, description: str = None):
        """
        Create a locator object
        
        Args:
            strategy: Locator strategy (id, xpath, css, etc.)
            value: Locator value
            description: Optional description for reporting
        """
        self.strategy = strategy.lower().strip()
        self.value = value.strip()
        self.description = description or f"{strategy}={value}"
        
        # Validate strategy
        valid_strategies = ['id', 'xpath', 'css', 'name', 'class', 'tag', 'link', 'partial_link']
        if self.strategy not in valid_strategies:
            raise ValueError(f"Unsupported locator strategy: {strategy}. "
                           f"Supported: {valid_strategies}")
    
    def to_selenium(self) -> tuple:
        """Convert to Selenium By tuple"""
        strategy_map = {
            'id': By.ID,
            'xpath': By.XPATH,
            'css': By.CSS_SELECTOR,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'link': By.LINK_TEXT,
            'partial_link': By.PARTIAL_LINK_TEXT
        }
        return strategy_map[self.strategy], self.value
    
    def to_appium(self) -> Dict[str, str]:
        """Convert to Appium locator dict"""
        appium_map = {
            'id': 'id',
            'xpath': 'xpath',
            'css': 'css selector',
            'name': 'name',
            'class': 'class name',
            'tag': 'tag name',
            'accessibility_id': 'accessibility id',
            'android_uiautomator': '-android uiautomator',
            'ios_predicate': '-ios predicate string',
            'ios_class_chain': '-ios class chain'
        }
        
        strategy = appium_map.get(self.strategy, self.strategy)
        return {'using': strategy, 'value': self.value}
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.strategy}={self.value}"
    
    def __repr__(self) -> str:
        """Developer representation"""
        return f"Locator('{self.strategy}', '{self.value}', '{self.description}')"
    
    @staticmethod
    def parse(locator_string: str) -> 'Locator':
        """
        Parse locator from string format
        
        Examples:
            Locator.parse("id=login-btn")
            Locator.parse("xpath=//button[text()='Submit']")
        """
        if '=' not in locator_string:
            # Default to ID if no strategy specified
            return Locator('id', locator_string)
        
        strategy, value = locator_string.split('=', 1)
        return Locator(strategy, value)
    
    @staticmethod
    def id(value: str, description: str = None) -> 'Locator':
        """Create ID locator"""
        return Locator('id', value, description)
    
    @staticmethod
    def xpath(value: str, description: str = None) -> 'Locator':
        """Create XPath locator"""
        return Locator('xpath', value, description)
    
    @staticmethod
    def css(value: str, description: str = None) -> 'Locator':
        """Create CSS selector locator"""
        return Locator('css', value, description)
    
    @staticmethod
    def name(value: str, description: str = None) -> 'Locator':
        """Create name locator"""
        return Locator('name', value, description)
    
    @staticmethod
    def class_name(value: str, description: str = None) -> 'Locator':
        """Create class name locator"""
        return Locator('class', value, description)
    
    @staticmethod
    def tag(value: str, description: str = None) -> 'Locator':
        """Create tag name locator"""
        return Locator('tag', value, description)
    
    @staticmethod
    def link_text(value: str, description: str = None) -> 'Locator':
        """Create link text locator"""
        return Locator('link', value, description)
    
    @staticmethod
    def partial_link_text(value: str, description: str = None) -> 'Locator':
        """Create partial link text locator"""
        return Locator('partial_link', value, description)


# Common locator collections for reuse
class CommonLocators:
    """Predefined common locators"""
    
    # Login form locators
    USERNAME = Locator.id("username", "Username input field")
    PASSWORD = Locator.id("password", "Password input field")
    LOGIN_BUTTON = Locator.xpath("//button[contains(text(), 'Login') or contains(text(), 'Sign In')]", "Login button")
    
    # Common buttons
    SUBMIT_BUTTON = Locator.xpath("//button[@type='submit' or contains(text(), 'Submit')]", "Submit button")
    CANCEL_BUTTON = Locator.xpath("//button[contains(text(), 'Cancel')]", "Cancel button")
    SAVE_BUTTON = Locator.xpath("//button[contains(text(), 'Save')]", "Save button")
    
    # Common elements
    ERROR_MESSAGE = Locator.css(".error, .alert-danger, .text-danger", "Error message")
    SUCCESS_MESSAGE = Locator.css(".success, .alert-success, .text-success", "Success message")
    LOADING_SPINNER = Locator.css(".spinner, .loading, .fa-spinner", "Loading spinner")


# Page Object Model helper
class PageElement:
    """Descriptor for page elements using locators"""
    
    def __init__(self, locator: Union[Locator, str], description: str = None):
        if isinstance(locator, str):
            self.locator = Locator.parse(locator)
        else:
            self.locator = locator
        
        if description:
            self.locator.description = description
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        # Return the locator string for use with Web keywords
        return str(self.locator)
    
    def __set_name__(self, owner, name):
        if not self.locator.description or self.locator.description == str(self.locator):
            # Auto-generate description from attribute name
            self.locator.description = name.replace('_', ' ').title()


# Example Page Object Model class
class LoginPage:
    """Example page object using PageElement descriptors"""
    
    username_field = PageElement(CommonLocators.USERNAME)
    password_field = PageElement(CommonLocators.PASSWORD)
    login_button = PageElement(CommonLocators.LOGIN_BUTTON)
    error_message = PageElement(CommonLocators.ERROR_MESSAGE)
    
    # Custom locators
    remember_me_checkbox = PageElement("id=remember-me", "Remember me checkbox")
    forgot_password_link = PageElement("xpath=//a[contains(text(), 'Forgot')]", "Forgot password link")


class WebElementEntity:
    """Represents a web element from the object repository XML"""
    
    def __init__(self, xml_path: str):
        """
        Parse WebElementEntity XML file from object repository
        
        Args:
            xml_path: Path to the XML file (relative to project root or absolute)
        """
        self.xml_path = xml_path
        self.name = ""
        self.tag = ""
        self.selector_collection: Dict[str, str] = {}
        self.selector_method = "XPATH"
        self.properties: Dict[str, str] = {}
        self._parse_xml()
    
    def _parse_xml(self):
        """Parse the XML file and extract locators"""
        # Normalize path to handle both forward slash and backslash
        # SMART FALLBACK: Automatically fix paths corrupted by escape sequences!
        
        sanitized_path = self.xml_path
        
        # Detect if path has been corrupted by escape sequences
        has_control_chars = any(ord(c) < 32 for c in sanitized_path if c not in '\n\r\t')
        
        if has_control_chars:
            # Path contains control characters - likely from escape sequences
            # FALLBACK: Reconstruct the original path by mapping control chars back to letters
            
            # Map control characters to the letter they represent + path separator
            escape_fix_map = {
                '\b': '/b',  # backspace (from \b) -> /b
                '\t': '/t',  # tab (from \t) -> /t
                '\n': '/n',  # newline (from \n) -> /n
                '\r': '/r',  # carriage return (from \r) -> /r
                '\f': '/f',  # form feed (from \f) -> /f
                '\v': '/v',  # vertical tab (from \v) -> /v
                '\a': '/a',  # bell (from \a) -> /a
                '\x00': '/0', # null
            }
            
            # Reconstruct the path
            fixed_path = sanitized_path
            for control_char, replacement in escape_fix_map.items():
                fixed_path = fixed_path.replace(control_char, replacement)
            
            # Clean up any remaining control characters (replace with /)
            import re
            fixed_path = re.sub(r'[\x00-\x1F\x7F]', '/', fixed_path)
            
            # Show helpful message
            print(f"[AUTO-FIX] Path auto-corrected from escape sequence issue:")
            print(f"  Original input: {repr(sanitized_path)}")
            print(f"  Corrected to: {fixed_path}")
            print(f"  Tip: Use forward slash (/) to avoid this: find_test_obj('{fixed_path}')")
            
            sanitized_path = fixed_path
        
        # Convert backslashes to forward slashes for consistency
        sanitized_path = sanitized_path.replace('\\', '/')
        
        # Normalize the path (but keep forward slashes on Windows for cross-platform)
        normalized_path = sanitized_path.replace('\\', '/').replace('//', '/')
        
        # Handle relative paths from project root
        if not os.path.isabs(normalized_path):
            # Try to find project root by looking for common markers
            current = Path.cwd()
            # Look for object_repository folder or project markers
            xml_file = None
            for parent in [current] + list(current.parents):
                potential_path = parent / normalized_path
                if potential_path.exists():
                    xml_file = potential_path
                    break
            
            if xml_file is None:
                # Try direct path from cwd
                xml_file = Path(normalized_path)
        else:
            xml_file = Path(normalized_path)
        
        if not xml_file.exists():
            # Provide helpful error message
            hint = (
                f"\n\n💡 Tip: Make sure the file exists and the path is correct.\n"
                f"   Looking for: {xml_file.absolute()}\n"
                f"   Working directory: {Path.cwd()}\n"
                f"\n"
                f"   Use forward slashes for cross-platform compatibility:\n"
                f"   find_test_obj(\"object_repository/your_file.xml\")"
            )
            raise FileNotFoundError(f"Object repository file not found: {normalized_path}{hint}")
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Extract basic info
        name_elem = root.find('name')
        if name_elem is not None:
            self.name = name_elem.text or ""
        
        tag_elem = root.find('tag')
        if tag_elem is not None:
            self.tag = tag_elem.text or ""
        
        # Extract selector collection
        selector_collection = root.find('selectorCollection')
        if selector_collection is not None:
            for entry in selector_collection.findall('entry'):
                key_elem = entry.find('key')
                value_elem = entry.find('value')
                if key_elem is not None and value_elem is not None:
                    key = key_elem.text
                    value = value_elem.text
                    if key and value:
                        self.selector_collection[key] = value
        
        # Extract selector method
        method_elem = root.find('selectorMethod')
        if method_elem is not None:
            self.selector_method = method_elem.text or "XPATH"
        
        # Extract web element properties
        for prop in root.findall('webElementProperties'):
            is_selected_elem = prop.find('isSelected')
            name_elem = prop.find('name')
            value_elem = prop.find('value')
            
            # Store properties that have values
            if name_elem is not None and value_elem is not None:
                name = name_elem.text
                value = value_elem.text
                
                if name and value and value.strip():
                    self.properties[name] = value
    
    def get_primary_locator(self) -> Tuple[str, str]:
        """
        Get the primary locator based on selector method
        
        Returns:
            Tuple of (strategy, value)
        """
        method = self.selector_method.upper()
        
        # Map XML selector method to Selenium strategy
        if method in self.selector_collection:
            value = self.selector_collection[method]
            
            if method == 'XPATH':
                return 'xpath', value
            elif method == 'CSS':
                return 'css', value
            elif method == 'ID':
                return 'id', value
            elif method == 'NAME':
                return 'name', value
            elif method == 'CLASS_NAME':
                return 'class', value
        
        # Fallback: use first available selector
        if self.selector_collection:
            first_key = next(iter(self.selector_collection))
            return first_key.lower(), self.selector_collection[first_key]
        
        return None, None
    
    def get_alternative_locators(self) -> List[Tuple[str, str]]:
        """
        Generate alternative locators for self-healing
        
        Returns:
            List of (strategy, value) tuples
        """
        alternatives = []
        
        # Add all selectors from selector collection (except primary)
        primary_method = self.selector_method.upper()
        for key, value in self.selector_collection.items():
            if key != primary_method and value:
                strategy = key.lower()
                if strategy in ['xpath', 'css', 'id', 'name', 'class_name']:
                    alternatives.append((strategy.replace('class_name', 'class'), value))
        
        # Build locators from properties
        props = self.properties
        
        # ID is most reliable
        if 'id' in props and props['id']:
            alternatives.append(('id', props['id']))
        
        # Name attribute
        if 'name' in props and props['name']:
            alternatives.append(('name', props['name']))
        
        # Build XPath from properties
        if self.tag:
            xpath_parts = []
            
            # Tag-based XPath
            if 'id' in props and props['id']:
                xpath = f"//{self.tag}[@id='{props['id']}']"
                xpath_parts.append(xpath)
            
            if 'name' in props and props['name']:
                xpath = f"//{self.tag}[@name='{props['name']}']"
                xpath_parts.append(xpath)
            
            if 'class' in props and props['class']:
                xpath = f"//{self.tag}[@class='{props['class']}']"
                xpath_parts.append(xpath)
            
            if 'type' in props and props['type']:
                xpath = f"//{self.tag}[@type='{props['type']}']"
                xpath_parts.append(xpath)
            
            if 'value' in props and props['value']:
                xpath = f"//{self.tag}[@value='{props['value']}']"
                xpath_parts.append(xpath)
            
            if 'text' in props and props['text']:
                xpath = f"//{self.tag}[text()='{props['text']}']"
                xpath_parts.append(xpath)
            
            # Combine multiple attributes for more specific matching
            if 'name' in props and 'type' in props:
                xpath = f"//{self.tag}[@name='{props['name']}' and @type='{props['type']}']"
                xpath_parts.append(xpath)
            
            for xpath in xpath_parts:
                if ('xpath', xpath) not in alternatives:
                    alternatives.append(('xpath', xpath))
        
        # Build CSS selectors from properties
        if self.tag:
            css_parts = []
            
            if 'id' in props and props['id']:
                css = f"{self.tag}#{props['id']}"
                css_parts.append(css)
            
            if 'class' in props and props['class']:
                classes = props['class'].split()
                css = f"{self.tag}.{'.'.join(classes)}"
                css_parts.append(css)
            
            if 'name' in props and props['name']:
                css = f"{self.tag}[name='{props['name']}']"
                css_parts.append(css)
            
            for css in css_parts:
                if ('css', css) not in alternatives:
                    alternatives.append(('css', css))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_alternatives = []
        for strategy, value in alternatives:
            key = (strategy, value)
            if key not in seen:
                seen.add(key)
                unique_alternatives.append((strategy, value))
        
        return unique_alternatives
    
    def get_all_locators(self) -> List[Tuple[str, str]]:
        """
        Get all locators (primary + alternatives) for self-healing
        
        Returns:
            List of (strategy, value) tuples ordered by priority
        """
        locators = []
        
        # Primary locator first
        primary = self.get_primary_locator()
        if primary[0] and primary[1]:
            locators.append(primary)
        
        # Then alternatives
        alternatives = self.get_alternative_locators()
        for alt in alternatives:
            if alt not in locators:
                locators.append(alt)
        
        return locators
    
    def __str__(self):
        """String representation"""
        strategy, value = self.get_primary_locator()
        return f"{strategy}={value}" if strategy else ""
    
    def __repr__(self):
        """Developer representation"""
        return f"WebElementEntity('{self.name}', primary={self.get_primary_locator()}, alternatives={len(self.get_alternative_locators())})"
