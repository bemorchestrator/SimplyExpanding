// Mapping of Customer Journey stages to their respective colors
const customerJourneyColors = {
    'Awareness': '#63b3ed',       // Blue
    'Consideration': '#68d391',   // Green
    'Decision': '#ed8936',        // Orange
    'Retention': '#5a67d8'        // Indigo
};

// Function to set the background color of the select element based on selected option
function updateSelectBackground(selectElement) {
    const selectedValue = selectElement.value;
    const color = customerJourneyColors[selectedValue] || '#2d3748'; // Default color if not found
    selectElement.style.backgroundColor = color;
    selectElement.style.color = '#fff'; // Ensure text is readable
}

// Function to save the field
function saveField(element) {
    const id = element.dataset.id;        // Get the row ID
    const field = element.dataset.field;  // Get the field name
    let value;

    // Handle dropdowns (e.g., Customer Journey)
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

    fetch("{% url 'update_keyword_field' %}", {  // Changed URL to 'update_keyword_field'
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}',
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
                updateSelectBackground(element); // Update background color
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

// Add event listeners for editable spans and initialize select backgrounds
document.addEventListener('DOMContentLoaded', function() {
    const editableSpans = document.querySelectorAll('.editable-span');
    const customerJourneySelects = document.querySelectorAll('.customer-journey-dropdown');

    // Initialize background colors for existing selects
    customerJourneySelects.forEach(select => {
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

    // Update background color when dropdown value changes
    customerJourneySelects.forEach(select => {
        select.addEventListener('change', function() {
            updateSelectBackground(this);
        });
    });
});
