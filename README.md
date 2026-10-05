# Grupo La Roca — Sistema de inventario y abastecimiento

**Una aplicación web para saber, en cualquier momento, qué productos tiene cada gasolinera,
cuáles se están acabando y qué hay que llevarles.**

![Panel del administrador](docs/capturas/02_panel_general.png)

Proyecto de la materia **Desarrollo de Software Empresarial** — Universidad Don Bosco, 2026.

🌐 **Sistema en línea:** <https://laroca.34-121-143-44.sslip.io> (Google Cloud, con datos ficticios de
demostración; las credenciales se entregan al docente por separado).

---

## 🤔 ¿Qué problema resuelve?

Grupo La Roca tiene varias gasolineras que venden productos como lentes, llaveros,
juguetes, gorras, aceites y aromatizantes. Antes, cuando a una gasolinera se le acababa algo,
el encargado **avisaba por WhatsApp**. Los mensajes se perdían entre conversaciones y era
difícil saber qué llevar a cada sucursal.

Con este sistema:
- Cada encargado **registra sus ventas** y **pide productos** desde la computadora o el celular;
  el inventario se actualiza solo.
- El sistema **avisa solo** cuando un producto se está acabando.
- El administrador ve **en una sola pantalla** qué gasolineras necesitan productos y **cuánto llevar**.
- Cada entrega queda **registrada**, con su historial y reportes.

## ✨ ¿Qué se puede hacer?

| | Función | En palabras simples |
|---|---|---|
| 📊 | **Un panel para cada rol** | El administrador ve un resumen de **todas** las gasolineras (números, gráficos, valor en $, quién no actualiza). El encargado ve **"Mi gasolinera"**: botones grandes y lo que se le está acabando. |
| 📦 | **Inventario por gasolinera** | La lista de productos de cada gasolinera con colores: 🟢 suficiente, 🟠 bajo, 🔴 crítico, y cuánto hay en la bodega central. |
| 🏬 | **Bodega central** | Un panel con lo que hay y lo que conviene comprar. Todos ven cuánto hay; el administrador suma la mercadería que le llega, agrega productos nuevos o corrige después de contar. |
| 🛒 | **Vender** | El encargado registra lo que vende ("5 llaveros") con botones − y +; ve al instante cuánto queda ("hay 20, quedan 15") y, si se acaba, "¡Ya no hay más!". Si no alcanza el stock, una alerta roja lo avisa. |
| 📨 | **Pedir productos** | En una sola pantalla el encargado escribe lo que necesita ("50 llaveros") y lo envía; aparece **"¡Tu pedido se realizó!"**. El administrador lo aprueba y se lo manda. Un pedido enviado no se modifica. |
| ✍️ | **Conteo rápido** | El administrador cuenta y corrige las existencias de una gasolinera en una sola pantalla. |
| 🔔 | **Alertas automáticas** | Si algo baja del mínimo, el administrador recibe un aviso (en el sistema y por correo). |
| 💡 | **Sugerencias** | El sistema calcula cuánto llevar de cada producto a cada gasolinera. |
| 🚚 | **Entregas** | El administrador las prepara en una pantalla (− y +), descarga la hoja en **PDF o Excel** con la gasolinera, el lugar y el pedido, y el encargado confirma lo que recibió. |
| 📄 | **Reportes** | Documentos PDF y gráficos: inventario, productos por acabarse y entregas del mes. |
| 🛍️ | **Catálogo con fotos** | Cada producto con su foto, descripción y precio. |
| 📥 | **Importar desde Excel** | Cargar de una vez los productos y cantidades reales de la empresa. |
| 👤 | **Usuarios** | El administrador crea usuarios, cambia contraseñas, roles y gasolineras, y desactiva cuentas. |

<p>
  <img src="docs/capturas/21_movil_inventario.png" width="230" alt="Inventario en el celular">
  &nbsp;
  <img src="docs/capturas/22_movil_entrega.png" width="230" alt="Recibir una entrega en el celular">
  &nbsp;
  <img src="docs/capturas/20_movil_panel.png" width="230" alt="Panel del encargado en el celular">
</p>

*Así se ve en el celular: inventario con colores, recepción de una entrega y el panel del encargado.*

## 👥 ¿Quién lo usa?

| Persona | Qué hace en el sistema |
|---|---|
| **Encargado de gasolinera** | Ve **solo su gasolinera**. **Vende**, **pide productos**, ve sus alertas y confirma las entregas que recibe. No corrige el stock a mano. |
| **Administrador** | Ve **todas** las gasolineras. Atiende pedidos, revisa alertas y sugerencias, prepara entregas, hace conteos, anula ventas, saca reportes y configura el sistema. |

---

## 💻 Cómo instalarlo en tu computadora (paso a paso)

No hace falta saber programar. Solo hay que seguir los pasos **una vez**.

### Paso 1 — Instalar Docker Desktop
**Docker** es un programa gratuito que "empaqueta" el sistema para que funcione igual en
cualquier computadora, sin instalar nada más.
1. Entrá a <https://www.docker.com/products/docker-desktop/> y descargá la versión para tu
   computadora (Mac o Windows).
2. Instalalo como cualquier programa y **abrilo**. Esperá a que el ícono de la ballena 🐳
   deje de moverse.

### Paso 2 — Tener la carpeta del proyecto
Copiá la carpeta **"Proyecto la roca"** a tu computadora (por ejemplo, al Escritorio).

### Paso 3 — Instalar el sistema (solo la primera vez)
**Opción fácil, con Visual Studio Code:**
1. Abrí Visual Studio Code → **Archivo → Abrir carpeta…** → elegí "Proyecto la roca".
2. Menú **Terminal → Ejecutar tarea…** → **"⚠ Instalar desde cero"** y respondé `s`.

**Opción con la Terminal (Mac):**
1. Abrí la app **Terminal** (`Cmd + Espacio`, escribí "Terminal").
2. Escribí `cd ` (con un espacio), **arrastrá la carpeta del proyecto** a la ventana y presioná Enter.
3. Escribí esto y presioná Enter:
   ```bash
   ./scripts/inicializar.sh
   ```
   Tarda entre 1 y 3 minutos. Al final dice **"Listo"**.

> **Windows:** usá la opción de Visual Studio Code, o abrí **Git Bash** en la carpeta del
> proyecto y escribí el mismo comando.

### Paso 4 — Abrir el sistema
Abrí el navegador (Chrome, Safari, Edge…) en **<http://localhost:8069>**.

---

## 🔑 Cómo entrar (usuarios de prueba)

El sistema trae **datos inventados** para probarlo: 5 gasolineras, 13 productos y estos usuarios.
Todos usan la contraseña de prueba **`LaRoca2026`**.

| Usuario | Persona (inventada) | Qué ve |
|---|---|---|
| `administrador` | Juan Pérez | Todo |
| `encargado.centro` | Carlos López | Solo La Roca Centro |
| `encargado.norte` | María Hernández | Solo La Roca Norte |
| `encargado.sur` | José Ramírez | La Roca Sur y La Roca Oriente |

> ⚠️ Estas contraseñas son **solo para pruebas**. Antes de usarlo con datos reales hay que cambiarlas:
> el administrador lo hace en **Configuración → Usuarios → (usuario) → Cambiar contraseña**.

**Para probarlo en el celular:** conectá el celular a la misma red Wi-Fi que la computadora y
abrí `http://<número-IP-de-la-computadora>:8069`.

## 🔄 Uso diario

| Quiero… | Qué hacer |
|---|---|
| **Encender** el sistema | Abrir Docker Desktop y, en Visual Studio Code, presionar `Cmd + Shift + B` (o en la Terminal: `docker compose up -d`). |
| **Apagarlo** | En Visual Studio Code: Terminal → Ejecutar tarea → **"Detener sistema"** (o `docker compose stop`). |
| **Ver los correos** que envía el sistema | Abrir <http://localhost:8025> (buzón de prueba: los correos no salen a internet). |
| Aprender a **usarlo** | Leer el **[Manual de usuario](docs/MANUAL_USUARIO.md)** (con imágenes). |

**¿Se pierden los datos al apagar?** No. Todo se guarda automáticamente. Solo se borra si
alguien usa a propósito la opción "Instalar desde cero".

## 🆘 ¿Algo no funciona?

| Lo que pasa | Qué hacer |
|---|---|
| "Cannot connect to the Docker daemon" | Docker Desktop no está abierto. Abrilo y esperá a la ballena 🐳. |
| El navegador dice "No se puede acceder al sitio" | Esperá 20 segundos y recargá la página. Si sigue, encendé el sistema (ver "Uso diario"). |
| Usuario o contraseña incorrectos | Revisá la tabla de usuarios. El usuario va en minúsculas y con punto (`encargado.centro`). |
| No veo una gasolinera | El encargado solo ve las suyas. El administrador puede asignarle más. |

---

## 📚 Documentos del proyecto

| Documento | Qué contiene |
|---|---|
| [Manual de usuario](docs/MANUAL_USUARIO.md) | Cómo usar cada pantalla, con imágenes. |
| [Etapa 1](docs/ETAPA_1.md) · [Etapa 2](docs/ETAPA_2.md) · [Etapa 3](docs/ETAPA_3.md) · [Etapa 4](docs/ETAPA_4.md) · [Mejoras](docs/MEJORAS.md) | Qué se construyó en cada fase, explicado en palabras simples. |
| [Guion del video](docs/GUION_VIDEO.md) | Guion del video de demostración (5–7 minutos). |
| [Ejemplos de reportes](docs/ejemplos_reportes/) | PDF de ejemplo que genera el sistema. |
| [Uso de inteligencia artificial](docs/USO_IA.md) | Declaración del uso de IA (lo piden los lineamientos). |
| [Créditos de imágenes](docs/CREDITOS_IMAGENES.md) | Autores y licencias de las fotos del catálogo. |
| [Guía técnica](docs/GUIA_TECNICA.md) | Para programadores: tecnología, código, comandos y pruebas. |
| [Despliegue](DEPLOY.md) | Cómo está publicado en internet y cómo actualizarlo. |

## 📌 Estado del proyecto

| Fase | Estado |
|---|---|
| 1. Base: usuarios, gasolineras, catálogo, inventario | ✅ Terminada |
| 2. Stock mínimo, colores, alertas y sugerencias | ✅ Terminada |
| 3. Entregas desde la bodega e historial | ✅ Terminada |
| 4. Panel general y reportes | ✅ Terminada |
| Mejoras: conteo rápido, fotos, correo, gráficos, Excel, diseño, usuarios, panel por rol, ventas y pedidos | ✅ Terminadas |
| 5. Publicado en internet (Google Cloud) | ✅ <https://laroca.34-121-143-44.sslip.io> |
| Video final | ⏳ Pendiente |

---

**Tecnología:** Odoo 18 Community, Python y PostgreSQL, funcionando con Docker
(detalles en la [guía técnica](docs/GUIA_TECNICA.md)).
**Equipo:** Alan Anderson Vásquez Leiva · Kelly Abigail Vásquez Rodríguez ·
Kennard David Pineda Aguilar · Luis Eduardo Cañas Santos — Docente: Delmy Majano.
