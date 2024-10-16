// Mapping of Customer Journey and SERP Content Type stages to their respective colors
const customerJourneyColors = {
    'Awareness': '#63b3ed',       // Blue
    'Consideration': '#68d391',   // Green
    'Decision': '#ed8936',        // Orange
    'Retention': '#5a67d8'        // Indigo
};

const serpContentTypeColors = {
    'Amazon Product Page': '#6b46c1',  // Purple
    'Blog Category': '#3182ce',        // Blue
    'Blog Post': '#38a169',            // Green
    'Citation Site': '#ed8936',        // Orange
    'Homepage': '#63b3ed',             // Light Blue
    'Lead Generation': '#e53e3e',      // Red
    'Local Lander': '#dd6b20',         // Dark Orange
    'Product Category': '#d69e2e',     // Yellow
    'Product Page': '#48bb78',         // Green
    'Resource Guide': '#319795',       // Teal
    'Review Site': '#805ad5',          // Indigo
    'Site Info': '#9b2c2c',            // Dark Red
    'YouTube Video': '#d53f8c',        // Pink
    'Pinterest Page': '#ed64a6',       // Pinkish Red
    'Wikipedia': '#2c5282'             // Dark Blue
};

// Function to set the background color of the select element based on selected option
function updateSelectBackground(selectElement) {
    const selectedValue = selectElement.value;
    
    // Determine the appropriate color mapping based on the select element's class
    const color = selectElement.classList.contains('customer-journey-dropdown')
        ? customerJourneyColors[selectedValue] || '#2d3748'
        : serpContentTypeColors[selectedValue] || '#2d3748';

    selectElement.style.backgroundColor = color;
    selectElement.style.color = '#fff'; // Ensure text is readable
}

// Function to save the field
function saveField(element) {
    const id = element.dataset.id;        // Get the row ID
    const field = element.dataset.field;  // Get the field name
    let value;

    // Handle dropdowns (e.g., Customer Journey and SERP Content Type)
    if (element.tagName === 'SELECT') {
        value = element.value;  // Get the value from the dropdown
    } else if (element.classList.contains('multi-line')) {
        value = element.innerText.trim();  // For multi-line fields
    } else {
        value = element.textContent.trim();  // For single-line fields
    }

    // Field-specific validation
    if (field === 'pk_volume' || field === 'pk_ranking') {
        if (value === '') {
            value = null;  // Allow empty value to set as null
        } else if (!/^\d+$/.test(value)) {  // Simple integer validation
            alert('Please enter a valid number.');
            element.focus();  // Optionally, revert to previous value or keep editing
            return;
        } else {
            value = parseInt(value, 10);
        }
    }

    // Remove editing highlight
    element.classList.remove('editing');

    fetch(updateKeywordFieldUrl, {  // Use the JS variable defined in the template
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),  // Retrieve CSRF token via helper function
            'X-Requested-With': 'XMLHttpRequest'  // Ensure AJAX request is identified
        },
        body: JSON.stringify({
            'id': id,
            'value': value,
            'action': 'update',
            'field': field
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(field + ' updated successfully');
            if (element.tagName !== 'SELECT') {  // Only modify for non-select elements
                if (field === 'secondary_keywords') {
                    element.innerHTML = value ? value.replace(/\n/g, '<br>') : '';
                } else {
                    element.innerHTML = value || '';
                }
            }
            if (element.tagName === 'SELECT') {
                updateSelectBackground(element); // Update background color for dropdowns
            }
        } else {
            console.error('Failed to update ' + field + ':', data.error);
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An unexpected error occurred.');
    });
}

// Function to handle keydown events
function handleKeyDown(element, event) {
    const field = element.dataset.field;
    if (field === 'secondary_keywords') {
        if (event.altKey && event.key === "Enter") {
            event.preventDefault();  // Prevent default behavior
            // Insert line break at cursor position
            document.execCommand('insertText', false, '\n');
        } else if (event.key === "Enter") {
            event.preventDefault(); // Prevent default Enter key behavior
        }
    } else {
        if (event.key === "Enter") {
            event.preventDefault();  // Prevent inserting a newline
            element.blur();          // Trigger onblur to save the data
        }
    }
}

// Function to adjust the height of the editable span
function adjustHeight(element) {
    if (element.classList.contains('multi-line')) {
        element.style.height = 'auto';  // Reset the height to auto
    }
}

// Helper function to retrieve CSRF token from cookies
function getCSRFToken() {
    let cookieValue = null;
    const name = 'csrftoken';
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Add event listeners for editable spans and initialize select backgrounds
document.addEventListener('DOMContentLoaded', function() {
    const editableSpans = document.querySelectorAll('.editable-span');
    const customerJourneySelects = document.querySelectorAll('.customer-journey-dropdown');
    const serpContentTypeSelects = document.querySelectorAll('.serp-content-type-dropdown');

    // Initialize background colors for existing customer journey selects
    customerJourneySelects.forEach(select => {
        updateSelectBackground(select);
    });

    // Initialize background colors for existing SERP content type selects
    serpContentTypeSelects.forEach(select => {
        updateSelectBackground(select);
    });

    editableSpans.forEach(span => {
        // Show edit icon on hover
        span.addEventListener('mouseenter', () => {
            const icon = span.querySelector('.editable-icon');
            if (icon) {
                icon.style.opacity = '1';
            }
        });

        span.addEventListener('mouseleave', () => {
            const icon = span.querySelector('.editable-icon');
            if (icon && !span.classList.contains('editing')) {
                icon.style.opacity = '0';
            }
        });

        // Highlight the span when editing
        span.addEventListener('focus', () => {
            span.classList.add('editing');
            const icon = span.querySelector('.editable-icon');
            if (icon) {
                icon.style.opacity = '0';
            }

            // Remove extra empty elements
            if (span.classList.contains('multi-line')) {
                span.innerHTML = span.innerHTML.replace(/<br>/gi, '');
            }

            adjustHeight(span);
        });

        span.addEventListener('blur', () => {
            span.classList.remove('editing');
            const icon = span.querySelector('.editable-icon');
            if (icon) {
                icon.style.opacity = '0';
            }

            // Clean up extra empty lines
            if (span.classList.contains('multi-line')) {
                span.innerHTML = span.innerHTML.trim().replace(/(<br>\s*)+$/, '');
            }

            adjustHeight(span);
        });

        // Adjust height on input for multi-line fields
        span.addEventListener('input', () => {
            if (span.classList.contains('multi-line')) {
                adjustHeight(span);
            }
        });

        // Adjust height based on initial content
        if (span.classList.contains('multi-line')) {
            adjustHeight(span);
        }
    });

    // Update background color when dropdown value changes (Customer Journey and SERP Content Type)
    customerJourneySelects.forEach(select => {
        select.addEventListener('change', function() {
            updateSelectBackground(this);
        });
    });

    serpContentTypeSelects.forEach(select => {
        select.addEventListener('change', function() {
            updateSelectBackground(this);
        });
    });
});
