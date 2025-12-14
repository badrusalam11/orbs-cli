# File: orbs/keyword/locator.py
"""
Locator utilities for element finding and management
Provides consistent locator handling across different automation types
"""

from typing import Union, Dict, Any
from selenium.webdriver.common.by import By


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