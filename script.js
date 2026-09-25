document.addEventListener("DOMContentLoaded", function () {
  /* =========================================================
     MOBILE MENU
  ========================================================= */

  const hamburger = document.querySelector(".hamburger");
  const navList = document.querySelector(".nav-list");

  if (hamburger && navList) {
    hamburger.addEventListener("click", () => {
      hamburger.classList.toggle("active");
      navList.classList.toggle("active");
    });

    // Close menu when a navigation link is clicked
    navList.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        hamburger.classList.remove("active");
        navList.classList.remove("active");
      });
    });
  }

  /* =========================================================
     SMOOTH SCROLL
  ========================================================= */

  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const targetId = this.getAttribute("href");

      // Ignore empty "#" links
      if (!targetId || targetId === "#") {
        return;
      }

      const target = document.querySelector(targetId);

      if (target) {
        e.preventDefault();

        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });

  /* =========================================================
     STATS
     
     Stats are intentionally static.
     This prevents NaN values when using text such as:
     "3+", "Full-Stack", and "Open".
  ========================================================= */

  // No numerical animation is needed here.

  /* =========================================================
     INTERSECTION OBSERVER
     
     Adds a small reveal effect to sections/cards if desired.
  ========================================================= */

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    },
    {
      threshold: 0.1,
    },
  );

  document
    .querySelectorAll(".section, .project-card, .skill-group")
    .forEach((element) => {
      observer.observe(element);
    });

  /* =========================================================
     CONTACT FORM SUBMISSION (FastAPI Backend)
  ========================================================= */

  const contactForm = document.getElementById("contactForm");
  const formStatus = document.getElementById("formStatus");

  if (contactForm) {
    const submitBtn = contactForm.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn ? submitBtn.innerHTML : "Send Message";
    let isSubmitting = false;

    function showStatus(message, type) {
      if (!formStatus) return;
      formStatus.textContent = message;
      formStatus.className = `form-status ${type}`;
      formStatus.style.display = "block";
    }

    function hideStatus() {
      if (!formStatus) return;
      formStatus.style.display = "none";
      formStatus.textContent = "";
      formStatus.className = "form-status";
    }

    contactForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      if (isSubmitting) {
        return;
      }

      const nameInput = contactForm.querySelector("#name") || contactForm.name;
      const emailInput =
        contactForm.querySelector("#email") || contactForm.email;
      const phoneInput =
        contactForm.querySelector("#phone") || contactForm.phone;
      const serviceInput =
        contactForm.querySelector("#service") || contactForm.service;
      const messageInput =
        contactForm.querySelector("#message") || contactForm.message;

      const name = nameInput ? nameInput.value.trim() : "";
      const email = emailInput ? emailInput.value.trim() : "";
      const phone = phoneInput ? phoneInput.value.trim() : "";
      const service = serviceInput ? serviceInput.value.trim() : "";
      const message = messageInput ? messageInput.value.trim() : "";

      if (!name || !email || !service || !message) {
        showStatus("Please fill in all required fields.", "error");
        return;
      }

      isSubmitting = true;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML =
          '<i class="fas fa-spinner fa-spin"></i> Sending...';
      }
      hideStatus();

      const payload = {
        name: name,
        email: email,
        phone: phone ? phone : null,
        service: service,
        message: message,
      };

      try {
        const response = await fetch("/api/contact", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json().catch(() => null);

        if (response.ok && data && data.success) {
          showStatus(
            data.message || "Your message has been received.",
            "success",
          );
          contactForm.reset();
        } else {
          let errorMsg = "Failed to send message. Please try again later.";
          if (data) {
            if (typeof data.detail === "string") {
              errorMsg = data.detail;
            } else if (data.detail && typeof data.detail.message === "string") {
              errorMsg = data.detail.message;
            } else if (Array.isArray(data.detail) && data.detail.length > 0) {
              errorMsg = data.detail
                .map((err) => err.msg || err.message)
                .join(", ");
            } else if (data.message) {
              errorMsg = data.message;
            }
          }
          showStatus(errorMsg, "error");
        }
      } catch (err) {
        console.error("Contact form submission error:", err);
        showStatus(
          "Unable to connect to the backend server. Please make sure the FastAPI server is running.",
          "error",
        );
      } finally {
        isSubmitting = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalBtnText;
        }
      }
    });
  }
});
