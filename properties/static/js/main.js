console.log("main.js loaded");

// ------ DOM ready ------
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOMContentLoaded");

  // Reference variables (can be null, handlers use delegation)
  window._propertyModalEl = document.getElementById("propertyModal");
  window._propertyDetailContent = document.getElementById("propertyDetailContent");
  window._contactModalContent = document.getElementById("contactModalContent");
});

// Helper to get CSRF token
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

// Delegated click handler (single listener, avoids null refs)
document.addEventListener("click", function (e) {
  // 1) Toggle favorite
  const favBtn = e.target.closest(
    ".toggle-favorite, .favorite-btn, .toggle-favorite-button"
  );
  if (favBtn) {
    e.preventDefault();
    console.log("toggle favorite clicked", favBtn);

    const propId =
      favBtn.dataset.propertyId ||
      favBtn.dataset.propertyid ||
      favBtn.dataset.id ||
      favBtn.getAttribute("data-property-id") ||
      favBtn.getAttribute("data-id");

    if (!propId) {
      console.error("toggle favorite: no property id found on button", favBtn);
      return;
    }

    const csrftoken = getCookie("csrftoken");
    // Prefer data-toggle-url if present
    const toggleUrl =
      favBtn.dataset.toggleUrl || `/toggle_favorite/${propId}/`;

    fetch(toggleUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrftoken || "",
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
      body: new URLSearchParams({}), // empty body for CSRF
    })
      .then((resp) =>
        resp.json().catch(() => ({ error: true, status: resp && resp.status }))
      )
      .then((data) => {
        console.log("toggle response", data);
        if (!data || data.error) {
          console.error("toggle favorite error:", data);
          return;
        }
        const icon = favBtn.querySelector("i") || favBtn;
        if (!icon) return;
        if (data.status === "added") {
          icon.classList.remove("bi-heart");
          icon.classList.add("bi-heart-fill", "text-danger");
        } else {
          icon.classList.remove("bi-heart-fill", "text-danger");
          icon.classList.add("bi-heart");
        }
      })
      .catch((err) => console.error("Error toggling favorite:", err));

    return; // end favorite handler
  }

  // 2) Open property detail (delegated)
  const viewLink = e.target.closest(".view-property");
  if (viewLink) {
    e.preventDefault();
    const url = viewLink.getAttribute("href");
    const container = window._propertyDetailContent;
    if (container) {
      container.innerHTML = `
        <div class="text-center p-5 w-100">
          <div class="spinner-border text-primary"></div>
          <p class="mt-3">Loading property...</p>
        </div>`;
    }
    fetch(url + (url.includes("?") ? "&" : "?") + "modal=1", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((r) => r.text())
      .then((html) => {
        if (container) container.innerHTML = html;
        if (window._propertyModalEl)
          new bootstrap.Modal(window._propertyModalEl).show();
      })
      .catch((err) => {
        console.error("Error loading property:", err);
        if (container)
          container.innerHTML =
            '<div class="alert alert-danger">Error loading property.</div>';
      });
    return;
  }

  // 3) Open contact form (button inside detail)
  const contactBtn = e.target.closest("#openContactBtn");
  if (contactBtn) {
    const url = contactBtn.dataset.url;
    if (!url) return;
    e.preventDefault();

    const content = window._contactModalContent;
    if (content) {
      content.innerHTML = `
        <div class="p-5 text-center">
          <div class="spinner-border text-primary"></div>
          <p class="mt-3">Loading contact form...</p>
        </div>`;
    }

    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then((r) => r.text())
      .then((html) => {
        if (content) content.innerHTML = html;
        const modal = document.getElementById("contactModal");
        if (modal) new bootstrap.Modal(modal).show();
      })
      .catch((err) => {
        console.error("Error loading contact form:", err);
        if (content)
          content.innerHTML =
            '<div class="alert alert-danger">Error loading form.</div>';
      });

    return;
  }
});

// Delegated submit handler (dynamically loaded forms)
document.addEventListener("submit", function (e) {
  const form = e.target.closest("#contactForm");
  if (!form) return;

  e.preventDefault();
  const formData = new FormData(form);
  fetch(form.action, {
    method: "POST",
    body: formData,
    headers: { "X-Requested-With": "XMLHttpRequest" },
    credentials: "same-origin",
  })
    .then((r) => r.json())
    .then((data) => {
      console.log("contact form response", data);
      if (data && data.success) {
        const msgEl = document.getElementById("formMessage");
        if (msgEl) {
          msgEl.classList.remove("d-none");
          msgEl.innerHTML = data.message;
        }
        const propertyId =
          document.getElementById("openContactBtn")?.dataset.propertyId ||
          form.dataset.propertyId;
        if (propertyId) {
          fetch(`/property/${propertyId}/?modal=1`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
          })
            .then((r) => r.text())
            .then((html) => {
              const modalDetail =
                document.querySelector("#propertyModal #propertyDetailContent") ||
                document.querySelector(".modal-content");
              if (modalDetail) modalDetail.innerHTML = html;
            });
        } else {
          window.location.reload();
        }
      } else {
        console.warn("Contact form failed", data);
      }
    })
    .catch((err) => console.error("Error submitting contact form:", err));
});
