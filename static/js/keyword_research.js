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
});
