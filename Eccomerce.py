import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Gestión Taller Benja", layout="wide")

# ==========================================
# GESTIÓN DE USUARIOS (PERSISTENCIA EN CSV)
# ==========================================
if not os.path.exists('usuarios.csv'):
    df_inicial = pd.DataFrame([
        {"usuario": "benja", "clave": "admin123", "rol": "admin"},
        {"usuario": "operario", "clave": "taller2026", "rol": "user"}
    ])
    df_inicial.to_csv('usuarios.csv', index=False, sep=';')

def cargar_usuarios():
    df = pd.read_csv('usuarios.csv', sep=';')
    df['usuario'] = df['usuario'].astype(str).str.strip().str.lower()
    return df

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_rol' not in st.session_state:
    st.session_state.usuario_rol = None
if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

# PANTALLA DE LOGIN
if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema - Taller Benja")
    input_user = st.text_input("Usuario:").strip().lower()
    input_pass = st.text_input("Contraseña:", type="password")
    
    if st.button("Iniciar Sesión"):
        df_users = cargar_usuarios()
        user_match = df_users[(df_users['usuario'] == input_user) & (df_users['clave'].astype(str) == input_pass)]
        
        if not user_match.empty:
            st.session_state.autenticado = True
            st.session_state.usuario_rol = user_match.iloc[0]['rol']
            st.session_state.usuario_actual = input_user
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.stop()

# ==========================================
# CARGAR DATOS DEL TALLER
# ==========================================
def cargar_datos_taller():
    stock = pd.read_csv('stock.csv', sep=';')
    historial = pd.read_csv('historial.csv', sep=';')
    stock.columns = stock.columns.str.strip().str.lower()
    historial.columns = historial.columns.str.strip().str.lower()
    return stock, historial

if 'stock_df' not in st.session_state or 'historial_df' not in st.session_state:
    st.session_state.stock_df, st.session_state.historial_df = cargar_datos_taller()

if 'recovery_backup' not in st.session_state:
    st.session_state.recovery_backup = tuple(st.session_state.stock_df.itertuples(index=False))

# Variables para guardar el último ticket generado en pantalla
if 'ultimo_ticket' not in st.session_state:
    st.session_state.ultimo_ticket = None

# ==========================================
# SIDEBAR: ACCIONES DEL PROGRAMA
# ==========================================
st.sidebar.title(f"👤 {st.session_state.usuario_actual.upper()}")
st.sidebar.write(f"**Rol:** {st.session_state.usuario_rol.upper()}")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.autenticado = False
    st.session_state.usuario_rol = None
    st.session_state.usuario_actual = None
    st.session_state.ultimo_ticket = None
    st.rerun()

st.sidebar.markdown("---")

# Registro de usuarios (Solo Admin)
if st.session_state.usuario_rol == "admin":
    st.sidebar.header("➕ Registrar Nuevo Usuario")
    nuevo_usuario = st.sidebar.text_input("Nuevo Usuario:").strip().lower()
    nueva_clave = st.sidebar.text_input("Nueva Contraseña:", type="password")
    nuevo_rol = st.sidebar.selectbox("Rol del Perfil:", ["user", "admin"])
    
    if st.sidebar.button("💾 Guardar Usuario"):
        if nuevo_usuario and nueva_clave:
            df_users = cargar_usuarios()
            if nuevo_usuario in df_users['usuario'].values:
                st.sidebar.error("El usuario ya existe.")
            else:
                nuevo_registro = pd.DataFrame([{"usuario": nuevo_usuario, "clave": nueva_clave, "rol": nuevo_rol}])
                df_users = pd.concat([df_users, nuevo_registro], ignore_index=True)
                df_users.to_csv('usuarios.csv', index=False, sep=';')
                st.sidebar.success(f"¡Usuario '{nuevo_usuario}' creado!")
                st.rerun()
        else:
            st.sidebar.error("Completá todos los campos.")
    st.sidebar.markdown("---")

# Formulario de Movimientos
st.sidebar.header("Registrar Movimiento")
id_prod = st.sidebar.number_input("ID del Repuesto", min_value=1, step=1)
cantidad = st.sidebar.number_input("Cantidad", min_value=1, step=1)
tipo_op = st.sidebar.selectbox("Operación", ["Venta", "Compra"])

if st.sidebar.button("Procesar Transacción"):
    if id_prod in st.session_state.stock_df['id'].values:
        fila_prod = st.session_state.stock_df[st.session_state.stock_df['id'] == id_prod]
        nombre_p = fila_prod['nombre'].values[0]
        precio_p = fila_prod['precio'].values[0]
        
        if tipo_op == "Venta":
            stock_actual = fila_prod['cantidad'].values[0]
            if stock_actual < cantidad:
                st.sidebar.error(f"Stock insuficiente. Quedan {stock_actual:.0f} unidades.")
                st.stop() 
            st.session_state.stock_df.loc[st.session_state.stock_df['id'] == id_prod, 'cantidad'] -= cantidad
            
            # Guardamos los datos para armar el comprobante de venta
            st.session_state.ultimo_ticket = {
                "tipo": "FACTURA B - CONSUMIDOR FINAL",
                "numero": f"0001-{int(datetime.now().timestamp())}",
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "detalle": nombre_p,
                "cantidad": cantidad,
                "precio_unitario": precio_p,
                "total": cantidad * precio_p,
                "atendio": st.session_state.usuario_actual
            }
        else:
            st.session_state.stock_df.loc[st.session_state.stock_df['id'] == id_prod, 'cantidad'] += cantidad
            st.session_state.ultimo_ticket = None # Las compras no generan ticket de venta
        
        st.session_state.stock_df.to_csv('stock.csv', index=False, sep=';')
        
        nuevo_mov = {
            'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'id_producto': id_prod,
            'tipo': tipo_op,
            'cantidad': cantidad,
            'usuario': st.session_state.usuario_actual
        }
        st.session_state.historial_df = pd.concat([st.session_state.historial_df, pd.DataFrame([nuevo_mov])], ignore_index=True)
        st.session_state.historial_df.to_csv('historial.csv', index=False, sep=';')
        
        st.sidebar.success(f"¡{tipo_op} exitosa!")
        st.rerun()
    else:
        st.sidebar.error(f"El ID {id_prod} no existe.")

# Recovery (Solo Admin)
if st.session_state.usuario_rol == "admin":
    st.sidebar.markdown("---")
    st.sidebar.header("🔄 Sistema de Recovery")
    if st.sidebar.button("⏪ Volver al Punto de Control"):
        columnas = st.session_state.stock_df.columns
        st.session_state.stock_df = pd.DataFrame(st.session_state.recovery_backup, columns=columnas)
        st.session_state.stock_df.to_csv('stock.csv', index=False, sep=';')
        st.sidebar.success("¡Sistema restaurado!")
        st.rerun()

# ==========================================
# 3. PANTALLA PRINCIPAL: INVENTARIO
# ==========================================
st.title("🛠️ Sistema de Stock - Taller de Repuestos")

# Mostrar ticket de la última venta si existe
if st.session_state.ultimo_ticket:
    st.info("🧾 Última transacción registrada. Listo para entrega al cliente:")
    with st.container(border=True):
        t = st.session_state.ultimo_ticket
        st.markdown(f"### {t['tipo']}")
        st.write(f"**Nro Comprobante:** {t['numero']} | **Fecha:** {t['fecha']}")
        st.markdown("---")
        st.write(f"**Detalle del Repuesto:** {t['detalle']}")
        st.write(f"**Cantidad:** {t['cantidad']} unidades | **Precio Unit.:** ${t['precio_unitario']:,.2f}")
        st.markdown(f"## TOTAL A PAGAR: ${t['total']:,.2f}")
        st.caption(f"Atendido por: {t['atendio'].upper()} | Taller de Repuestos Benja")
    if st.button("Limpiar Pantalla / Siguiente Cliente"):
        st.session_state.ultimo_ticket = None
        st.rerun()

st.subheader("📦 Inventario en Tiempo Real")

def resaltar_bajo_stock(row):
    cant = row.get('cantidad', 0)
    minimo = row.get('stock_minimo', 0)
    if cant <= minimo:
        return ['background-color: #ffcccc'] * len(row)
    return [''] * len(row)

st.dataframe(st.session_state.stock_df.style.format({
    "id": "{:.0f}", 
    "cantidad": "{:.0f}", 
    "stock_minimo": "{:.0f}",
    "precio": "${:,.2f}"
}).apply(resaltar_bajo_stock, axis=1))

# ALERTAS Y GENERACIÓN DE ORDEN DE COMPRA
st.subheader("⚠️ Alertas de Reposición Crítica")
hay_alertas = False
for index, row in st.session_state.stock_df.iterrows():
    cant = row.get('cantidad', 0)
    minimo = row.get('stock_minimo', 0)
    nombre_prod = row.get('nombre', 'Producto')
    marca_prod = row.get('marca', '')
    
    if cant <= minimo:
        hay_alertas = True
        col_cartel, col_boton = st.columns([3, 1])
        with col_cartel:
            st.warning(f"**Falta Stock:** **{nombre_prod}** ({marca_prod}) llegó a **{cant:.0f}** unidades. (Mínimo: {minimo:.0f})")
        with col_boton:
            # Botón interactivo para simular la orden de compra en el momento
            if st.button(f"📝 Orden de Compra ID {row.get('id'):.0f}"):
                st.session_state.orden_compra_texto = f"""
                **ORDEN DE COMPRA GENERADA**
                **Para:** Distribuidora Mayorista de Repuestos
                **Fecha Emisión:** {datetime.now().strftime('%Y-%m-%d')}
                
                Solicitamos el envío urgente del siguiente ítem para reposición de stock:
                - **Producto:** {nombre_prod}
                - **Marca:** {marca_prod}
                - **Cantidad sugerida a pedir:** {(minimo - cant) + 10:.0f} unidades.
                
                Autorizado por: {st.session_state.usuario_actual.upper()} - Taller Benja
                """

if not hay_alertas:
    st.success("✅ Todo en orden. Todos los repuestos tienen stock suficiente.")
    st.session_state.orden_compra_texto = None

# Si se tocó el botón de orden de compra, se muestra acá
if 'orden_compra_texto' in st.session_state and st.session_state.orden_compra_texto:
    st.info("📋 Documento de Pedido listo para enviar al Proveedor:")
    st.code(st.session_state.orden_compra_texto, language="markdown")
    if st.button("Cerrar Vista de Orden de Compra"):
        st.session_state.orden_compra_texto = None
        st.rerun()

# HISTORIAL
st.subheader("📜 Últimos Movimientos")
st.dataframe(st.session_state.historial_df.tail(10).style.format({
    "id_producto": "{:.0f}", 
    "cantidad": "{:.0f}"
}))

# ==========================================
# 4. EXCLUSIVO ADMIN: PANEL DE CONTROL DE USUARIOS
# ==========================================
if st.session_state.usuario_rol == "admin":
    st.markdown("---")
    st.subheader("🔑 Panel de Control de Seguridad (Solo visible para ADMIN)")
    df_visibilidad = cargar_usuarios()
    col_tabla, col_eliminar = st.columns([2, 1])
    with col_tabla:
        st.markdown("**Usuarios Registrados Activos:**")
        # CORREGIDO ACÁ: Cambiamos df_users por df_visibilidad
        st.dataframe(df_visibilidad, use_container_width=True) 
    with col_eliminar:
        st.markdown("**🗑️ Eliminar Usuario del Sistema:**")
        lista_usuarios = df_visibilidad['usuario'].tolist()
        usuario_a_eliminar = st.selectbox("Seleccionar usuario para dar de baja:", lista_usuarios)
        if st.button("❌ Confirmar Baja"):
            if usuario_a_eliminar == st.session_state.usuario_actual:
                st.error("No podés eliminar tu propio usuario en uso.")
            else:
                df_actualizado = df_visibilidad[df_visibilidad['usuario'] != usuario_a_eliminar]
                df_actualizado.to_csv('usuarios.csv', index=False, sep=';')
                st.success(f"El usuario '{usuario_a_eliminar}' fue eliminado con éxito.")
                st.rerun()