document.querySelector("form").addEventListener("submit", function(e) {
  const pw = document.getElementById("password").value;
  const cpw = document.getElementById("confirm_password").value;
  if (pw !== cpw) {
    e.preventDefault();
    alert("Passwords do not match.");
  }
});
document.getElementById("password").addEventListener("input", function () {
  const pw = this.value;
  const strengthIndicator = document.getElementById("strength-indicator");

  let strength = 0;
  if (pw.length >= 8) strength++;
  if (/[a-z]/.test(pw)) strength++;
  if (/[A-Z]/.test(pw)) strength++;
  if (/\d/.test(pw)) strength++;
  if (/[@$!%*?&]/.test(pw)) strength++;

  if (pw.length === 0) {
    strengthIndicator.textContent = "";
  } else if (strength <= 2) {
    strengthIndicator.textContent = "Weak";
    strengthIndicator.style.color = "red";
  } else if (strength <= 4) {
    strengthIndicator.textContent = "Medium";
    strengthIndicator.style.color = "orange";
  } else {
    strengthIndicator.textContent = "Strong";
    strengthIndicator.style.color = "green";
  }
});
