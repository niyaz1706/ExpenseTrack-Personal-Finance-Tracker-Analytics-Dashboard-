// Global utility functions for API requests and UI helpers
function showToast(message, type = 'success') {
    const toastEl = document.getElementById('liveToast');
    const toastMessage = document.getElementById('toastMessage');
    if (!toastEl || !toastMessage) return;

    toastEl.className = `toast align-items-center text-white border-0 shadow bg-${type}`;
    toastMessage.textContent = message;

    const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
    toast.show();
}

async function apiRequest(url, options = {}) {
    options.headers = options.headers || {};
    if (!options.headers['Content-Type'] && options.body) {
        options.headers['Content-Type'] = 'application/json';
    }
    options.headers['Accept'] = 'application/json';

    try {
        const response = await fetch(url, options);
        if (response.status === 401) {
            window.location.href = '/auth/login';
            return null;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Request failed with status ' + response.status);
        }
        return data;
    } catch (err) {
        showToast(err.message || 'An error occurred', 'danger');
        throw err;
    }
}
