console.log("main.js loaded");

// ------ DOM ready ------
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOMContentLoaded");

  // Reference variables (can be null, handlers use delegation)
  window._propertyModalEl = document.getElementById("propertyModal");
  window._propertyDetailContent = document.getElementById("propertyDetailContent");
  window._contactModalContent = document.getElementById("contactModalContent");
  
  // Limpiar backdrop cuando se cierra el modal de propiedad
  if (window._propertyModalEl) {
    window._propertyModalEl.addEventListener('hidden.bs.modal', function () {
      // Limpiar el contenido del modal
      if (window._propertyDetailContent) {
        window._propertyDetailContent.innerHTML = `
          <div class="text-center p-5 w-100">
            <div class="spinner-border text-primary"></div>
            <p class="mt-3">Loading property...</p>
          </div>`;
      }
      
      // Asegurar que se eliminen todos los backdrops
      const backdrops = document.querySelectorAll('.modal-backdrop');
      backdrops.forEach(backdrop => backdrop.remove());
      
      // Restaurar scroll del body
      document.body.classList.remove('modal-open');
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
    });
  }
  
  // Limpiar backdrop cuando se cierra el modal de contacto
  const contactModalEl = document.getElementById("contactModal");
  if (contactModalEl) {
    contactModalEl.addEventListener('hidden.bs.modal', function () {
      // Asegurar que se eliminen todos los backdrops
      const backdrops = document.querySelectorAll('.modal-backdrop');
      backdrops.forEach(backdrop => backdrop.remove());
      
      // Restaurar scroll del body si no hay otros modales abiertos
      if (!document.querySelector('.modal.show')) {
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
      }
    });
  }
});

// Password visibility toggle: inject eye button into password inputs inside auth pages
document.addEventListener("DOMContentLoaded", function () {
  try {
    const pwInputs = document.querySelectorAll('.auth-page input[type="password"]');
    const eyeClosedSvg = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M2.47 2.47l19.06 19.06" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.53 9.53a3 3 0 004.24 4.24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 5c4.97 0 9 4.5 9 7s-4.03 7-9 7c-1.31 0-2.55-.25-3.67-.7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    const eyeOpenSvg = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';

    pwInputs.forEach(function (input) {
      if (input.dataset.toggleAttached) return; // avoid duplicates

      // Create wrapper
      const wrapper = document.createElement('div');
      wrapper.className = 'password-toggle';

      // Insert wrapper before input and move input inside
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      // Create toggle button
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'toggle-password';
      btn.setAttribute('aria-label', 'Mostrar contraseña');
      btn.innerHTML = eyeClosedSvg;

      // Append button to wrapper
      wrapper.appendChild(btn);

      // Mark attached
      input.dataset.toggleAttached = '1';

      // Click handler
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        if (input.type === 'password') {
          input.type = 'text';
          btn.innerHTML = eyeOpenSvg;
          btn.setAttribute('aria-label', 'Ocultar contraseña');
        } else {
          input.type = 'password';
          btn.innerHTML = eyeClosedSvg;
          btn.setAttribute('aria-label', 'Mostrar contraseña');
        }
      });
    });
  } catch (err) {
    console.error('Error initializing password toggles', err);
  }
});

// Helper to get CSRF token
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

// Allow unchecking radios with class .allow-uncheck (handles label clicks and touch)
function getRelatedAllowUncheck(target) {
  // Direct radio
  let r = target.closest && target.closest('.allow-uncheck[type="radio"]');
  if (r) return r;
  // Label next to radio input
  if (target.classList && target.classList.contains('form-check-label')) {
    const sib = target.previousElementSibling;
    if (sib && sib.matches && sib.matches('.allow-uncheck[type="radio"]')) return sib;
  }
  return null;
}

// Use pointerdown to catch both mouse and touch
document.addEventListener(
  "pointerdown",
  function (e) {
    const r = getRelatedAllowUncheck(e.target);
    if (r) {
      r.dataset.waschecked = r.checked ? "true" : "false";
    }
  },
  true
);

document.addEventListener(
  "click",
  function (e) {
    const r = getRelatedAllowUncheck(e.target);
    if (r && r.dataset.waschecked === "true") {
      // If it was already checked, uncheck on click
      r.checked = false;
      r.removeAttribute("data-waschecked");
      // Prevent default selection
      e.preventDefault();
      // Notify listeners of change
      r.dispatchEvent(new Event("change", { bubbles: true }));
    }
  },
  true
);

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
        // Remove any mutually-exclusive color classes that could override the red color
        icon.classList.remove("text-dark", "text-muted", "text-secondary");
        if (data.status === "added") {
          icon.classList.remove("bi-heart");
          icon.classList.add("bi-heart-fill", "text-danger");
        } else {
          icon.classList.remove("bi-heart-fill", "text-danger");
          // Add a sensible default color for the unliked state
          icon.classList.add("bi-heart", "text-dark");
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

    fetch(url, { 
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin"
    })
      .then((r) => {
        // Intentar parsear como JSON primero (en caso de error/redirect)
        const contentType = r.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          return r.json().then(data => ({ type: 'json', data }));
        }
        return r.text().then(html => ({ type: 'html', data: html }));
      })
      .then((response) => {
        if (response.type === 'json') {
          // Respuesta JSON (error o redirección)
          if (response.data.redirect) {
            window.location.href = response.data.redirect;
            return;
          }
          if (content) {
            content.innerHTML = `<div class="alert alert-warning">${response.data.message || 'No se puede contactar al propietario.'}</div>`;
          }
        } else {
          // Respuesta HTML (formulario)
          if (content) content.innerHTML = response.data;
          const modal = document.getElementById("contactModal");
          if (modal) new bootstrap.Modal(modal).show();
        }
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
        // Cerrar el modal de contacto
        const contactModalEl = document.getElementById("contactModal");
        if (contactModalEl) {
          const contactModalInstance = bootstrap.Modal.getInstance(contactModalEl);
          if (contactModalInstance) {
            contactModalInstance.hide();
          }
        }
        
        // Mostrar mensaje de éxito con alert o toast
        // Opción 1: Alert Bootstrap en el modal de la propiedad
        const propertyDetailContent = document.getElementById("propertyDetailContent");
        if (propertyDetailContent) {
          const successAlert = document.createElement('div');
          successAlert.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
          successAlert.style.zIndex = '9999';
          successAlert.innerHTML = `
            <strong>¡Mensaje enviado!</strong> ${data.message || 'El propietario recibirá tu mensaje pronto.'}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          `;
          document.body.appendChild(successAlert);
          
          // Auto-cerrar después de 5 segundos
          setTimeout(() => {
            successAlert.remove();
          }, 5000);
        }
      } else {
        console.warn("Contact form failed", data);
        // Mostrar error en el formulario
        const msgEl = document.getElementById("formMessage");
        if (msgEl) {
          msgEl.classList.remove("d-none", "alert-success");
          msgEl.classList.add("alert-danger");
          // Si el servidor envió errores de campos, formatearlos
          if (data.errors) {
            let html = `<strong>${(data.message && data.message) || 'Errores en el formulario:'}</strong><ul class="mb-0">`;
            try {
              // data.errors puede venir como objeto con listas
              for (const [field, errs] of Object.entries(data.errors)) {
                const fieldLabel = field === '__all__' ? '' : `<em>${field}:</em> `;
                const messages = Array.isArray(errs) ? errs : [errs];
                messages.forEach(m => { html += `<li>${fieldLabel}${m}</li>` });
              }
            } catch (e) {
              html += `<li>${data.message || 'Error al enviar el mensaje.'}</li>`;
            }
            html += `</ul>`;
            msgEl.innerHTML = html;
          } else {
            msgEl.innerHTML = data.message || 'Error al enviar el mensaje.';
          }
        }
      }
    })
    .catch((err) => {
      console.error("Error submitting contact form:", err);
      alert('Error al enviar el mensaje. Por favor, intenta nuevamente.');
    });
});
