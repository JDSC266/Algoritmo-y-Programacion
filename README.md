# Sistema de Pedidos desde la Mesa

Proyecto de programación: los clientes de un restaurante piden desde su
celular escaneando o abriendo el enlace de su mesa, sin esperar al mesero.
Backend 100% Python (Flask + sqlite3), interfaz web en HTML y CSS.

## Estructura del proyecto

```
restaurante/
├── app.py                  # Rutas de Flask (cliente, cocina, admin)
├── models.py                # Acceso a la base de datos (sqlite3 puro)
├── requirements.txt          # Dependencias
├── database.db               # Se crea sola al arrancar (no se sube a git)
├── templates/
│   ├── base.html              # Plantilla compartida (CSS, favicon, título)
│   ├── configuracion.html      # Primer uso: nombre, logo, claves
│   ├── admin_login.html         # Acceso al panel de administración
│   ├── admin.html                # Gestión de platillos y categorías
│   ├── cocina_login.html          # Acceso al panel de cocina
│   ├── cocina.html                 # Tablero de pedidos entrantes
│   ├── menu.html                    # Vista del cliente en la mesa
│   └── cuenta.html                   # Total a pagar de una mesa
└── static/
    ├── css/estilo.css              # Todos los estilos
    └── logos/                       # Aquí se guarda el logo subido
```

## Requisitos

- Python 3.10 o superior instalado ([python.org](https://www.python.org/downloads/))
  - Al instalar en Windows, marca la casilla **"Add python.exe to PATH"**.

## Instalación (Windows)

1. Descomprime la carpeta del proyecto donde quieras, por ejemplo
   `C:\Users\TuUsuario\Documents\restaurante`.

2. Abre **PowerShell** o **CMD** en esa carpeta:
   - Botón derecho dentro de la carpeta en el Explorador de Windows →
     **"Abrir en Terminal"** (o Shift + clic derecho → "Abrir ventana de
     PowerShell aquí" en versiones más antiguas de Windows).

3. (Recomendado) Crea un entorno virtual, para no mezclar las librerías
   con otros proyectos de Python que tengas:

   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

   Si `activate` da error de permisos en PowerShell, ejecuta primero:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```
   y vuelve a intentar.

4. Instala las dependencias:

   ```powershell
   pip install -r requirements.txt
   ```

5. Ejecuta la aplicación:

   ```powershell
   python app.py
   ```

6. Verás algo como:

   ```
   * Running on http://127.0.0.1:5000
   ```

   Abre esa dirección en tu navegador: **http://127.0.0.1:5000**

## Primer uso

La primera vez que abras la app, te mandará directo a **/configuracion**:

1. Pon el nombre del restaurante.
2. (Opcional) Sube un logo `.ico`.
3. Define una **clave de administración** (para editar platillos y precios)
   y una **clave de cocina** (para ver los pedidos entrantes) — pueden ser
   distintas para no dar acceso completo a los meseros.

Después de guardar, entras directo al panel de administración
(**/admin**) para cargar tus categorías y platillos.

## Cómo se usa

| Quién | Entra a | Para qué |
|---|---|---|
| Cliente en la mesa 5 | `http://127.0.0.1:5000/mesa/5` | Ver el menú y pedir |
| Cliente | `http://127.0.0.1:5000/mesa/5/cuenta` | Ver el total a pagar |
| Cocina / meseros | `http://127.0.0.1:5000/cocina` | Ver pedidos entrantes (pide clave de cocina) |
| Propietario | `http://127.0.0.1:5000/admin` | Gestionar platillos, precios y categorías (pide clave de admin) |

Cada mesa tiene su propio número en la URL (`/mesa/1`, `/mesa/2`, etc.). En
un restaurante real, cada número se generaría con un QR pegado en la mesa;
para la demo de clase basta con cambiar el número en la barra de direcciones.

## Probar desde el celular en la misma red (para la sustentación)

Por defecto Flask solo responde en `127.0.0.1` (tu propio PC). Para que un
celular conectado al mismo Wi-Fi pueda abrir el menú como si fuera un
cliente real:

1. Al final de `app.py`, cambia la última línea por:

   ```python
   app.run(debug=True, host="0.0.0.0")
   ```

2. Averigua la IP de tu PC en la red local con `ipconfig` en PowerShell
   (busca "Dirección IPv4", algo como `192.168.1.15`).

3. En el celular (misma red Wi-Fi), abre:
   `http://192.168.1.15:5000/mesa/1`

## Notas técnicas

- El acceso a la base de datos está en `models.py` usando `sqlite3` puro
  (sin librerías externas como SQLAlchemy).
- El panel de cocina se actualiza solo cada 8 segundos con
  `<meta http-equiv="refresh">` — 100% HTML, sin JavaScript. Si el profe
  autoriza JS más adelante, se puede reemplazar por `fetch()` contra el
  endpoint `/api/pedidos`, que ya está listo y devuelve JSON.
- `app.secret_key` en `app.py` está con un valor de ejemplo; para producción
  real se cambiaría por uno secreto, pero para el proyecto de clase no es
  necesario tocarlo.