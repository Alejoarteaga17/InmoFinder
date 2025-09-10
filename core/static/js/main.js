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

// Abrir modal de contacto
document.addEventListener("click", function (e) {
    const contactBtn = e.target.closest("#openContactBtn");
    if (contactBtn) {
        const propiedadId = contactBtn.dataset.propiedad;
        const url = `/core/contact-form/${propiedadId}/`; // ✅ ruta corregida

        // loader
        document.getElementById("contactModalBody").innerHTML = `
            <div class="text-center p-5 w-100">
              <div class="spinner-border text-primary"></div>
              <p class="mt-3">Cargando formulario...</p>
            </div>
        `;

        fetch(url)
            .then(response => response.text())
            .then(html => {
                document.getElementById("contactModalBody").innerHTML = html;

                // mostrar modal
                const modal = new bootstrap.Modal(document.getElementById("contactModal"));
                modal.show();
            })
            .catch(err => {
                document.getElementById("contactModalBody").innerHTML = `
                    <div class="alert alert-danger">
                        Error cargando el formulario. Intenta de nuevo.
                    </div>`;
            });
    }
});
