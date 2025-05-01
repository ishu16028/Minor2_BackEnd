// app/static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
  // Add event listeners and initialization code

  // Example: Flash message auto-dismiss
  const flashMessages = document.querySelectorAll('.alert');
  flashMessages.forEach(message => {
    setTimeout(() => {
      message.classList.add('fade-out');
      setTimeout(() => {
        message.remove();
      }, 500);
    }, 5000);
  });

  // Example: Form validation
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function(event) {
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;

      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          field.classList.add('is-invalid');
        } else {
          field.classList.remove('is-invalid');
        }
      });

      if (!isValid) {
        event.preventDefault();
      }
    });
  });
});