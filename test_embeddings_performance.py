"""
Script de prueba para medir el rendimiento de búsqueda con embeddings cacheados.
Ejecutar: python test_embeddings_performance.py
"""
import os
import sys
import django
import time

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InmoFinder.settings')
django.setup()

from properties.management.commands.embeddings import buscar_propiedades

def test_search_performance():
    """Prueba el rendimiento de múltiples búsquedas consecutivas."""
    queries = [
        "apartamento cerca del centro",
        "casa con jardín y parqueadero",
        "estudio amoblado económico",
        "penthouse con vista",
        "apartamento 2 habitaciones"
    ]
    
    print("🔍 Probando rendimiento de búsqueda con embeddings cacheados...\n")
    
    times = []
    for i, query in enumerate(queries, 1):
        start = time.time()
        try:
            results = buscar_propiedades(query, top_k=50)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"✅ Búsqueda #{i}: '{query}'")
            print(f"   Tiempo: {elapsed:.3f}s | Resultados: {len(results)}")
            if results:
                print(f"   Top resultado: ID={results[0]['id']}, score={results[0]['score']}")
        except Exception as e:
            print(f"❌ Error en búsqueda #{i}: {e}")
        print()
    
    if times:
        print(f"\n📊 Estadísticas:")
        print(f"   Primera búsqueda (carga cache): {times[0]:.3f}s")
        if len(times) > 1:
            avg_cached = sum(times[1:]) / len(times[1:])
            print(f"   Promedio búsquedas con cache: {avg_cached:.3f}s")
            print(f"   Mejora de velocidad: {(times[0] / avg_cached):.1f}x más rápido")

if __name__ == "__main__":
    test_search_performance()
