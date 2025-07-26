// Remove existing listeners if any
if (window._spy_cleanup) {
    window._spy_cleanup();
}

// Mouse move handler
function handleMouseMove(e) {
    if (window._last_hover) {
        window._last_hover.style.outline = '';
    }
    window._last_hover = e.target;
    e.target.style.outline = '2px solid blue';
}

// Keydown handler  
function handleKeyDown(e) {
    if (e.ctrlKey && e.code === 'Backquote') {
        e.preventDefault();
        const el = window._last_hover;
        if (!el) return;

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
            if (el.id !== "") return 'id("' + el.id + '")';
            if (el === document.body) return '/html/body';
            let ix = 0;
            const siblings = el.parentNode.childNodes;
            for (let i = 0; i < siblings.length; i++) {
                const sibling = siblings[i];
                if (sibling === el) {
                    const path = getXPath(el.parentNode) + '/' + el.tagName.toLowerCase();
                    return ix > 0 ? path + `[${ix + 1}]` : path;
                }
                if (sibling.nodeType === 1 && sibling.tagName === el.tagName) {
                    ix++;
                }
            }
        }

        const xpath = getXPath(el);
        const payload = {
            selector,
            xpath,
            tag: el.tagName.toLowerCase(),
            name: el.getAttribute('name') || '',
            text: el.innerText || '',
            attributes: {
                id: el.id || '',
                class: el.className || '',
                href: el.getAttribute('href') || '',
                text: el.innerText || '',
                type: el.getAttribute('type') || '',
                placeholder: el.getAttribute('placeholder') || '',
                ariaLabel: el.getAttribute('aria-label') || ''
            }
        };
        console.log('[SPY]' + JSON.stringify(payload));
    }
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
    window._spy_listeners_injected = false;
    if (window._last_hover) {
        window._last_hover.style.outline = '';
        window._last_hover = null;
    }
};

console.log('[SPY] Listeners injected successfully');