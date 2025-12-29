import os
import unicodedata
import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_URL = "https://apiplataformaelectoral9.jne.gob.pe/api/v1/plan-gobierno/busqueda-avanzada"
HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def quitar_tildes_unicode(texto):
    """Normaliza el texto a NFD y elimina los caracteres diacríticos."""
    if not texto: return ""
    texto_normalizado = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn')

def limpiar_nombre(texto):
    """Limpia el nombre para facilitar el match (minúsculas, sin tildes, sin 'partido')."""
    if not texto: return ""
    limpio = quitar_tildes_unicode(texto.lower())
    limpio = limpio.replace("partido", "")
    return " ".join(limpio.split())

def descargar_archivo(url, ruta_destino):
    """Descarga solo si el archivo no existe o tiene tamaño 0."""
    if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 0:
        print(f"    [EXISTE] Omitiendo: {os.path.basename(ruta_destino)}")
        return

    if not url:
        print(f"    [!] URL vacía para {os.path.basename(ruta_destino)}")
        return

    try:
        print(f"    [DESCARGANDO] {os.path.basename(ruta_destino)}...")
        with requests.get(url, stream=True, verify=False) as r:
            r.raise_for_status()
            with open(ruta_destino, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        print(f"    [ERROR] Falló descarga: {e}")

# --- 1. FILTRADO INICIAL ---
# Identificamos qué carpetas locales necesitan archivos ANTES de hacer peticiones
carpetas_locales = [d for d in os.listdir() if os.path.isdir(d) and not d.startswith('.')]
carpetas_pendientes = []

print("🔍 Verificando estado de carpetas locales...")
for carpeta in carpetas_locales:
    path_docs = os.path.join(carpeta, "Documentos Gubernamentales")
    path_gob = os.path.join(path_docs, "PLAN GOBIERNO.pdf")
    path_res = os.path.join(path_docs, "PLAN RESUMEN.pdf")
    
    # Si falta alguno de los dos archivos, añadimos a la lista de pendientes
    if not (os.path.exists(path_gob) and os.path.exists(path_res)):
        carpetas_pendientes.append(carpeta)

print(f"📋 Carpetas completas: {len(carpetas_locales) - len(carpetas_pendientes)}")
print(f"🚀 Carpetas a procesar: {len(carpetas_pendientes)}\n")

if not carpetas_pendientes:
    print("¡Todo está actualizado! No se necesitan descargas.")
    exit()

# --- 2. PROCESO DE API Y MATCHING ---
for skip in range(1, 5):
    print(f"--- Procesando página API {skip} ---")
    
    payload = {
        "pageSize": 10,
        "skip": skip,
        "filter": {
            "idProcesoElectoral": 124, "idTipoEleccion": "1",
            "idOrganizacionPolitica": "0", "txDatoCandidato": "", "idJuradoElectoral": 0
        }
    }

    try:
        response = requests.post(BASE_URL, data=json.dumps(payload), headers=HEADERS, verify=False)
        lista_partidos = response.json().get("data", [])

        if not lista_partidos: break

        for item in lista_partidos:
            nombre_api = item.get("txOrganizacionPolitica", "")
            nombre_api_clean = limpiar_nombre(nombre_api)
            
            # Solo buscamos match dentro de 'carpetas_pendientes'
            match_encontrado = False
            
            for carpeta in carpetas_pendientes:
                nombre_carpeta_clean = limpiar_nombre(carpeta)

                # Match bidireccional
                if (nombre_api_clean in nombre_carpeta_clean) or (nombre_carpeta_clean in nombre_api_clean):
                    print(f"✅ Match: '{nombre_api}' -> '{carpeta}'")
                    
                    path_docs = os.path.join(carpeta, "Documentos Gubernamentales")
                    os.makedirs(path_docs, exist_ok=True)

                    # Intentamos descargar ambos (la función valida si ya existen individualmente)
                    descargar_archivo(item.get("txRutaCompleto"), os.path.join(path_docs, "PLAN GOBIERNO.pdf"))
                    descargar_archivo(item.get("txRutaResumen"), os.path.join(path_docs, "PLAN RESUMEN.pdf"))
                    
                    match_encontrado = True
                    break 
            
            # Opcional: comentar este print si ensucia mucho la consola
            if not match_encontrado:
                # Nota: Puede no encontrarlo porque ya está completo (filtrado) o porque no existe la carpeta
                pass 

    except Exception as e:
        print(f"Error en skip {skip}: {e}")

print("\n🏁 Proceso finalizado.")
