// Custom JavaScript can go here.
// For now, we are mostly relying on HTMX.

document.body.addEventListener('htmx:beforeSwap', function(evt) {
    if (evt.detail.xhr.status === 422) {
        // alert("Unprocessable Entity");
    }
});
