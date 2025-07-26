// Remove existing listeners if any
if (window._spy_cleanup) {
    window._spy_cleanup();
}

// Global variables
let blinkInterval = null;
let blinkTimeout = null;
let currentBlinkingElement = null;

// Mouse move handler
function handleMouseMove(e) {
    // Clear any existing blink animation when moving to new element
    if (window._last_hover && window._last_hover !== e.target) {
        clearBlinkAnimation();
        window._last_hover.style.outline = '';
        window._last_hover.style.boxShadow = '';
    }
    
    window._last_hover = e.target;
    
    // Only apply blue outline if not currently blinking
    if (currentBlinkingElement !== e.target) {
        e.target.style.outline = '2px solid blue';
    }
}

// Blink animation functions
function startBlinkAnimation(element) {
    // Clear any existing animation first
    clearBlinkAnimation();
    
    currentBlinkingElement = element;
    let isVisible = true;
    
    blinkInterval = setInterval(() => {
        if (currentBlinkingElement) {
            if (isVisible) {
                currentBlinkingElement.style.outline = '3px solid green'; // Fixed typo: 'gren' -> 'green'
                currentBlinkingElement.style.boxShadow = '0 0 10px rgba(0, 255, 30, 1)';
            } else {
                currentBlinkingElement.style.outline = '';
                currentBlinkingElement.style.boxShadow = '';
            }
            isVisible = !isVisible;
        }
    }, 300);
    
    // Stop blinking after 1 seconds
    blinkTimeout = setTimeout(() => {
        clearBlinkAnimation();
        // Return to blue outline if still the hovered element
        if (element === window._last_hover) {
            element.style.outline = '2px solid blue';
            element.style.boxShadow = '';
        }
        currentBlinkingElement = null;
    }, 1000);
}

function clearBlinkAnimation() {
    if (blinkInterval) {
        clearInterval(blinkInterval);
        blinkInterval = null;
    }
    
    if (blinkTimeout) {
        clearTimeout(blinkTimeout);
        blinkTimeout = null;
    }
    
    // Clear the outline and shadow from the blinking element
    if (currentBlinkingElement) {
        currentBlinkingElement.style.outline = '';
        currentBlinkingElement.style.boxShadow = '';
        currentBlinkingElement = null;
    }
}

// Keydown handler  
function handleKeyDown(e) {
    if (e.ctrlKey && e.code === 'Backquote') {
        e.preventDefault();
        const el = window._last_hover;
        if (!el) return;

        // Start blinking animation
        startBlinkAnimation(el);

        function uniqueSelector(el) {
            if (el.id) return '#' + el.id;
            let path = [];
            while (el.nodeType === 1 && el !== document.body) {
                let idx = 1, sib = el;
                while ((sib = sib.previousElementSibling)) if (sib.nodeName === el.nodeName) idx++;
                path.unshift(el.nodeName.toLowerCase() + (idx > 1 ? `:nth-of-type(${idx})` : ''));
                el = el.parentNode;
            }
            return path.join(' > ');
        }

        const selector = uniqueSelector(el);
        
        function getXPath(el) {
            // Handle special cases
            if (el === document.documentElement) return '//html';
            if (el === document.body) return '//body';
            
            // For elements with unique ID
            if (el.id && el.id.trim() !== '') {
                return `//*[@id="${el.id}"]`;
            }
            
            // Build path from root
            let path = '';
            let current = el;
            
            while (current && current.nodeType === 1 && current !== document.documentElement) {
                let tagName = current.tagName.toLowerCase();
                
                if (current === document.body) {
                    path = '//body' + path;
                    break;
                }
                
                // Count siblings with same tag name
                let siblings = Array.from(current.parentNode.children).filter(
                    sibling => sibling.tagName.toLowerCase() === tagName
                );
                
                if (siblings.length > 1) {
                    let index = siblings.indexOf(current) + 1;
                    path = `/${tagName}[${index}]` + path;
                } else {
                    path = `/${tagName}` + path;
                }
                
                current = current.parentNode;
            }
            
            // Ensure it starts with //
            return '//' + path.substring(1);
        }

        const xpath = getXPath(el);
        
        // Enhanced attributes collection
        const attributes = {
            id: el.id || '',
            class: el.className || '',
            href: el.getAttribute('href') || '',
            text: (el.innerText || '').trim(),
            type: el.getAttribute('type') || '',
            placeholder: el.getAttribute('placeholder') || '',
            ariaLabel: el.getAttribute('aria-label') || '',
            name: el.getAttribute('name') || '',
            value: el.value || '',
            title: el.getAttribute('title') || '',
            role: el.getAttribute('role') || ''
        };

        const payload = {
            selector,
            xpath,
            tag: el.tagName.toLowerCase(),
            name: el.getAttribute('name') || '',
            text: (el.innerText || '').trim(),
            attributes,
            // Additional metadata
            boundingBox: {
                x: el.offsetLeft,
                y: el.offsetTop,
                width: el.offsetWidth,
                height: el.offsetHeight
            },
            visible: el.offsetParent !== null,
            enabled: !el.disabled
        };
        
        console.log('[SPY]' + JSON.stringify(payload));
        
        // Optional: Show a visual confirmation
        showCaptureConfirmation(el);
    }
}

// Visual confirmation function
function showCaptureConfirmation(element) {
    // Create a temporary tooltip
    const tooltip = document.createElement('div');
    tooltip.innerHTML = '✓ Element Captured!';
    tooltip.style.cssText = `
        position: fixed;
        background: #28a745;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-family: Arial, sans-serif;
        z-index: 999999;
        pointer-events: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    `;
    
    // Position near the element
    const rect = element.getBoundingClientRect();
    tooltip.style.left = (rect.left + rect.width / 2 - 60) + 'px';
    tooltip.style.top = (rect.top - 40) + 'px';
    
    document.body.appendChild(tooltip);
    
    // Remove tooltip after 1.5 seconds
    setTimeout(() => {
        if (tooltip.parentNode) {
            tooltip.parentNode.removeChild(tooltip);
        }
    }, 1500);
}

// Add event listeners
document.addEventListener('mousemove', handleMouseMove, true);
document.addEventListener('keydown', handleKeyDown, true);

// Mark that listeners are injected
window._spy_listeners_injected = true;

// Cleanup function for removing listeners
window._spy_cleanup = function() {
    document.removeEventListener('mousemove', handleMouseMove, true);
    document.removeEventListener('keydown', handleKeyDown, true);
    clearBlinkAnimation();
    window._spy_listeners_injected = false;
    if (window._last_hover) {
        window._last_hover.style.outline = '';
        window._last_hover.style.boxShadow = '';
        window._last_hover = null;
    }
};

console.log('[SPY] Enhanced listeners injected successfully - Ctrl+` to capture elements');