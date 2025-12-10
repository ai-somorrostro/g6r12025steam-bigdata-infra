import pandas as pd
from elasticsearch import Elasticsearch
import warnings

# --- Gestión de Warnings SSL ---
try:
    from urllib3.exceptions import InsecureRequestWarning
except Exception:
    InsecureRequestWarning = None

if InsecureRequestWarning is not None:
    warnings.simplefilter('ignore', InsecureRequestWarning)
else:
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# --- Configuración de Conexión ---
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

# --- Funciones ---

def indice_mas_reciente(patron="steam_games-*"):
    try:
        indices = es.indices.get(index=patron)
        if not indices:
            raise ValueError(f"No se encontraron índices con patrón '{patron}'")
        indices_ordenados = sorted(indices.keys())
        return indices_ordenados[-1]
    except Exception as e:
        print(f"Error al obtener índices: {e}")
        return None

def buscar_juego(texto_usuario, campo="name", fuzziness="AUTO"):
    try:
        indice_actual = indice_mas_reciente()
        if not indice_actual:
            return
    except Exception as e:
        print(f"Error al obtener índice: {e}")
        return

    print(f"\n🎮 Buscando en índice '{indice_actual}': '{texto_usuario}' en campo '{campo}' (Fuzziness: {fuzziness})...")

    query_body = {
        "size": 5,
        "query": {
            "match": {
                campo: {
                    "query": texto_usuario,
                    "fuzziness": fuzziness
                }
            }
        },
        "_source": ["name", "price_final", "price_category", "genres", "release_date"]
    }

    try:
        response = es.search(index=indice_actual, body=query_body)
        hits = response['hits']['hits']
        if not hits:
            print("No se encontraron juegos.")
            return

        datos = []
        for hit in hits:
            juego = hit['_source']
            juego['score'] = hit['_score']
            datos.append(juego)

        df = pd.DataFrame(datos)
        cols = ['name', 'score', 'price_final', 'price_category']
        cols_existentes = [c for c in cols if c in df.columns]
        print(df[cols_existentes])

    except Exception as e:
        print(f"❌ Error durante la búsqueda: {e}")

# --- Ejecución ---

try:
    count = es.count(index="steam_games-*")
    print(f"Documentos totales en 'steam_games-*': {count['count']}")
except Exception as e:
    print(f"No se pudo conectar o encontrar el índice (revisar API KEY): {e}")

# --- Interfaz por terminal ---
while True:
    texto = input("\nEscribe el nombre del juego a buscar (o 'salir' para terminar): ")

    if texto.lower() == "salir":
        print("Saliste del buscador.")
        break

    buscar_juego(texto)
