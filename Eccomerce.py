import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN Y RUTAS ABSOLUTAS (Evita el bug de la consola)
# ==========================================
CATEGORIAS_DISPONIBLES = ["Filtros", "Frenos", "Motor y Encendido", "Transmisión", "Lubricantes", "Otros"]
st.set_page_config(page_title="Gestión Diesel Messina", layout="wide")

# Forzamos al sistema a mirar SOLAMENTE adentro de la carpeta del proyecto
DIR_BASE = os.path.dirname(os.path.abspath(__file__))
PATH_STOCK = os.path.join(DIR_BASE, 'stock.csv')
PATH_USUARIOS = os.path.join(DIR_BASE, 'usuarios.csv')
PATH_HISTORIAL = os.path.join(DIR_BASE, 'historial.csv')

# ==========================================
# 2. COMPONENTE DE PERSISTENCIA Y SEGURIDAD (CSV)
# ==========================================
if not os.path.exists(PATH_USUARIOS):
    pd.DataFrame([{"usuario": "benja", "clave": "admin123", "rol": "admin"},
                  {"usuario": "operario", "clave": "taller2026", "rol": "user"}]).to_csv(PATH_USUARIOS, index=False, sep=';')

def cargar_usuarios():
    df = pd.read_csv(PATH_USUARIOS, sep=';')
    df['usuario'] = df['usuario'].astype(str).str.strip().str.lower()
    return df

def guardar_y_sanear_stock(df):
    columnas = ['id', 'nombre', 'marca', 'categoria', 'cantidad', 'precio', 'stock_minimo']
    
    for col in columnas:
        if col not in df.columns:
            df[col] = 0 if col in ['id', 'cantidad', 'stock_minimo', 'precio'] else "Otros"
            
    df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
    df['nombre'] = df['nombre'].astype(str).fillna("Sin Nombre")
    df['marca'] = df['marca'].astype(str).fillna("Sin Marca")
    df['categoria'] = df['categoria'].astype(str).fillna("Otros").replace("nan", "Otros")
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(float)
    df['precio'] = pd.to_numeric(df['precio'], errors='coerce').fillna(0.0).astype(float)
    df['stock_minimo'] = pd.to_numeric(df['stock_minimo'], errors='coerce').fillna(0).astype(float)
    
    df = df[columnas]
    df.to_csv(PATH_STOCK, index=False, sep=';')
    st.session_state.stock_df = df
    return df

# ==========================================
# 3. CONTROL DE ACCESO (PANTALLA DE LOGIN)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado, st.session_state.usuario_rol, st.session_state.usuario_actual = False, None, None

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema - Diesel Messina")
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
# 4. INICIALIZACIÓN DE DATOS EN MEMORIA RAM
# ==========================================
if 'stock_df' not in st.session_state or 'historial_df' not in st.session_state:
    if not os.path.exists(PATH_HISTORIAL):
        pd.DataFrame(columns=['fecha', 'id_producto', 'tipo', 'cantidad', 'usuario', 'comprobante_texto']).to_csv(PATH_HISTORIAL, index=False, sep=';')
    
    stock_inicial = pd.read_csv(PATH_STOCK, sep=';') if os.path.exists(PATH_STOCK) else pd.DataFrame()
    stock_inicial.columns = stock_inicial.columns.str.strip().str.lower()
    
    st.session_state.historial_df = pd.read_csv(PATH_HISTORIAL, sep=';')
    st.session_state.historial_df.columns = st.session_state.historial_df.columns.str.strip().str.lower()
    guardar_y_sanear_stock(stock_inicial)

if 'recovery_dataframe' not in st.session_state:
    st.session_state.recovery_dataframe = st.session_state.stock_df.copy()
if 'ultimo_ticket' not in st.session_state:
    st.session_state.ultimo_ticket = None

# ==========================================
# 5. BARRA LATERAL (UI/UX Limpia por Expanders)
# ==========================================
st.sidebar.title("🛠️ Diesel Messina")

logo_encontrado = None
for posible_nombre in ["logo.png", "logo.png.png", "logo.jpg", "logo.jpeg"]:
    camino_comprobar = os.path.join(DIR_BASE, posible_nombre)
    if os.path.exists(camino_comprobar):
        logo_encontrado = camino_comprobar
        break

if logo_encontrado: 
    st.sidebar.image(logo_encontrado, use_container_width=True)

st.sidebar.write(f"👤 **Usuario:** {st.session_state.usuario_actual.upper()} | 💼 **Rol:** {st.session_state.usuario_rol.upper()}")
if st.sidebar.button("🚪 Cerrar Sesión"): 
    st.session_state.autenticado = False
    st.rerun()
st.sidebar.markdown("---")

# DESPLEGABLE 1: REGISTRAR NUEVO REPUESTO
with st.sidebar.expander("📦 Registrar Nuevo Repuesto", expanded=False):
    add_id = st.number_input("Nuevo ID:", min_value=1, step=1, key="add_id")
    add_nombre = st.text_input("Nombre del Repuesto:", key="add_nombre").strip()
    add_marca = st.text_input("Marca:", key="add_marca").strip()
    add_cat = st.selectbox("Categoría:", CATEGORIAS_DISPONIBLES, key="add_cat")
    add_cant = st.number_input("Stock Inicial:", min_value=0, step=1, key="add_cant")
    add_precio = st.number_input("Precio Unitario ($):", min_value=0.0, step=50.0, key="add_precio")
    add_min = st.number_input("Stock Mínimo Alerta:", min_value=0, step=1, key="add_min")

    if st.button("💾 Guardar en Catálogo", key="btn_save_prod"):
        if add_nombre and add_marca:
            if add_id in st.session_state.stock_df['id'].values: 
                st.error(f"El ID {add_id} ya existe.")
            else:
                nueva_fila = pd.DataFrame([{"id": add_id, "nombre": add_nombre, "marca": add_marca, "categoria": add_cat, "cantidad": add_cant, "precio": add_precio, "stock_minimo": add_min}])
                guardar_y_sanear_stock(pd.concat([st.session_state.stock_df, nueva_fila], ignore_index=True))
                st.success("¡Repuesto agregado!")
                st.rerun()
        else: 
            st.error("Completá Nombre y Marca.")

# DESPLEGABLE 2: MODIFICAR PRODUCTO EXISTENTE
with st.sidebar.expander("✏️ Modificar Repuesto Existente", expanded=False):
    lista_ids_modificar = st.session_state.stock_df['id'].tolist()
    if lista_ids_modificar:
        id_a_modificar = st.selectbox("ID a modificar:", lista_ids_modificar, key="edit_id_select")
        fila_actual = st.session_state.stock_df[st.session_state.stock_df['id'] == id_a_modificar]
        
        edit_nombre = st.text_input("Editar Nombre:", value=str(fila_actual['nombre'].values[0]), key="edit_nombre")
        edit_marca = st.text_input("Editar Marca:", value=str(fila_actual['marca'].values[0]), key="edit_marca")
        try: 
            idx_cat_actual = CATEGORIAS_DISPONIBLES.index(str(fila_actual['categoria'].values[0]))
        except: 
            idx_cat_actual = 0
        edit_cat = st.selectbox("Editar Categoría:", CATEGORIAS_DISPONIBLES, index=idx_cat_actual, key="edit_cat")
        edit_precio = st.number_input("Editar Precio ($):", min_value=0.0, value=float(fila_actual['precio'].values[0]), step=50.0, key="edit_precio")
        edit_min = st.number_input("Editar Stock Mínimo:", min_value=0.0, value=float(fila_actual['stock_minimo'].values[0]), step=1.0, key="edit_min")
        
        if st.button("📝 Actualizar Información", key="btn_update_prod"):
            if edit_nombre and edit_marca:
                st.session_state.stock_df.loc[st.session_state.stock_df['id'] == id_a_modificar, ['nombre', 'marca', 'categoria', 'precio', 'stock_minimo']] = [edit_nombre, edit_marca, edit_cat, edit_precio, edit_min]
                guardar_y_sanear_stock(st.session_state.stock_df)
                st.success("¡Datos actualizados!")
                st.rerun()
            else: 
                st.error("Los campos no pueden quedar vacíos.")
    else: 
        st.info("No hay productos para modificar.")

# DESPLEGABLE 3: REGISTRAR MOVIMIENTO COMERCIAL
with st.sidebar.expander("🛒 Registrar Venta / Compra", expanded=True):
    id_prod = st.number_input("ID del Repuesto", min_value=1, step=1, key="mov_id")
    cantidad = st.number_input("Cantidad", min_value=1, step=1, key="mov_cant")
    tipo_op = st.selectbox("Operación", ["Venta", "Compra"])

    if st.button("Procesar Transacción", key="btn_process_mov"):
        if id_prod in st.session_state.stock_df['id'].values:
            fila_prod = st.session_state.stock_df[st.session_state.stock_df['id'] == id_prod]
            nombre_p, precio_p, marca_p, cat_p = fila_prod['nombre'].values[0], fila_prod['precio'].values[0], fila_prod['marca'].values[0], fila_prod['categoria'].values[0]
            timestamp_str, fecha_str, total_calc = int(datetime.now().timestamp()), datetime.now().strftime("%Y-%m-%d %H:%M"), cantidad * precio_p
            
            if tipo_op == "Venta":
                stock_actual = fila_prod['cantidad'].values[0]
                if stock_actual < cantidad: 
                    st.error(f"Stock insuficiente. Quedan {stock_actual:.0f} un.")
                    st.stop()
                st.session_state.stock_df.loc[st.session_state.stock_df['id'] == id_prod, 'cantidad'] -= cantidad
                prefix, doc_type, t_label = "FAC", "FACTURA DE VENTA DIGITAL", "FACTURA B - CONSUMIDOR FINAL"
            else:
                st.session_state.stock_df.loc[st.session_state.stock_df['id'] == id_prod, 'cantidad'] += cantidad
                prefix, doc_type, t_label = "OC", "ORDEN DE COMPRA / INGRESO", "ORDEN DE COMPRA / REMITO DE INGRESO"
            
            texto_copiara = f"========================================\nDIESEL MESSINA - {doc_type}\n========================================\nNro Registro    : {prefix}-0001-{timestamp_str}\nFecha/Hora      : {fecha_str}\nOperador        : {st.session_state.usuario_actual.upper()}\n----------------------------------------\nDETALLE:\n- Item: {nombre_p} ({marca_p}) [{cat_p}]\n- Cantidad: {cantidad} unidades\n- Unitario: ${precio_p:,.2f}\n----------------------------------------\nTOTAL VALORIZADO : ${total_calc:,.2f}\n========================================"
            st.session_state.ultimo_ticket = {"tipo": t_label, "numero": f"0001-{timestamp_str}", "fecha": fecha_str, "detalle": f"{nombre_p} ({marca_p})", "cantidad": cantidad, "precio_unitario": precio_p, "total": total_calc, "atendio": st.session_state.usuario_actual, "texto_plano": texto_copiara}
            
            guardar_y_sanear_stock(st.session_state.stock_df)
            nuevo_mov = {'fecha': fecha_str, 'id_producto': id_prod, 'tipo': tipo_op, 'cantidad': cantidad, 'usuario': st.session_state.usuario_actual, 'comprobante_texto': texto_copiara}
            st.session_state.historial_df = pd.concat([st.session_state.historial_df, pd.DataFrame([nuevo_mov])], ignore_index=True)
            st.session_state.historial_df.to_csv(PATH_HISTORIAL, index=False, sep=';')
            st.sidebar.success("¡Éxito!")
            st.rerun()
        else: 
            st.error("El ID ingresado no existe.")

# DESPLEGABLE 4: BACKUP RECOVERY (Solo Admin)
if st.session_state.usuario_rol == "admin":
    with st.sidebar.expander("🔄 Respaldo del Sistema", expanded=False):
        if st.button("⏪ Restaurar Catálogo Inicial", key="btn_recovery"):
            guardar_y_sanear_stock(st.session_state.recovery_dataframe.copy())
            st.success("¡Inventario original restaurado!")
            st.rerun()

# ==========================================
# 6. PANTALLA PRINCIPAL INTERACTIVA
# ==========================================
st.title("🛠️ Sistema de Gestión Logística - Diesel Messina")

if st.session_state.ultimo_ticket:
    t = st.session_state.ultimo_ticket
    st.info(f"🧾 Comprobante de Operación Emitido ({t['tipo']}):")
    col_card, col_texto_plano = st.columns(2)
    with col_card:
        with st.container(border=True):
            st.markdown(f"### {t['tipo']}")
            st.write(f"**Nro Comprobante:** {t['numero']} | **Fecha:** {t['fecha']}")
            st.markdown("---")
            st.write(f"**Detalle:** {t['detalle']} x {t['cantidad']} un.")
            st.markdown(f"## TOTAL: ${t['total']:,.2f}")
            st.caption("Diesel Messina - Hurlingham")
    with col_texto_plano:
        st.markdown("**📋 Plantilla de Texto Formal (Copiá y pegá):**")
        st.code(t['texto_plano'], language="text")
    if st.button("Limpiar Vista / Siguiente Operación", key="btn_clean_ticket"): 
        st.session_state.ultimo_ticket = None
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📊 Inventario de Repuestos", "📜 Historial de Auditoría", "⚠️ Alertas Críticas"])

with tab1:
    st.subheader("Filtro de Catálogo")
    filtro_cat = st.selectbox("🔍 Seleccionar Categoría:", ["Todas"] + CATEGORIAS_DISPONIBLES, key="main_filter_cat")
    df_mostrar = st.session_state.stock_df if filtro_cat == "Todas" else st.session_state.stock_df[st.session_state.stock_df['categoria'].astype(str).str.lower() == filtro_cat.lower()]

    def resaltar_bajo_stock(row):
        try: 
            return ['background-color: #ffcccc'] * len(row) if float(row.get('cantidad', 0)) <= float(row.get('stock_minimo', 0)) else [''] * len(row)
        except: 
            return [''] * len(row)

    st.dataframe(
        df_mostrar.style.format({
            "id": "{:.0f}", "cantidad": "{:.0f}", "stock_minimo": "{:.0f}", "precio": "${:,.2f}"
        }).apply(resaltar_bajo_stock, axis=1), 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "id": st.column_config.Column("ID", alignment="center"),
            "nombre": st.column_config.Column("Nombre", alignment="center"),
            "marca": st.column_config.Column("Marca", alignment="center"),
            "categoria": st.column_config.Column("Categoría", alignment="center"),
            "cantidad": st.column_config.Column("Cantidad en Stock", alignment="center"),
            "precio": st.column_config.Column("Precio Unitario", alignment="center"),
            "stock_minimo": st.column_config.Column("Stock Mínimo", alignment="center"),
        }
    )

with tab2:
    st.subheader("Trazabilidad y Auditoría de Operaciones")
    st.dataframe(st.session_state.historial_df.drop(columns=['comprobante_texto'], errors='ignore').tail(15).style.format({"id_producto": "{:.0f}", "cantidad": "{:.0f}"}), use_container_width=True, hide_index=True)
    st.markdown("---")
    if not st.session_state.historial_df.empty:
        opciones_historial = [f"[{row['fecha']}] - Op: {row['tipo']} | ID Repuesto: {row['id_producto']}" for idx, row in st.session_state.historial_df.iterrows()]
        idx_seleccionado = st.selectbox("Elegí una transacción vieja para extraer su ticket original:", range(len(opciones_historial)), format_func=lambda x: opciones_historial[x], key="hist_select_comprobante")
        st.code(st.session_state.historial_df.iloc[idx_seleccionado]['comprobante_texto'], language="text")

with tab3:
    st.subheader("Gatillo Logístico de Órdenes de Reposición")
    hay_alertas = False
    for index, row in st.session_state.stock_df.iterrows():
        try: 
            cant, minimo = float(row.get('cantidad', 0)), float(row.get('stock_minimo', 0))
        except: 
            cant, minimo = 0.0, 0.0
        if cant <= minimo:
            hay_alertas = True
            col_cartel, col_boton = st.columns([3, 1])
            with col_cartel: 
                st.warning(f"🚨 **Stock Crítico:** {str(row.get('nombre', 'Producto')).upper()} ({row.get('marca', '')}) -> Quedan solo {cant:.0f} unidades")
            with col_boton:
                if st.button(f"📝 Orden de Compra ID {row.get('id'):.0f}", key=f"btn_alert_{row.get('id')}"):
                    st.session_state.orden_compra_texto = f"========================================\nORDEN DE PEDIDO DE REPUESTOS - PROVEEDOR\n========================================\nFecha Emisión   : {datetime.now().strftime('%Y-%m-%d')}\nEstablecimiento : Diesel Messina\nItem Solicitado : {row.get('nombre')} ({row.get('marca')})\nCantidad Calculada de Reposición: {(minimo - cant) + 15:.0f} unidades.\n----------------------------------------\nFirma de Autorización: {st.session_state.usuario_actual.upper()}\n========================================"

    if not hay_alertas: 
        st.success("✅ Logística balanceada. Todos los repuestos cuentan con stock seguro.")
    if 'orden_compra_texto' in st.session_state and st.session_state.orden_compra_texto: 
        st.code(st.session_state.orden_compra_texto, language="text")

# ==========================================
# 7. EXCLUSIVO ADMIN: PANEL DE SEGURIDAD MÁXIMA
# ==========================================
if st.session_state.usuario_rol == "admin":
    st.markdown("---")
    st.subheader("🔑 Panel de Control de Seguridad (Solo visible para ADMIN)")
    col_usuarios, col_productos = st.columns(2)
    
    with col_usuarios:
        st.markdown("### 👤 Administración de Personal")
        df_visibilidad = cargar_usuarios()
        st.dataframe(df_visibilidad, use_container_width=True, hide_index=True)
        
        add_u_nom = st.text_input("Nombre de Usuario:", key="new_user_name").strip().lower()
        add_u_pass = st.text_input("Contraseña de Acceso:", type="password", key="new_user_pass")
        add_u_rol = st.selectbox("Rol Jerárquico:", ["user", "admin"], key="new_user_rol")
        
        if st.button("💾 Guardar Usuario Nuevo", key="btn_save_user"):
            if add_u_nom and add_u_pass:
                if add_u_nom in df_visibilidad['usuario'].values: 
                    st.error("El usuario ya existe.")
                else:
                    pd.concat([df_visibilidad, pd.DataFrame([{"usuario": add_u_nom, "clave": add_u_pass, "rol": add_u_rol}])], ignore_index=True).to_csv(PATH_USUARIOS, index=False, sep=';')
                    st.success("¡Usuario dado de alta!")
                    st.rerun()
            else: 
                st.error("Por favor, completá los campos.")
                
        st.markdown("---")
        usuario_a_eliminar = st.selectbox("Seleccionar usuario a dar de baja:", df_visibilidad['usuario'].tolist(), key="del_user_select")
        if st.button("❌ Confirmar Baja de Usuario", key="btn_del_user"):
            if usuario_a_eliminar == st.session_state.usuario_actual: 
                st.error("No podés eliminar tu propia cuenta activa.")
            else:
                df_visibilidad[df_visibilidad['usuario'] != usuario_a_eliminar].to_csv(PATH_USUARIOS, index=False, sep=';')
                st.success("Usuario removido.")
                st.rerun()

    with col_productos:
        st.markdown("### 📦 Depuración del Catálogo de Repuestos")
        lista_ids_eliminar = st.session_state.stock_df['id'].tolist()
        if lista_ids_eliminar:
            id_a_eliminar = st.selectbox("Seleccionar ID del repuesto:", lista_ids_eliminar, key="del_prod_select")
            nombre_prod_del = st.session_state.stock_df[st.session_state.stock_df['id'] == id_a_eliminar]['nombre'].values[0]
            st.warning(f"⚠️ Confirmación requerida: Vas a eliminar de raíz: **{str(nombre_prod_del).upper()}**")
            if st.button("❌ Confirmar Eliminación del Catálogo", key="btn_del_prod"):
                guardar_y_sanear_stock(st.session_state.stock_df[st.session_state.stock_df['id'] != id_a_eliminar])
                st.success("Repuesto removido.")
                st.rerun()
        else: 
            st.info("No hay productos registrados.")
            
        st.markdown("---")
        st.markdown("### 🚨 Zona de Peligro Interno")
        if st.button("🗑️ Vaciar Historial de Pedidos por Completo", key="btn_clear_entire_history"):
            st.session_state.historial_df = pd.DataFrame(columns=['fecha', 'id_producto', 'tipo', 'cantidad', 'usuario', 'comprobante_texto'])
            st.session_state.historial_df.to_csv(PATH_HISTORIAL, index=False, sep=';')
            st.success("¡Historial purgado por completo!")
            st.rerun()
