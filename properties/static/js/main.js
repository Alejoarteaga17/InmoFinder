document.addEventListener("DOMContentLoaded", function () {
    const propertyModal = document.getElementById("propertyModal");
    const propertyDetailContent = document.getElementById("propertyDetailContent");

    if (!propertyModal || !propertyDetailContent) return;

    // Delegación de eventos: enlaces con .view-property
    document.body.addEventListener("click", function (e) {
        const target = e.target.closest(".view-property");
        if (target) {
            e.preventDefault();
            const url = target.getAttribute("href");

            // loader
            propertyDetailContent.innerHTML = `
                <div class="text-center p-5 w-100">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-3">Cargando propiedad...</p>
                </div>
            `;

            // cargar la vista detalle
            fetch(url)
                .then(response => response.text())
                .then(html => {
                    propertyDetailContent.innerHTML = html;
                })
                .catch(err => {
                    propertyDetailContent.innerHTML = `
                        <div class="alert alert-danger">
                        Error cargando la propiedad. Intenta de nuevo.
                        </div>`;
                });
        }
    });
});

document.addEventListener("click", function (e) {
    const btn = e.target.closest("#openContactBtn");
    if (btn) {
        const url = btn.dataset.url;

        document.getElementById("contactModalContent").innerHTML = `
            <div class="p-5 text-center">
                <div class="spinner-border text-primary"></div>
                <p class="mt-3">Loading contact form...</p>
            </div>`;

        fetch(url)
            .then(response => response.text())
            .then(html => {
                document.getElementById("contactModalContent").innerHTML = html;
                new bootstrap.Modal(document.getElementById("contactModal")).show();
            })
            .catch(() => {
                document.getElementById("contactModalContent").innerHTML =
                    `<div class="alert alert-danger">Error loading form.</div>`;
            });
    }
});

document.getElementById('contactForm').addEventListener('submit', function(e){
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(response => response.json())
    .then(data => {
        if(data.success){
            document.getElementById('formMessage').classList.remove('d-none');
            document.getElementById('formMessage').innerHTML = data.message;

            // Mantener modal abierto y refrescar el contenido de la propiedad dentro del modal
            setTimeout(() => {
                // Usar AJAX para traer de nuevo el detalle de la propiedad
                fetch("{% url 'detalle_propiedad' propiedad.id %}?modal=1")
                    .then(res => res.text())
                    .then(html => {
                        document.querySelector('.modal-content').innerHTML = html;
                    });
            }, 2000);
        }
    })
    .catch(error => console.error('Error:', error));
});

// --- Toggle Favoritos ---
document.addEventListener("DOMContentLoaded", () => {
  const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  document.querySelectorAll(".favorite-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const propiedadId = btn.dataset.id;

      fetch("/toggle-favorite/", {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `propiedad_id=${propiedadId}`,
      })
      .then(res => res.json())
      .then(data => {
        const icon = btn.querySelector("i");
        if (data.favorited) {
          icon.classList.remove("bi-heart");
          icon.classList.add("bi-heart-fill");
        } else {
          icon.classList.remove("bi-heart-fill");
          icon.classList.add("bi-heart");
        }
      });
    });
  });
});
