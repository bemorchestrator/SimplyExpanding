document.addEventListener('DOMContentLoaded', function () {
    // -------------------------------
    // Modal Handling
    // -------------------------------
    const openModalBtn = document.getElementById('openCreateModal');
    const closeModalBtn = document.getElementById('closeCreateModal');
    const modal = document.getElementById('createDashboardModal');

    if (openModalBtn) {
        openModalBtn.addEventListener('click', function () {
            modal.classList.remove('hidden');
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function () {
            modal.classList.add('hidden');
        });
    }

    window.addEventListener('click', function (event) {
        if (event.target === modal) {
            modal.classList.add('hidden');
        }
    });

    // -------------------------------
    // Inline Editing Handling
    // -------------------------------
    document.querySelectorAll('.editable').forEach(element => {
        element.addEventListener('change', function () {
            const id = this.getAttribute('data-id');
            const field = this.getAttribute('data-field');
            const value = this.value;

            fetch(UPDATE_FIELD_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({
                    id: id,
                    field_name: field,
                    new_value: value
                })
            }).then(response => response.json()).then(data => {
                if (data.success) {
                    console.log('Field updated successfully');
                } else {
                    console.error('Error updating field');
                }
            });
        });
    });
});
