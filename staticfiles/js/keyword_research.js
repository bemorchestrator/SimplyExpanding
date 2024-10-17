document.addEventListener('DOMContentLoaded', function () {
    const openModalButton = document.getElementById('openCreateModal');
    const closeModalButton = document.getElementById('closeCreateModal');
    const modal = document.getElementById('createDashboardModal');
    const firstInput = modal.querySelector('input, select, textarea, button');

    function openModal() {
        modal.classList.remove('hidden');
        if (firstInput) {
            firstInput.focus();
        }
    }

    function closeModal() {
        modal.classList.add('hidden');
        if (openModalButton) {
            openModalButton.focus();
        }
    }

    if (openModalButton) {
        openModalButton.addEventListener('click', openModal);
    }

    if (closeModalButton) {
        closeModalButton.addEventListener('click', closeModal);
    }

    window.addEventListener('click', function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    window.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });
});
