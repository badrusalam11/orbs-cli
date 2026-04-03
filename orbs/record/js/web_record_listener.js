// Remove existing listeners if any
if (window._record_cleanup) {
    window._record_cleanup();
}

// Global variables for recording - exposed to window for Python access
window.recordedActions = [];
let isRecording = true;
let recordingStartTime = Date.now();
let actionCounter = 0;

// Add CSS for highlight effect only
function addRecordingStyles() {
    if (document.getElementById('record-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'record-styles';
    style.textContent = `
        .recording-highlight {
            outline: 2px solid #dc3545 !important;
            outline-offset: 2px !important;
            animation: recordPulse 0.5s ease-out !important;
        }
        
        @keyframes recordPulse {
            0% { outline-color: #dc3545; }
            50% { outline-color: #ff6b7d; }
            100% { outline-color: #dc3545; }
        }
    `;
    document.head.appendChild(style);
}

// Highlight element briefly when action is recorded
function highlightElement(element) {
    element.classList.add('recording-highlight');
    setTimeout(() => {
        element.classList.remove('recording-highlight');
    }, 500);
}

// Get unique selector for an element
function getUniqueSelector(el) {
    if (el.id) return '#' + el.id;
    
    // Try to build a CSS selector
    let path = [];
    while (el.nodeType === 1 && el !== document.body) {
        let idx = 1, sib = el;
        while ((sib = sib.previousElementSibling)) {
            if (sib.nodeName === el.nodeName) idx++;
        }
        path.unshift(el.nodeName.toLowerCase() + (idx > 1 ? `:nth-of-type(${idx})` : ''));
        el = el.parentNode;
    }
    return path.join(' > ');
}

// Get XPath for element (same as spy)
function getXPath(el) {
    if (el === document.documentElement) return '//html';
    if (el === document.body) return '//body';
    
    if (el.id && el.id.trim() !== '') {
        return `//*[@id="${el.id}"]`;
    }
    
    let path = '';
    let current = el;
    
    while (current && current.nodeType === 1 && current !== document.documentElement) {
        let tagName = current.tagName.toLowerCase();
        
        if (current === document.body) {
            path = '//body' + path;
            break;
        }
        
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
    
    if (path.startsWith('//')) {
        return path;
    }
    return '//' + path.substring(1);
}

// Record an action
function recordAction(type, element, value = null, additionalData = {}) {
    if (!isRecording) return;
    
    actionCounter++;
    
    const selector = getUniqueSelector(element);
    const xpath = getXPath(element);
    const timestamp = Date.now() - recordingStartTime;
    
    // Enhanced attributes collection (same as spy listener)
    const attributes = {
        id: element.id || '',
        class: element.className || '',
        href: element.getAttribute('href') || '',
        text: (element.innerText || '').trim(),
        type: element.getAttribute('type') || '',
        placeholder: element.getAttribute('placeholder') || '',
        ariaLabel: element.getAttribute('aria-label') || '',
        name: element.getAttribute('name') || '',
        value: element.value || '',
        title: element.getAttribute('title') || '',
        role: element.getAttribute('role') || ''
    };
    
    const action = {
        id: actionCounter,
        type: type,
        timestamp: timestamp,
        element: {
            tagName: element.tagName.toLowerCase(),
            id: element.id || '',
            className: element.className || '',
            type: element.type || '',
            text: (element.innerText || '').trim().substring(0, 50), // Limit text length
            selector: selector,
            xpath: xpath,
            attributes: attributes
        },
        value: value,
        url: window.location.href,
        ...additionalData
    };
    
    window.recordedActions.push(action);
    
    // Highlight element
    highlightElement(element);
    
    // Log to console for Python to pick up
    console.log(`[ORBS_RECORD] ${JSON.stringify(action)}`);
}

// Click event listener
function handleClick(e) {
    const element = e.target;
    recordAction('click', element, null, {
        button: e.button, // 0=left, 1=middle, 2=right
        coordinates: { x: e.clientX, y: e.clientY }
    });
}

// Input event listener (for text input)
function handleInput(e) {
    const element = e.target;
    if (element.type === 'password') {
        recordAction('input', element, element.value); // record actual password, mask in output
    } else {
        recordAction('input', element, element.value);
    }
}

// Change event listener (for selects, checkboxes, etc.)
function handleChange(e) {
    const element = e.target;
    let value;

    if (element.type === 'password') {
        value = element.value; // record actual password, mask in output
    } else if (element.type === 'checkbox' || element.type === 'radio') {
        value = element.checked;
    } else if (element.tagName.toLowerCase() === 'select') {
        value = {
            value: element.value,
            text: element.options[element.selectedIndex]?.text || '',
            index: element.selectedIndex
        };
    } else {
        value = element.value;
    }
    
    recordAction('change', element, value);
}

// Keydown event listener (for special keys)
function handleKeyDown(e) {
    // Record special keys like Enter, Tab, Escape
    if (['Enter', 'Tab', 'Escape'].includes(e.key)) {
        recordAction('keypress', e.target, e.key, {
            keyCode: e.keyCode,
            ctrlKey: e.ctrlKey,
            shiftKey: e.shiftKey,
            altKey: e.altKey
        });
    }
}

// Page navigation listener
function handlePageChange() {
    recordAction('navigation', document.body, window.location.href, {
        title: document.title
    });
}

// Stop recording function
function stopRecording() {
    isRecording = false;
    
    // Final summary action
    const summaryAction = {
        type: 'summary',
        timestamp: Date.now() - recordingStartTime,
        totalActions: actionCounter,
        duration: Date.now() - recordingStartTime,
        finalUrl: window.location.href
    };
    
    console.log(`[ORBS_RECORD_SUMMARY] ${JSON.stringify(summaryAction)}`);
    console.log(`[ORBS_RECORD_END]`);
}

// Initialize recording
function initializeRecording() {
    // Add recording styles for highlight effect
    addRecordingStyles();
    
    // Add event listeners
    document.addEventListener('click', handleClick, true);
    document.addEventListener('input', handleInput, true);
    document.addEventListener('change', handleChange, true);
    document.addEventListener('keydown', handleKeyDown, true);
    
    // Listen for page navigation
    let currentUrl = window.location.href;
    setInterval(() => {
        if (window.location.href !== currentUrl) {
            currentUrl = window.location.href;
            handlePageChange();
        }
    }, 1000);
    
    // Record initial page load
    recordAction('page_load', document.body, window.location.href, {
        title: document.title
    });
    
    // Cleanup function
    window._record_cleanup = function() {
        document.removeEventListener('click', handleClick, true);
        document.removeEventListener('input', handleInput, true);
        document.removeEventListener('change', handleChange, true);
        document.removeEventListener('keydown', handleKeyDown, true);
    };
    
    console.log('[ORBS_RECORD_START]');
    console.log('[ORBS_RECORD] Recording initialized');
}

// Start recording
window._record_listeners_injected = true;
initializeRecording();