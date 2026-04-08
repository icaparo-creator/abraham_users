import os
import platform
import subprocess
import json
import requests
import sys

# ========== CONFIGURACIÓN ==========
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyPvqQnkBEDr2wpZzsfPslOEqpXmhQTFiGpm33SfZ1xdmWhj0TxMa_rSgVpA98mw3kCDw/exec"
# ===================================

def get_hostname():
    return platform.node()

def get_os_name():
    return platform.system()

def user_exists(username):
    sistema = get_os_name()
    if sistema == "Windows":
        try:
            subprocess.run(["net", "user", username], capture_output=True, check=True)
            return True
        except:
            return False
    else:
        try:
            subprocess.run(["id", username], capture_output=True, check=True)
            return True
        except:
            return False

def create_user(username):
    sistema = get_os_name()
    if sistema == "Windows":
        try:
            subprocess.run(["net", "user", username, "/add"], capture_output=True, text=True, check=True)
            return True, f"Usuario '{username}' creado."
        except subprocess.CalledProcessError as e:
            return False, f"Error al crear '{username}': {e.stderr or e.stdout}"
    else:
        try:
            subprocess.run(["sudo", "useradd", "-m", username], capture_output=True, text=True, check=True)
            return True, f"Usuario '{username}' creado."
        except subprocess.CalledProcessError as e:
            return False, f"Error al crear '{username}': {e.stderr or e.stdout}"

def delete_user(username):
    sistema = get_os_name()
    if sistema == "Windows":
        try:
            subprocess.run(["net", "user", username, "/delete"], capture_output=True, text=True, check=True)
            return True, f"Usuario '{username}' eliminado."
        except subprocess.CalledProcessError as e:
            return False, f"Error al eliminar '{username}': {e.stderr or e.stdout}"
    else:
        try:
            subprocess.run(["sudo", "userdel", username], capture_output=True, text=True, check=True)
            return True, f"Usuario '{username}' eliminado."
        except subprocess.CalledProcessError as e:
            return False, f"Error al eliminar '{username}': {e.stderr or e.stdout}"

def fetch_sheet_data(hostname):
    try:
        response = requests.get(WEBHOOK_URL, params={"hostname": hostname}, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"ERROR al consultar la hoja: {e}")
        return None

def clear_control_columns(hostname):
    """Envía POST para limpiar NEW_USERS y DELETE_USERS."""
    payload = {
        "hostname": hostname,
        "clear_new": "",
        "clear_delete": ""
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"ERROR al limpiar columnas de control: {e}")
        return False

def main():
    print("=== Sincronizador de usuarios (3 columnas) ===\n")
    hostname = get_hostname()
    sistema = get_os_name()
    print(f"Hostname: {hostname}  |  Sistema: {sistema}\n")

    # 1. Obtener instrucciones desde la hoja
    sheet_data = fetch_sheet_data(hostname)
    if not sheet_data:
        print("No se pudo obtener datos de la hoja. Abortando.")
        sys.exit(1)

    if not sheet_data.get("exists"):
        print("Máquina no registrada en la hoja. Se creará la fila al finalizar.")
        new_users_str = delete_users_str = ""
    else:
        new_users_str = sheet_data.get("new_users", "").strip()
        delete_users_str = sheet_data.get("delete_users", "").strip()

    # Parsear listas
    new_users = [u.strip() for u in new_users_str.split(",") if u.strip()]
    delete_users = [u.strip() for u in delete_users_str.split(",") if u.strip()]

    # Validaciones
    if len(new_users) != len(set(new_users)):
        print("ERROR: Hay nombres duplicados en NEW_USERS.")
        sys.exit(1)
    if len(delete_users) != len(set(delete_users)):
        print("ERROR: Hay nombres duplicados en DELETE_USERS.")
        sys.exit(1)
    conflict = set(new_users) & set(delete_users)
    if conflict:
        print(f"ERROR: Usuarios en ambas listas (new y delete): {conflict}")
        sys.exit(1)

    # 2. Procesar eliminaciones
    if delete_users:
        print("--- Procesando eliminaciones ---")
        for user in delete_users:
            if user_exists(user):
                ok, msg = delete_user(user)
                print(msg)
            else:
                print(f"ERROR: No se puede eliminar '{user}' porque no existe localmente.")

    # 3. Procesar creaciones
    if new_users:
        print("\n--- Procesando creaciones ---")
        for user in new_users:
            if user_exists(user):
                print(f"ERROR: No se puede crear '{user}' porque ya existe localmente.")
            else:
                ok, msg = create_user(user)
                print(msg)

    # 4. Limpiar columnas de control en la hoja (siempre, incluso si no había cambios)
    print("\nLimpiando columnas NEW_USERS y DELETE_USERS en la hoja...")
    if clear_control_columns(hostname):
        print("Columnas limpiadas correctamente.")
    else:
        print("No se pudieron limpiar las columnas, pero los cambios locales ya se aplicaron.")

if __name__ == "__main__":
    # Verificar permisos
    if get_os_name() == "Windows":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("AVISO: Este script debe ejecutarse como Administrador para modificar usuarios.")
    else:
        if os.geteuid() != 0:
            print("AVISO: Este script debe ejecutarse con sudo para modificar usuarios.")
    main()
