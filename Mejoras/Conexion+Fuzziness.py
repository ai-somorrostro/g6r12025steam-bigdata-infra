import pandas as pd
from elasticsearch import Elasticsearch
import warnings

# ===============================
#  SUPRESIÓN WARNINGS SSL
# ===============================
try:
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter('ignore', InsecureRequestWarning)
except Exception:
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# ===============================
#  CONEXIÓN ELASTICSEARCH
# ===============================
IP_ELASTIC = [
    "https://192.199.1.53:9200",
    "https://192.199.1.65:9200",
    "https://192.199.1.66:9200"
]

API_KEY_ID = "L8C96JoBlpi-YpBzl02z"
API_KEY_SECRET = "eL5iFNv2V267C0fr4MZyww"

es = Elasticsearch(
    hosts=IP_ELASTIC,
    api_key=(API_KEY_ID, API_KEY_SECRET),
    verify_certs=False,
    ssl_show_warn=False,
    max_retries=5,
    retry_on_timeout=True,
    request_timeout=30
)

# ===============================
#  UTILIDADES
# ===============================
def indice_mas_reciente(patron="steam_games-2025*"):
    try:
        indices = es.indices.get(index=patron)
        return sorted(indices.keys())[-1]
    except Exception as e:
        print(f"❌ Error obteniendo índices: {e}")
        return None


def mostrar_resultados(response):
    hits = response["hits"]["hits"]
    if not hits:
        print("❌ No se encontraron resultados.")
        return

    datos = [hit["_source"] for hit in hits]
    df = pd.DataFrame(datos)
    print(df)


# ===============================
#  BÚSQUEDAS
# ===============================

# 🔍 Búsqueda general (FUZZINESS)
def buscar_texto_general(texto):
    indice = indice_mas_reciente()
    if not indice:
        return

    query = {
        "size": 5,
        "query": {
            "multi_match": {
                "query": texto,
                "fields": [
                    "name^3",
                    "genres^2",
                    "categories^2",
                    "short_description",
                    "detailed_description"
                ],
                "fuzziness": "AUTO",
                "operator": "or",
                "minimum_should_match": "50%"
            }
        },
        "_source": ["name", "genres", "price_final", "metacritic_score"]
    }

    mostrar_resultados(es.search(index=indice, body=query))


# 🎮 Buscar por género
def buscar_por_genero(genero):
    indice = indice_mas_reciente()
    if not indice:
        return

    query = {
        "size": 5,
        "query": {
            "match": {
                "genres": {
                    "query": genero,
                    "operator": "and"
                }
            }
        },
        "_source": ["name", "genres", "price_final"]
    }

    mostrar_resultados(es.search(index=indice, body=query))


# 🏷️ Buscar por categoría
def buscar_por_categoria(categoria):
    indice = indice_mas_reciente()
    if not indice:
        return

    query = {
        "size": 5,
        "query": {
            "match": {
                "categories": {
                    "query": categoria,
                    "operator": "and"
                }
            }
        },
        "_source": ["name", "categories", "price_final"]
    }

    mostrar_resultados(es.search(index=indice, body=query))


# 💰 Buscar por rango de precio
def buscar_por_precio(min_p, max_p):
    indice = indice_mas_reciente()
    if not indice:
        return

    query = {
        "size": 5,
        "query": {
            "range": {
                "price_final": {
                    "gte": min_p,
                    "lte": max_p
                }
            }
        },
        "_source": ["name", "price_final"]
    }

    mostrar_resultados(es.search(index=indice, body=query))


# 🆓 Juegos gratis
def buscar_gratis():
    indice = indice_mas_reciente()
    if not indice:
        return

    query = {
        "size": 5,
        "query": {
            "term": {
                "is_free": True
            }
        },
        "_source": ["name", "genres"]
    }

    mostrar_resultados(es.search(index=indice, body=query))


# ⭐ Top por Metacritic
def top_metacritic(min_score):
    indice = indice_mas_reciente()
    if not indice:
        return

    query = {
        "size": 5,
        "query": {
            "range": {
                "metacritic_score": {
                    "gte": min_score
                }
            }
        },
        "sort": [{"metacritic_score": "desc"}],
        "_source": ["name", "metacritic_score", "price_final"]
    }

    mostrar_resultados(es.search(index=indice, body=query))


# ===============================
#  MENÚ TERMINAL
# ===============================
def menu():
    print("\n====== BUSCADOR STEAM ======")
    print("1. Búsqueda general (fuzzy)")
    print("2. Buscar por género")
    print("3. Buscar por categoría")
    print("4. Buscar por precio")
    print("5. Juegos gratis")
    print("6. Top Metacritic")
    print("0. Salir")
    return input("Opción: ")


# ===============================
#  MAIN
# ===============================
if __name__ == "__main__":
    try:
        count = es.count(index="steam_games-*")
        print(f"📦 Documentos totales: {count['count']}")
    except Exception as e:
        print(f"❌ Error conexión Elastic: {e}")

    while True:
        op = menu()

        if op == "1":
            buscar_texto_general(input("Texto a buscar: "))

        elif op == "2":
            buscar_por_genero(input("Género (Rol, Aventura...): "))

        elif op == "3":
            buscar_por_categoria(input("Categoría (Anime, Mundo abierto...): "))

        elif op == "4":
            buscar_por_precio(
                float(input("Precio mínimo: ")),
                float(input("Precio máximo: "))
            )

        elif op == "5":
            buscar_gratis()

        elif op == "6":
            top_metacritic(int(input("Nota mínima: ")))

        elif op == "0":
            print("👋 Hasta luego")
            break

        else:
            print("Opción no válida")
