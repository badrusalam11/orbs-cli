// Remove existing listeners if any
if (window._spy_cleanup) {
    window._spy_cleanup();
}

// Global variables
let blinkInterval = null;
let blinkTimeout = null;
let currentBlinkingElement = null;
let infoBox = null;

// Create and show info box
function createInfoBox() {
    // Remove existing info box if any
    if (infoBox) {
        infoBox.remove();
    }
    
    infoBox = document.createElement('div');
    infoBox.id = 'spy-info-box';
    infoBox.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: #007bff; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">i</div>
            <span style="flex: 1;">🎯 <strong>Object Spy Active</strong> - Hover over elements and press <strong>Ctrl + \` or Cmd + \`</strong> to capture</span>
            <button id="spy-close-btn" style="background: none; border: none; color: #6c757d; cursor: pointer; font-size: 18px; padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">&times;</button>
        </div>
    `;
    
    infoBox.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
        border-bottom: 2px solid #007bff;
        padding: 12px 20px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        color: #495057;
        z-index: 999998;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        animation: slideDown 0.3s ease-out;
    `;
    
    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideDown {
            from {
                transform: translateY(-100%);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes slideUp {
            from {
                transform: translateY(0);
                opacity: 1;
            }
            to {
                transform: translateY(-100%);
                opacity: 0;
            }
        }
        
        .spy-slide-up {
            animation: slideUp 0.3s ease-out forwards;
        }
        
        #spy-close-btn:hover {
            background: rgba(108, 117, 125, 0.1) !important;
            border-radius: 50% !important;
        }
        
        kbd {
            box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
        }
    `;
    
    if (!document.getElementById('spy-styles')) {
        style.id = 'spy-styles';
        document.head.appendChild(style);
    }
    
    document.body.appendChild(infoBox);
    
    // Add close button functionality
    const closeBtn = document.getElementById('spy-close-btn');
    closeBtn.addEventListener('click', hideInfoBox);
    
    // Auto-hide after 10 seconds (optional)
    setTimeout(() => {
        if (infoBox && infoBox.parentNode) {
            showTemporaryMessage();
        }
    }, 10000);
}

// Hide info box with animation
function hideInfoBox() {
    if (infoBox) {
        infoBox.classList.add('spy-slide-up');
        setTimeout(() => {
            if (infoBox && infoBox.parentNode) {
                infoBox.remove();
                infoBox = null;
            }
        }, 300);
    }
}

// Show temporary reminder message
function showTemporaryMessage() {
    if (!infoBox) return;
    
    const originalContent = infoBox.innerHTML;
    infoBox.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: #28a745; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">✓</div>
            <span style="flex: 1;">🎯 Object Spy is still active. Press <strong>Ctrl + \` or Cmd + \`</strong> to capture elements</span>
            <button id="spy-close-btn-2" style="background: none; border: none; color: #6c757d; cursor: pointer; font-size: 18px; padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">&times;</button>
        </div>
    `;
    
    infoBox.style.background = 'linear-gradient(135deg, #d4edda 0%, #d1ecf1 100%)';
    infoBox.style.borderColor = '#28a745';
    
    // Re-add close functionality
    const closeBtn2 = document.getElementById('spy-close-btn-2');
    closeBtn2.addEventListener('click', hideInfoBox);
    
    // Hide after 5 more seconds
    setTimeout(hideInfoBox, 5000);
}

// Update capture confirmation to show counter
let captureCount = 0;
function updateCaptureCounter() {
    captureCount++;
    if (infoBox) {
        // Flash the info box briefly
        infoBox.style.background = 'linear-gradient(135deg, #d4edda 0%, #d1ecf1 100%)';
        infoBox.style.borderColor = '#28a745';
        
        setTimeout(() => {
            if (infoBox) {
                infoBox.style.background = 'linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%)';
                infoBox.style.borderColor = '#007bff';
            }
        }, 500);
    }
}

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
                currentBlinkingElement.style.outline = '3px solid green';
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
        
        // Update capture counter
        updateCaptureCounter();

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
    tooltip.innerHTML = `✓ Element Captured! (#${captureCount})`;
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
        animation: fadeInOut 1.5s ease-out forwards;
    `;
    
    // Add fade animation
    const fadeStyle = document.createElement('style');
    fadeStyle.textContent = `
        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateY(10px); }
            20% { opacity: 1; transform: translateY(0); }
            80% { opacity: 1; transform: translateY(0); }
            100% { opacity: 0; transform: translateY(-10px); }
        }
    `;
    document.head.appendChild(fadeStyle);
    
    // Position near the element
    const rect = element.getBoundingClientRect();
    tooltip.style.left = (rect.left + rect.width / 2 - 70) + 'px';
    tooltip.style.top = (rect.top - 40) + 'px';
    
    document.body.appendChild(tooltip);
    
    // Remove tooltip after animation
    setTimeout(() => {
        if (tooltip.parentNode) {
            tooltip.parentNode.removeChild(tooltip);
        }
        if (fadeStyle.parentNode) {
            fadeStyle.parentNode.removeChild(fadeStyle);
        }
    }, 1500);
}

// Add event listeners
document.addEventListener('mousemove', handleMouseMove, true);
document.addEventListener('keydown', handleKeyDown, true);

// Mark that listeners are injected
window._spy_listeners_injected = true;

// Create info box
createInfoBox();

// Cleanup function for removing listeners
window._spy_cleanup = function() {
    document.removeEventListener('mousemove', handleMouseMove, true);
    document.removeEventListener('keydown', handleKeyDown, true);
    clearBlinkAnimation();
    hideInfoBox();
    
    // Remove styles
    const spyStyles = document.getElementById('spy-styles');
    if (spyStyles) {
        spyStyles.remove();
    }
    
    window._spy_listeners_injected = false;
    if (window._last_hover) {
        window._last_hover.style.outline = '';
        window._last_hover.style.boxShadow = '';
        window._last_hover = null;
    }
    
    captureCount = 0;
};

console.log('[SPY] Enhanced listeners with info box injected successfully - Ctrl+` to capture elements');