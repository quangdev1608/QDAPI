// project-root/admin/static/js/base.js
document.addEventListener("DOMContentLoaded", () => {
  // Tự động ẩn các thông báo alert sau 5 giây
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.5s ease';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });
});
