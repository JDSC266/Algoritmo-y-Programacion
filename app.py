"""
app.py
Rutas de Flask para el sistema de pedidos del restaurante.
100% Python: Flask + Jinja2 (plantillas) + sqlite3 (en models.py).
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import models

app = Flask(__name__)
app.secret_key = "cambia-esta-clave-por-una-propia"  # necesaria para usar session

CARPETA_LOGOS = os.path.join("static", "logos")
os.makedirs(CARPETA_LOGOS, exist_ok=True)


# ---------------------------------------------------------
# Se ejecuta antes de CADA petición: si la tienda todavía no
# tiene nombre configurado, obliga a pasar por /configuracion
# ---------------------------------------------------------
@app.before_request
def revisar_configuracion():
    rutas_permitidas = ("configuracion", "static")
    if request.endpoint in rutas_permitidas:
        return
    if not models.esta_configurado():
        return redirect(url_for("configuracion"))


@app.context_processor
def inyectar_configuracion():
    """Hace que 'config' esté disponible en TODAS las plantillas
    automáticamente, sin tener que pasarla a mano en cada ruta."""
    return {"config": models.obtener_configuracion()}


@app.template_filter("moneda")
def moneda(valor):
    """Formatea 18000 como $18.000"""
    return "${:,.0f}".format(valor).replace(",", ".")


# ---------------------------------------------------------
# CONFIGURACIÓN INICIAL (nombre de la tienda + logo)
# ---------------------------------------------------------
@app.route("/configuracion", methods=["GET", "POST"])
def configuracion():
    if request.method == "POST":
        nombre_tienda = request.form.get("nombre_tienda", "").strip()
        clave_admin = request.form.get("clave_admin", "").strip()
        clave_cocina = request.form.get("clave_cocina", "").strip()
        logo_path = None

        archivo_logo = request.files.get("logo")
        if archivo_logo and archivo_logo.filename:
            logo_path = os.path.join(CARPETA_LOGOS, "logo.ico")
            archivo_logo.save(logo_path)

        if nombre_tienda and clave_admin and clave_cocina:
            models.guardar_configuracion(nombre_tienda, logo_path, clave_admin, clave_cocina)
            return redirect(url_for("admin_panel"))

    return render_template("configuracion.html")


# ---------------------------------------------------------
# CLIENTE: menú y toma de pedido desde la mesa
# ---------------------------------------------------------
@app.route("/mesa/<int:numero>")
def menu(numero):
    mesa = models.obtener_o_crear_mesa(numero)
    productos = models.obtener_productos(solo_disponibles=True)
    categorias = models.obtener_categorias()
    pedido_enviado = request.args.get("pedido") == "enviado"
    return render_template(
        "menu.html",
        mesa=mesa,
        productos=productos,
        categorias=categorias,
        pedido_enviado=pedido_enviado
    )


@app.route("/mesa/<int:numero>/pedir", methods=["POST"])
def hacer_pedido(numero):
    mesa = models.obtener_o_crear_mesa(numero)

    productos_ids = request.form.getlist("producto_id")
    cantidades = request.form.getlist("cantidad")
    notas = request.form.getlist("notas")

    items = []
    for producto_id, cantidad, nota in zip(productos_ids, cantidades, notas):
        if int(cantidad) > 0:
            items.append({
                "producto_id": int(producto_id),
                "cantidad": int(cantidad),
                "notas": nota
            })

    if items:
        models.crear_pedido(mesa["id"], items)
        return redirect(url_for("menu", numero=numero, pedido="enviado"))

    return redirect(url_for("menu", numero=numero))


@app.route("/mesa/<int:numero>/cuenta")
def cuenta(numero):
    mesa = models.obtener_o_crear_mesa(numero)
    datos_cuenta = models.obtener_cuenta(mesa["id"])
    return render_template("cuenta.html", mesa=mesa, cuenta=datos_cuenta)


# ---------------------------------------------------------
# COCINA: login (clave separada de la del admin)
# ---------------------------------------------------------
@app.route("/cocina/login", methods=["GET", "POST"])
def cocina_login():
    error = None
    if request.method == "POST":
        clave = request.form.get("clave", "")
        if models.verificar_clave_cocina(clave):
            session["es_cocina"] = True
            return redirect(url_for("cocina"))
        error = "Clave incorrecta"
    return render_template("cocina_login.html", error=error)


@app.route("/cocina/logout")
def cocina_logout():
    session.pop("es_cocina", None)
    return redirect(url_for("cocina_login"))


def requiere_cocina():
    """Devuelve una redirección si no hay sesión de cocina activa (ni de admin,
    que también puede entrar), o None si sí puede pasar."""
    if not session.get("es_cocina") and not session.get("es_admin"):
        return redirect(url_for("cocina_login"))
    return None


# ---------------------------------------------------------
# COCINA: ver y actualizar el estado de los pedidos
# ---------------------------------------------------------
@app.route("/cocina")
def cocina():
    redireccion = requiere_cocina()
    if redireccion:
        return redireccion

    pedidos = models.obtener_pedidos()
    return render_template("cocina.html", pedidos=pedidos)


@app.route("/cocina/pedido/<int:pedido_id>/estado", methods=["POST"])
def cambiar_estado_pedido(pedido_id):
    redireccion = requiere_cocina()
    if redireccion:
        return redireccion

    nuevo_estado = request.form.get("estado")
    if nuevo_estado in ("pendiente", "en_preparacion", "listo", "entregado"):
        models.actualizar_estado_pedido(pedido_id, nuevo_estado)
    return redirect(url_for("cocina"))


# Endpoint JSON, solo por si el profe autoriza usar JavaScript más adelante
@app.route("/api/pedidos")
def api_pedidos():
    redireccion = requiere_cocina()
    if redireccion:
        return redireccion

    return jsonify(models.obtener_pedidos())


# ---------------------------------------------------------
# ADMIN: login
# ---------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        clave = request.form.get("clave", "")
        if models.verificar_clave_admin(clave):
            session["es_admin"] = True
            return redirect(url_for("admin_panel"))
        error = "Clave incorrecta"
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("es_admin", None)
    return redirect(url_for("admin_login"))


def requiere_admin():
    """Devuelve una redirección si no hay sesión de admin activa, o None si sí la hay."""
    if not session.get("es_admin"):
        return redirect(url_for("admin_login"))
    return None


# ---------------------------------------------------------
# ADMIN: panel principal (productos + categorías)
# ---------------------------------------------------------
@app.route("/admin")
def admin_panel():
    redireccion = requiere_admin()
    if redireccion:
        return redireccion

    productos = models.obtener_productos(solo_disponibles=False)
    categorias = models.obtener_categorias()
    return render_template(
        "admin.html", productos=productos, categorias=categorias
    )


@app.route("/admin/productos/nuevo", methods=["POST"])
def admin_producto_nuevo():
    redireccion = requiere_admin()
    if redireccion:
        return redireccion

    nombre = request.form.get("nombre", "").strip()
    precio = request.form.get("precio", "0")
    categoria_id = request.form.get("categoria_id")

    if nombre and categoria_id:
        models.crear_producto(nombre, float(precio), int(categoria_id))

    return redirect(url_for("admin_panel"))


@app.route("/admin/productos/<int:producto_id>/editar", methods=["POST"])
def admin_producto_editar(producto_id):
    redireccion = requiere_admin()
    if redireccion:
        return redireccion

    nombre = request.form.get("nombre", "").strip()
    precio = request.form.get("precio", "0")
    categoria_id = request.form.get("categoria_id")
    disponible = 1 if request.form.get("disponible") == "on" else 0

    if nombre and categoria_id:
        models.actualizar_producto(
            producto_id, nombre, float(precio), int(categoria_id), disponible
        )

    return redirect(url_for("admin_panel"))


@app.route("/admin/productos/<int:producto_id>/eliminar", methods=["POST"])
def admin_producto_eliminar(producto_id):
    redireccion = requiere_admin()
    if redireccion:
        return redireccion

    models.eliminar_producto(producto_id)
    return redirect(url_for("admin_panel"))


@app.route("/admin/categorias/nueva", methods=["POST"])
def admin_categoria_nueva():
    redireccion = requiere_admin()
    if redireccion:
        return redireccion

    nombre = request.form.get("nombre", "").strip()
    if nombre:
        models.crear_categoria(nombre)

    return redirect(url_for("admin_panel"))


@app.route("/admin/categorias/<int:categoria_id>/renombrar", methods=["POST"])
def admin_categoria_renombrar(categoria_id):
    redireccion = requiere_admin()
    if redireccion:
        return redireccion

    nuevo_nombre = request.form.get("nombre", "").strip()
    if nuevo_nombre:
        models.renombrar_categoria(categoria_id, nuevo_nombre)

    return redirect(url_for("admin_panel"))


@app.route("/admin/categorias/<int:categoria_id>/eliminar", methods=["POST"])
def admin_categoria_eliminar(categoria_id):
    redireccion = requiere_admin()
    if redireccion:
        return redireccion

    ok = models.eliminar_categoria(categoria_id)
    if not ok:
        # Todavía hay productos usando esta categoría
        pass

    return redirect(url_for("admin_panel"))


if __name__ == "__main__":
    models.crear_tablas()
    app.run(debug=True)
