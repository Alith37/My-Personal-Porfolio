document.addEventListener('DOMContentLoaded', function() {
  // Mobile menu
  const hamburger = document.querySelector('.hamburger');
  const navList = document.querySelector('.nav-list');
  
  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navList.classList.toggle('active');
  });

  // Smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      document.querySelector(this.getAttribute('href')).scrollIntoView({
        behavior: 'smooth'
      });
    });
  });

  // Stats animation
  function animateStats() {
    document.querySelectorAll('.stat-num').forEach(stat => {
      const target = parseInt(stat.dataset.target);
      let count = 0;
      const increment = target / 100;
      
      const update = () => {
        if (count < target) {
          count += increment;
          stat.textContent = Math.floor(count);
          requestAnimationFrame(update);
        } else {
          stat.textContent = target;
        }
      };
      update();
    });
  }

  // Intersection Observer
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => { 
          if (entry.isIntersecting) {
        if (entry.target.querySelector('.stats')) {
          animateStats();
        }
      }
    });
  });

  document.querySelectorAll('.section').forEach(section => {
    observer.observe(section);
  });
});
