document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.table-row-link').forEach(function(row) {
    row.style.cursor = 'pointer';  // Change cursor to pointer
    row.addEventListener('click', function() {
      const href = this.getAttribute('data-href');
      if (href) {
        window.location = href;
      }
    });
  });
});
