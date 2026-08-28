"""
models.py
Manejo de la base de datos con sqlite3 puro (sin librerías externas).
Aquí viven todas las funciones que leen o escriben en database.db
"""

import sqlite3

DB_NAME = "database.db"


def get_conn():
    """Abre una conexión a la base de datos y permite acceder a las
    columnas por nombre (fila['nombre']) en vez de solo por índice."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def crear_tablas():
    """Crea las tablas si no existen. Se llama una vez al iniciar la app."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            categoria_id INTEGER NOT NULL,
            disponible INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (categoria_id) REFERENCES categorias (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nombre_tienda TEXT,
            logo_path TEXT,
            clave_admin TEXT,
            clave_cocina TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS mesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_id INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mesa_id) REFERENCES mesas (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            notas TEXT,
            FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    """)

    # Nos aseguramos de que siempre exista la fila única de configuración
    cur.execute("SELECT id FROM configuracion WHERE id = 1")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO configuracion (id, nombre_tienda, logo_path, clave_admin, clave_cocina) "
            "VALUES (1, NULL, NULL, NULL, NULL)"
        )

    conn.commit()
    conn.close()


# ---------- CONFIGURACIÓN DE LA TIENDA ----------

def obtener_configuracion():
    conn = get_conn()
    fila = conn.execute("SELECT * FROM configuracion WHERE id = 1").fetchone()
    conn.close()
    return dict(fila) if fila else None


def esta_configurado():
    """True si el propietario ya puso el nombre de la tienda (paso obligatorio)."""
    config = obtener_configuracion()
    return bool(config and config["nombre_tienda"])


def guardar_configuracion(nombre_tienda, logo_path, clave_admin, clave_cocina):
    conn = get_conn()
    conn.execute(
        """UPDATE configuracion
           SET nombre_tienda = ?, logo_path = ?, clave_admin = ?, clave_cocina = ?
           WHERE id = 1""",
        (nombre_tienda, logo_path, clave_admin, clave_cocina)
    )
    conn.commit()
    conn.close()


def verificar_clave_admin(clave):
    config = obtener_configuracion()
    return bool(config and config["clave_admin"] and config["clave_admin"] == clave)


def verificar_clave_cocina(clave):
    config = obtener_configuracion()
    return bool(config and config["clave_cocina"] and config["clave_cocina"] == clave)


# ---------- CATEGORÍAS ----------

def obtener_categorias():
    conn = get_conn()
    filas = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    conn.close()
    return [dict(f) for f in filas]


def crear_categoria(nombre):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (nombre,)
    )
    conn.commit()
    conn.close()


def renombrar_categoria(categoria_id, nuevo_nombre):
    conn = get_conn()
    conn.execute(
        "UPDATE categorias SET nombre = ? WHERE id = ?",
        (nuevo_nombre, categoria_id)
    )
    conn.commit()
    conn.close()


def eliminar_categoria(categoria_id):
    """Solo elimina si ningún producto la está usando, para no dejar
    productos huérfanos."""
    conn = get_conn()
    en_uso = conn.execute(
        "SELECT COUNT(*) AS total FROM productos WHERE categoria_id = ?",
        (categoria_id,)
    ).fetchone()["total"]

    if en_uso > 0:
        conn.close()
        return False

    conn.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
    conn.commit()
    conn.close()
    return True


# ---------- PRODUCTOS ----------

def obtener_productos(solo_disponibles=True):
    """Trae los productos junto con el nombre de su categoría."""
    conn = get_conn()
    base = """SELECT productos.*, categorias.nombre AS categoria_nombre
              FROM productos
              JOIN categorias ON productos.categoria_id = categorias.id"""
    if solo_disponibles:
        filas = conn.execute(base + " WHERE productos.disponible = 1").fetchall()
    else:
        filas = conn.execute(base).fetchall()
    conn.close()
    return [dict(f) for f in filas]


def crear_producto(nombre, precio, categoria_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO productos (nombre, precio, categoria_id) VALUES (?, ?, ?)",
        (nombre, precio, categoria_id)
    )
    conn.commit()
    conn.close()


def actualizar_producto(producto_id, nombre, precio, categoria_id, disponible):
    conn = get_conn()
    conn.execute(
        """UPDATE productos
           SET nombre = ?, precio = ?, categoria_id = ?, disponible = ?
           WHERE id = ?""",
        (nombre, precio, categoria_id, disponible, producto_id)
    )
    conn.commit()
    conn.close()


def eliminar_producto(producto_id):
    conn = get_conn()
    conn.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()


# ---------- MESAS ----------

def obtener_o_crear_mesa(numero):
    conn = get_conn()
    fila = conn.execute(
        "SELECT * FROM mesas WHERE numero = ?", (numero,)
    ).fetchone()

    if fila is None:
        conn.execute("INSERT INTO mesas (numero) VALUES (?)", (numero,))
        conn.commit()
        fila = conn.execute(
            "SELECT * FROM mesas WHERE numero = ?", (numero,)
        ).fetchone()

    conn.close()
    return dict(fila)


# ---------- PEDIDOS ----------

def crear_pedido(mesa_id, items):
    """
    items: lista de diccionarios, cada uno con
           {"producto_id": int, "cantidad": int, "notas": str}
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO pedidos (mesa_id, estado) VALUES (?, 'pendiente')",
        (mesa_id,)
    )
    pedido_id = cur.lastrowid

    for item in items:
        cur.execute(
            """INSERT INTO items_pedido (pedido_id, producto_id, cantidad, notas)
               VALUES (?, ?, ?, ?)""",
            (pedido_id, item["producto_id"], item["cantidad"], item.get("notas", ""))
        )

    conn.commit()
    conn.close()
    return pedido_id


def obtener_pedidos(estado=None):
    """Trae los pedidos junto con el número de mesa y sus items."""
    conn = get_conn()

    if estado:
        pedidos = conn.execute(
            """SELECT pedidos.*, mesas.numero AS mesa_numero
               FROM pedidos
               JOIN mesas ON pedidos.mesa_id = mesas.id
               WHERE pedidos.estado = ?
               ORDER BY pedidos.fecha ASC""",
            (estado,)
        ).fetchall()
    else:
        pedidos = conn.execute(
            """SELECT pedidos.*, mesas.numero AS mesa_numero
               FROM pedidos
               JOIN mesas ON pedidos.mesa_id = mesas.id
               ORDER BY pedidos.fecha ASC"""
        ).fetchall()

    resultado = []
    for pedido in pedidos:
        items = conn.execute(
            """SELECT items_pedido.*, productos.nombre AS producto_nombre,
                      productos.precio AS producto_precio
               FROM items_pedido
               JOIN productos ON items_pedido.producto_id = productos.id
               WHERE items_pedido.pedido_id = ?""",
            (pedido["id"],)
        ).fetchall()

        pedido_dict = dict(pedido)
        pedido_dict["items"] = [dict(i) for i in items]
        resultado.append(pedido_dict)

    conn.close()
    return resultado


def actualizar_estado_pedido(pedido_id, nuevo_estado):
    conn = get_conn()
    conn.execute(
        "UPDATE pedidos SET estado = ? WHERE id = ?",
        (nuevo_estado, pedido_id)
    )
    conn.commit()
    conn.close()


def obtener_cuenta(mesa_id):
    """Suma el total de todos los pedidos activos de una mesa."""
    conn = get_conn()
    filas = conn.execute(
        """SELECT items_pedido.cantidad, productos.precio, productos.nombre
           FROM pedidos
           JOIN items_pedido ON items_pedido.pedido_id = pedidos.id
           JOIN productos ON items_pedido.producto_id = productos.id
           WHERE pedidos.mesa_id = ? AND pedidos.estado != 'entregado'""",
        (mesa_id,)
    ).fetchall()
    conn.close()

    items = [dict(f) for f in filas]
    total = sum(i["cantidad"] * i["precio"] for i in items)
    return {"items": items, "total": total}