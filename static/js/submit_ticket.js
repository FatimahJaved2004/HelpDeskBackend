document.addEventListener("DOMContentLoaded", function () {
  // Get the description textarea and character count display element
  const desc = document.getElementById("description");
  const count = document.getElementById("desc-count");

  // Update the character count on load and on input
  if (desc && count) {
    const updateCount = () => {
      count.textContent = `${desc.value.length} / 500 characters`;
    };

    updateCount(); // Initial count
    desc.addEventListener("input", updateCount); // Live update 
  }

  // Enable Bootstrap's custom validation styling
  const form = document.querySelector('form');
  if (form) {
    form.addEventListener('submit', function (e) {
      // If form is invalid, prevent submission and show validation feedback
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      // Add Bootstrap's validation class
      form.classList.add('was-validated');
    });
  }
});
