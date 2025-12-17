# 🎮 Steam Big Data Infrastructure

Este proyecto implementa una infraestructura completa de Big Data para el análisis de datos de videojuegos de Steam, utilizando el stack ELK (Elasticsearch, Logstash, Kibana) con un clúster distribuido de 3 nodos.

## 📁 Estructura del Proyecto

```
/home/g6/reto/
├── datos/                          # Datos fuente y logs
│   ├── steam-games-data-vect.ndjson    # Dataset principal de juegos Steam
│   └── scraper_metrics.log             # Logs del proceso de scraping
│
├── elasticsearch-9.2.1/            # Nodo de Elasticsearch
│   └── config/
│       ├── elasticsearch.yml           # Configuración del clúster
│       └── certs/                      # Certificados SSL/TLS
│           ├── http.p12
│           ├── transport.p12
│           └── http_ca.crt
│
├── logstash-9.2.1/                 # Pipeline de procesamiento
│   └── config/
│       ├── Datos.conf                  # Pipeline para datos de juegos
│       ├── Logs.conf                   # Pipeline para logs de scraping
│       └── pipelines.yml               # Configuración de pipelines
│
└── metricbeat-9.2.1/               # Monitoreo de métricas
    └── config/
        └── metricbeat.yml
```

---

## 🔗 Flujo de Datos: Cómo se Complementan las Carpetas

### 1️⃣ **`/reto/datos` - Origen de los Datos**

**Contenido:**
- `steam-games-data-vect.ndjson`: Archivo NDJSON con información de ~86,000 juegos de Steam
  - Datos: nombre, precio, géneros, requisitos PC, embeddings vectoriales
  - Formato: Una línea JSON por juego
  
- `scraper_metrics.log`: Logs generados durante el scraping de la API de Steam
  - Métricas: latencia de API, códigos HTTP, offsets, errores

**Propósito:**
- Actúa como la **fuente de verdad** del sistema
- Datos persistentes que se ingestan y procesan

---

### 2️⃣ **`/reto/logstash-9.2.1/config` - Pipeline de Transformación**

#### **Archivo: `Datos.conf`** 
**Pipeline de Datos de Juegos → Elasticsearch**

```
┌─────────────────────────────────────────────────────────────┐
│ INPUT: Lee steam-games-data-vect.ndjson                    │
│   - Lectura línea por línea con codec JSON                 │
│   - sincedb_path => "/dev/null" (reingestar desde inicio)  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FILTER: Transformación de Datos                            │
│   1. Date parsing: release_date → formato Elasticsearch    │
│   2. GROK: Extrae requisitos PC (SO, CPU, RAM, GPU)        │
│   3. Mutate: Conversiones de tipos (float, int, boolean)   │
│   4. Ruby: Categoriza precios (Gratis/Barato/Normal/Premium)│
│   5. Añade timestamp de última actualización               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT: Elasticsearch Clúster (3 nodos)                    │
│   - Índice dinámico: steam_games-YYYY.MM.DD                │
│   - Hosts: 192.199.1.53, 192.199.1.65, 192.199.1.66        │
│   - Autenticación: API Key                                 │
│   - SSL/TLS con certificado CA                             │
│   - Document ID: appid (evita duplicados)                  │
└─────────────────────────────────────────────────────────────┘
```

**Características clave:**
- ✅ **Idempotencia**: Usa `appid` como ID único
- ✅ **Índice diario rotativo**: Facilita la gestión de datos históricos
- ✅ **Enriquecimiento**: Extrae metadata de requisitos PC y Datos de el .log con GROK
- ✅ **Seguridad**: Conexión HTTPS con validación completa de certificados

---

#### **Archivo: `Logs.conf`**
**Pipeline de Logs de Scraping → Elasticsearch**

```
┌─────────────────────────────────────────────────────────────┐
│ INPUT: Lee scraper_metrics.log                             │
│   - Tag: "scraper_metrics"                                 │
│   - Monitoreo continuo del archivo                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FILTER: Parsing Estructurado de Logs                       │
│   1. GROK: Extrae timestamp, log_level, mensaje            │
│   2. Condicional por nivel:                                │
│      - INFO: Extrae URL, status HTTP, latency, offset      │
│      - ERROR: Extrae tipo de error, URL fallida, detalles  │
│   3. Date parsing: Convierte timestamp a @timestamp        │
│   4. Limpieza de campos intermedios                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT: Elasticsearch Clúster                              │
│   - Índice dinámico: scraper_logs-YYYY.MM.DD               │
│   - Misma configuración SSL/TLS que Datos.conf             │
│   - Debug: stdout con rubydebug                            │
└─────────────────────────────────────────────────────────────┘
```

**Características clave:**
- ✅ **Observabilidad**: Monitoreo de rendimiento del scraper
- ✅ **Trazabilidad**: Cada petición HTTP registrada
- ✅ **Alertas**: Detecta errores y timeouts

---

### 3️⃣ **`/reto/elasticsearch-9.2.1/config` - Almacenamiento y Búsqueda**

#### **Archivo: `elasticsearch.yml`**

**Configuración del Clúster:**

```yaml
cluster.name: chatbot-cluster          # Clúster unificado de 3 nodos
node.name: node-2                      # Identificador del nodo
node.roles: [master, data, ingest]     # Nodo completo (todos los roles)

# Red
network.host: 0.0.0.0                  # Escucha en todas las interfaces
discovery.seed_hosts:                  # IPs de los otros nodos
  - 192.199.1.53:9300
  - 192.199.1.65:9300
  - 192.199.1.66:9300

# Seguridad (HTTPS + Autenticación)
xpack.security.enabled: true
xpack.security.http.ssl:
  enabled: true
  keystore.path: certs/http.p12        # Certificado HTTPS
  
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate       # Verificación mutua TLS
  keystore.path: certs/transport.p12   # Certificado inter-nodos
  truststore.path: certs/transport.p12
```

**Características del Clúster:**

```
┌─────────────────────────────────────────────────────────────┐
│                     CLÚSTER: chatbot-cluster                │
├─────────────────────────────────────────────────────────────┤
│  Nodo 1 (192.199.1.53)    Nodo 2 (192.199.1.65)           │
│  Nodo 3 (192.199.1.66)                                     │
│                                                             │
│  ✅ Alta Disponibilidad: Tolerancia a fallos (2/3 activos) │
│  ✅ Balanceo de Carga: Logstash distribuye entre 3 nodos   │
│  ✅ Replicación: Shards duplicados entre nodos            │
│  ✅ Seguridad: TLS + API Keys + RBAC                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo Completo de Extremo a Extremo

```
┌───────────────────┐
│  Steam API        │
│  (Scraper)        │
└────────┬──────────┘
         │ Genera
         ↓
┌───────────────────────────────────────────────────────────┐
│  /reto/datos/                                             │
│  ├── steam-games-data-vect.ndjson  (86K juegos)          │
│  └── scraper_metrics.log           (logs de scraping)    │
└────────┬──────────────────────────────┬─────────────────┘
         │                              │
         │ Lee                          │ Lee
         ↓                              ↓
┌───────────────────────┐    ┌───────────────────────┐
│  Logstash Pipeline    │    │  Logstash Pipeline    │
│  Datos.conf           │    │  Logs.conf            │
│  ├─ Parse JSON        │    │  ├─ Parse logs        │
│  ├─ GROK requisitos   │    │  ├─ GROK métricas     │
│  ├─ Categoriza precio │    │  └─ Extrae errores    │
│  └─ Valida tipos      │    └───────────┬───────────┘
└───────────┬───────────┘                │
            │                            │
            └────────────┬───────────────┘
                         │ Envía (HTTPS)
                         ↓
        ┌────────────────────────────────────┐
        │   Elasticsearch Clúster (3 nodos)  │
        │   ├─ node-1 (192.199.1.53)         │
        │   ├─ node-2 (192.199.1.65)         │
        │   └─ node-3 (192.199.1.66)         │
        │                                    │
        │   Índices creados:                 │
        │   ├─ steam_games-2025.12.02       │
        │   └─ scraper_logs-2025.12.02      │
        └───────────┬────────────────────────┘
                    │ Consultas
                    ↓
        ┌────────────────────────┐
        │  Kibana / Visualización│
        │  - Dashboards          │
        │  - Búsquedas           │
        │  - Alertas             │
        └────────────────────────┘
```

---

## 🛠️ Gestión del Sistema

### Iniciar Servicios

```bash
# Elasticsearch (en cada nodo)
/home/g6/reto/elasticsearch-9.2.1/bin/elasticsearch -d

# Logstash (como servicio systemd)
sudo systemctl start logstash
sudo systemctl enable logstash  # Auto-inicio en boot

# Verificar estado
sudo systemctl status logstash
```

### Monitoreo

```bash
# Estado del clúster
curl -k -H "Authorization: ApiKey $(echo -n 'API_ID:API_KEY' | base64)" \
  https://192.199.1.53:9200/_cluster/health?pretty

# Ver índices creados
curl -k -H "Authorization: ApiKey $(echo -n 'API_ID:API_KEY' | base64)" \
  https://192.199.1.53:9200/_cat/indices?v

# Logs de Logstash en tiempo real
sudo journalctl -u logstash -f
```

### Reingesta de Datos

```bash
# Detener Logstash
sudo systemctl stop logstash

# Eliminar índice (si es necesario)
curl -X DELETE "https://192.199.1.53:9200/steam_games-*" \
  -H "Authorization: ApiKey ..."

# Reiniciar Logstash (reingestará automáticamente)
sudo systemctl start logstash
```

---

## 🔐 Seguridad Implementada

| Capa | Mecanismo | Ubicación |
|------|-----------|-----------|
| **Transporte** | TLS mutuo | `elasticsearch-9.2.1/config/certs/transport.p12` |
| **HTTP/API** | HTTPS | `elasticsearch-9.2.1/config/certs/http.p12` |
| **Autenticación** | API Keys | Configurados en Datos.conf y Logs.conf |
| **Autorización** | RBAC | Permisos por API Key |
| **Validación** | Certificate Authority | `certs/http_ca.crt` |

---

## 📊 Índices y Esquemas

### `steam_games-YYYY.MM.DD`
**Campos principales:**
- `appid` (integer): ID único del juego
- `name` (text): Nombre del juego
- `price_final` (float): Precio actual
- `price_category` (keyword): Gratis/Barato/Normal/Premium
- `release_date` (date): Fecha de lanzamiento
- `min_ram_gb`, `min_cpu`, `min_gpu`: Requisitos PC
- `vector_embedding` (dense_vector): Para búsquedas semánticas

### `scraper_logs-YYYY.MM.DD`
**Campos principales:**
- `@timestamp` (date): Momento del log
- `log_level` (keyword): INFO/ERROR/WARNING
- `request_url` (text): URL de la API consultada
- `http_status` (integer): Código de respuesta HTTP
- `api_latency` (float): Tiempo de respuesta en segundos
- `error_type`, `error_details`: Información de errores

---

**Documentación creada:** Diciembre 2025  
**Versión Stack ELK:** 9.2.1  
**Proyecto:** Steam Big Data Infrastructure

# Para ¡¡¡VALIDACION!!!

**Usar estos comandos para descargar elastic y logstash**

```bash

# Elasticsearch 9.2.1

wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-9.2.2-linux-x86_64.tar.gz
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-9.2.2-linux-x86_64.tar.gz.sha512
shasum -a 512 -c elasticsearch-9.2.2-linux-x86_64.tar.gz.sha512
tar -xzf elasticsearch-9.2.2-linux-x86_64.tar.gz
cd elasticsearch-9.2.2/

# Logstash 9.2.1
wget https://artifacts.elastic.co/downloads/logstash/logstash-9.2.2-linux-x86_64.tar.gz
wget https://artifacts.elastic.co/downloads/logstash/logstash-9.2.2-linux-x86_64.tar.gz.sha512
shasum -a 512 -c logstash-9.2.2-linux-x86_64.tar.gz.sha512
tar -xzf logstash-9.2.2-linux-x86_64.tar.gz
cd logstash-9.2.2/

# Iniciar elastic
bin/elasticsearch

```

**Copiar a un block de notas la pasword de elastic**

**entrar logsatsh, crear el datos.conf y pegar esto dentro**

```yaml

input {
  # Lectura del archivo .ndjson
  file {
    path => "/home/lander/valReto/scraper/data_output/steam-games-data-vect.ndjson"  <----- Cambiar el path al archivo real
    start_position => "beginning"
    sincedb_path => "/dev/null"
    codec => json
  }
}

filter {
  # --- 1. Procesamiento de fechas ---
  if [release_date] {
    date {
      match => [ "release_date", "yyyy-MM-dd" ]
      target => "release_date"
      timezone => "UTC"
    }
  }

  # --- 2. Grok para extraer requisitos mínimos de PC ---
  
  grok {
    match => { 
      "pc_requirements_min" => [
        # Intenta capturar un patrón más completo, que es común
        "SO: .*?%{DATA:min_os}\. Procesador: %{DATA:min_cpu}\. Memoria: .*?%{NUMBER:min_ram_gb:int} GB de RAM Gráficos: .*?%{DATA:min_gpu} DirectX: .*?%{DATA:min_directx}.*",
        # Patrón para los que no tienen el SO
        "Procesador: .*?%{DATA:min_cpu} Memoria: .*?%{NUMBER:min_ram_gb:int} GB de RAM Gráficos: .*?%{DATA:min_gpu} DirectX: .*?%{DATA:min_directx}.*"
      ]
    }
    tag_on_failure => [ "grok_pc_fail" ]
    remove_field => ["pc_requirements_min"] 
  }

  mutate {
    # Convertir campos numéricos y booleanos.
    convert => {
      "price_eur"          => "float"
      "price_initial_eur"  => "float"
      "discount_pct"       => "integer"
      "metacritic_score"   => "integer"
      "recommendations_total" => "integer"
      "achievements_count" => "integer"
      "is_free"            => "boolean"
      "steam_id"           => "integer"
      "min_ram_gb"         => "integer"
      "vector_embedding" => "float" 
    }
    

    rename => {
      "steam_id"  => "appid"
      "price_eur" => "price_final"
    }
    
    # Limpieza final de campos no necesarios 
    remove_field => [
      "message",
      "@version",
      "host",
      "path",
      "type",
      "tags", 
      "event",
      "message" 
    ]
  }

  ruby {
    code => '
      price = event.get("price_final")
      is_free = event.get("is_free")

      if is_free == true || (price && price == 0)
        event.set("price_category", "Gratis")
      elsif price && price < 15.0
        event.set("price_category", "Barato")
      elsif price && price < 40.0
        event.set("price_category", "Normal")
      else
        event.set("price_category", "Premium")
      end
    '
  }

  mutate {
    add_field => { "last_updated" => "%{@timestamp}" }
  }
  
  date {
    match => ["last_updated", "ISO8601"]
    target => "last_updated"
  }
}

output {
  elasticsearch {
    index => "steam_games-%{+yyyy.MM.dd}" 
    
    # CORRECCIÓN 1: Faltaban las barras // después de https:
    hosts => ["https://localhost:9200"]
    
    # CORRECCIÓN 2: Cambio de API Key a Usuario/Pass
    user => "elastic"
    password => "A2*dwvdR4O4BDc6DN_a4"  <----- Cambiar a la contraseña de elastic
    
    # Configuración SSL/TLS
    ssl_certificate_authorities => ["/home/lander/valReto/elasticsearch-9.2.2/config/certs/http_ca.crt"]    <----- Cambiar el path al archivo real del certificado
    
    # Si te da errores de certificado en local, puedes cambiar esto a "none" temporalmente
    ssl_verification_mode => "full" 
    
    document_id => "%{appid}"
    
    # Evita duplicados o problemas si el documento ya existe
    action => "update"
    doc_as_upsert => true
  }
  
  # Descomenta esto si quieres ver por pantalla qué está pasando
  stdout { codec => rubydebug }
}

```

**Ejecutar este comando en la TERMINAL de ELASTIC para generar el mapping**

Cambiar esto por la contraseña de elastic: (elastic:A2*dwvdR4O4BDc6DN_a4 <---- Esto)

```bash

curl -k -u elastic:A2*dwvdR4O4BDc6DN_a4 \ 
-X PUT "https://localhost:9200/_index_template/steam_games_template" \
-H 'Content-Type: application/json' \
-d'
{
  "index_patterns": ["steam_games-*"],
  "template": {
    "mappings": {
      "properties": {
        "vector_embedding": {
          "type": "dense_vector",
          "dims": 768,
          "index": true,
          "similarity": "cosine"
        },
        "price_final": { "type": "float" },
        "release_date": { "type": "date" },
        "name": { "type": "text", "analyzer": "standard" },
        "detailed_description": { "type": "text", "analyzer": "spanish" }
      }
    }
  }
}
'

```

**Iniciar logastash en su terminal**

Poner el path de el datos.conf aqui ---> (config/datos.conf)

```bash

bin/logastash -f config/datos.conf

```


**Por ultimo comprobar que se han subido los datos**

Cambiar la contraseña de elastic aqui ---> (elastic:A2*dwvdR4O4BDc6DN_a4)

```bash

curl -k -u elastic:A2*dwvdR4O4BDc6DN_a4 -X GET "https://localhost:9200/_cat/indices/steam_games-*?v"

```


