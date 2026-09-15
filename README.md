# AWS Cloud Inventory

Aplicación de inventario AWS orientada a producción, de solo lectura, con backend FastAPI, dashboard React y persistencia en PostgreSQL.

## Contenido

- Inventario multi-cuenta mediante STS AssumeRole.
- Descubrimiento de regiones habilitadas.
- Diez colectores de solo lectura: EC2, EBS, VPC, S3, RDS, Lambda, IAM, ELBv2, ECS y EKS.
- Aislamiento por cuenta y región, con clasificación de errores AWS.
- Persistencia de ejecuciones e historial de errores.
- Paginación y filtros del lado del servidor.
- Exportación CSV y JSON.
- Resumen del dashboard con métricas de Owner y Environment faltantes.
- API de comparación entre ejecuciones (recursos añadidos, eliminados y modificados).
- Frontend React con lanzador de inventario, historial de runs, filtros y exportación.
- Podman Compose para PostgreSQL, API y frontend.

## Diagrama de arquitectura

![Arquitectura de AWS Cloud Inventory](docs/diagrams/architecture.png)

El diagrama interactivo y su especificación se encuentran en [`docs/diagrams`](docs/diagrams/).

---

## Prerrequisitos

### Para ejecutar con Podman Compose (recomendado)

| Herramienta | Versión mínima | Verificar |
|---|---|---|
| Podman | 4.x | `podman --version` |
| podman-compose | 1.x | `podman-compose --version` |
| AWS CLI | v2 | `aws --version` |
| Credenciales AWS activas | — | `aws sts get-caller-identity` |

> **Nota:** `podman-compose` se instala con `pip install podman-compose` o con el gestor de paquetes del sistema (p. ej. `brew install podman-compose` en macOS).

### Para desarrollo local (sin Podman)

| Herramienta | Versión mínima | Verificar |
|---|---|---|
| Python | 3.12 | `python --version` |
| Node.js | 20 | `node --version` |
| npm | 9 | `npm --version` |
| PostgreSQL | 15 | `psql --version` |

### Credenciales y permisos AWS

La aplicación usa la cadena estándar de credenciales de Boto3 (variables de entorno, `~/.aws/credentials`, perfil de instancia, etc.). No se solicitan credenciales desde la interfaz de usuario.

Para inventario multi-cuenta se recomienda crear el rol `AWSInventoryReadOnlyRole` en cada cuenta destino con las siguientes acciones de solo lectura:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "elasticloadbalancing:Describe*",
        "s3:ListAllMyBuckets",
        "s3:GetBucketTagging",
        "rds:Describe*",
        "rds:ListTagsForResource",
        "lambda:ListFunctions",
        "lambda:GetFunction",
        "iam:ListUsers",
        "iam:ListRoles",
        "ecs:ListClusters",
        "ecs:DescribeClusters",
        "ecs:ListServices",
        "ecs:DescribeServices",
        "eks:ListClusters",
        "eks:DescribeCluster",
        "organizations:ListAccounts",
        "organizations:DescribeOrganization",
        "sts:AssumeRole"
      ],
      "Resource": "*"
    }
  ]
}
```

La política de ejemplo completa está en `deploy/iam/inventory-read-only-policy.json`.

---

## Ejecución con Podman Compose

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd aws-cloud-inventory-final
```

### 2. Configurar variables de entorno (opcional)

```bash
cp .env.example .env
# Editar .env si se necesitan valores distintos a los por defecto
```

### 3. Iniciar todos los servicios

```bash
podman-compose up --build
```

Esto levanta tres servicios:
- **postgres** — PostgreSQL 17 en `localhost:5432`
- **backend** — API FastAPI en `http://localhost:8000`
- **frontend** — Dashboard React en `http://localhost:3000`

### 4. Acceder a la aplicación

| Servicio | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API (documentación interactiva) | http://localhost:8000/docs |
| API (OpenAPI JSON) | http://localhost:8000/openapi.json |
| Health check | http://localhost:8000/health |

### 5. Detener los servicios

```bash
podman-compose down
# Para eliminar también el volumen de PostgreSQL:
podman-compose down -v
```

---

## Desarrollo local (sin Podman)

### Backend

```bash
# 1. Crear y activar el entorno virtual
cd backend
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# 2. Instalar dependencias (incluye herramientas de desarrollo)
pip install -e '.[dev]'

# 3. Configurar variables de entorno
cp ../.env.example .env
# Editar DATABASE_URL para apuntar a un PostgreSQL local o usar SQLite:
# DATABASE_URL=sqlite:///./inventory.db

# 4. Ejecutar el servidor en modo recarga automática
uvicorn main:app --app-dir src --reload
```

El servidor queda disponible en `http://localhost:8000`.

#### Calidad del código (backend)

```bash
# Tests
pytest

# Linting
ruff check .

# Verificación de tipos
mypy src
```

### Frontend

```bash
# 1. Instalar dependencias
cd frontend
npm install

# 2. Configurar la URL de la API (opcional, por defecto apunta a localhost:8000)
echo "VITE_API_URL=http://localhost:8000" > .env.local

# 3. Iniciar servidor de desarrollo
npm run dev
```

El frontend queda disponible en `http://localhost:5173`.

#### Comandos disponibles (frontend)

```bash
npm run dev       # Servidor de desarrollo con hot-reload
npm run build     # Build de producción en dist/
npm run preview   # Preview del build de producción
```

### Base de datos local (PostgreSQL)

Si se prefiere usar PostgreSQL en lugar de SQLite para el desarrollo local:

```bash
# Crear base de datos (asume PostgreSQL corriendo localmente)
createdb aws_inventory

# Configurar la variable en backend/.env
DATABASE_URL=postgresql+psycopg://inventory:inventory@localhost:5432/aws_inventory
```

El esquema se crea automáticamente al arrancar el backend.

---

## Variables de entorno

### Backend

| Variable | Descripción | Por defecto | Formato |
|---|---|---|---|
| `DATABASE_URL` | Cadena de conexión a la base de datos | `sqlite:///./inventory.db` | URL SQLAlchemy |
| `AWS_DEFAULT_REGION` | Región AWS por defecto para clientes boto3 | `us-east-1` | Código de región |
| `AWS_INVENTORY_ROLE_NAME` | Nombre del rol IAM a asumir en cuentas destino | — | Cadena |

### Frontend

| Variable | Descripción | Por defecto |
|---|---|---|
| `VITE_API_URL` | URL base de la API backend | `http://localhost:8000` |

---

## Autenticación AWS

La aplicación nunca solicita claves de acceso desde la interfaz de usuario. Boto3 utiliza la cadena estándar de proveedores de credenciales. Para inventario multi-cuenta, `AwsSessionFactory.assume_role()` asume el rol `AWSInventoryReadOnlyRole` en cada cuenta destino mediante STS.

La interfaz de usuario es agnóstica al proveedor de identidad. Para entornos de producción se recomienda colocar OIDC/RBAC en el ingress o API Gateway.

---

## Límite de solo lectura

Los colectores están definidos de forma explícita y limitada a operaciones de lectura. No se implementa ninguna operación de creación, actualización, eliminación, mutación de etiquetas ni modificación de recursos AWS. Las credenciales de larga duración no se persisten en ningún componente del sistema.

---

## API

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/inventory-runs` | Lanzar nueva ejecución de inventario |
| `GET` | `/api/v1/inventory-runs` | Listar ejecuciones (paginado) |
| `GET` | `/api/v1/inventory-runs/{run_id}` | Detalle de una ejecución |
| `POST` | `/api/v1/inventory-runs/{run_id}/cancel` | Cancelar ejecución en curso |
| `GET` | `/api/v1/inventory-runs/{run_id}/errors` | Errores de una ejecución |
| `GET` | `/api/v1/inventory-runs/{current}/compare/{baseline}` | Comparar dos ejecuciones |
| `GET` | `/api/v1/resources` | Listar recursos (paginado y filtrable) |
| `GET` | `/api/v1/resources/summary` | Resumen agregado de recursos |
| `GET` | `/api/v1/resources/export.csv` | Exportar recursos en CSV |
| `GET` | `/api/v1/resources/export.json` | Exportar recursos en JSON |
| `GET` | `/api/v1/accounts` | Listar cuentas AWS (vía Organizations) |
| `GET` | `/api/v1/regions` | Listar regiones habilitadas |
| `GET` | `/health` | Health check |

La documentación interactiva completa (Swagger UI) está disponible en `http://localhost:8000/docs`.

---

## Uso con Postman

### Configuración inicial

1. Asegurarse de que los servicios estén corriendo (`podman-compose up --build` o el backend local).
2. Crear una nueva colección en Postman llamada `AWS Cloud Inventory`.
3. Definir una variable de colección `base_url` con el valor `http://localhost:8000`.

---

### Flujo típico

#### 1. Verificar que la API está disponible

```
GET {{base_url}}/health
```

Respuesta esperada:
```json
{"status": "ok"}
```

---

#### 2. Lanzar una ejecución de inventario

```
POST {{base_url}}/api/v1/inventory-runs
Content-Type: application/json
```

Body (raw → JSON):
```json
{
  "account_ids": ["123456789012"],
  "regions": ["us-east-1", "eu-west-1"]
}
```

> `regions` es opcional. Si se omite, la API descubre automáticamente todas las regiones habilitadas.

Respuesta:
```json
{
  "run_id": "a1b2c3d4-...",
  "status": "queued"
}
```

Copiar el `run_id` para usarlo en los siguientes pasos.

---

#### 3. Consultar el estado de la ejecución

```
GET {{base_url}}/api/v1/inventory-runs/{{run_id}}
```

El campo `status` puede ser: `queued` → `running` → `completed` | `failed` | `cancelled`.

---

#### 4. Listar los recursos recolectados

```
GET {{base_url}}/api/v1/resources?inventory_run_id={{run_id}}&limit=100&offset=0
```

Parámetros de filtro disponibles:

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `inventory_run_id` | `a1b2c3d4-...` | Filtrar por ejecución |
| `account_id` | `123456789012` | Filtrar por cuenta |
| `region` | `us-east-1` | Filtrar por región |
| `service` | `ec2` | Filtrar por servicio |
| `resource_type` | `ec2:instance` | Filtrar por tipo de recurso |
| `state` | `running` | Filtrar por estado |
| `environment` | `production` | Filtrar por etiqueta Environment |
| `owner` | `equipo-infra` | Filtrar por etiqueta Owner |
| `search` | `web-server` | Búsqueda en nombre, ID o ARN |
| `limit` | `100` | Máximo de resultados (1–1000) |
| `offset` | `0` | Desplazamiento para paginación |

---

#### 5. Ver el resumen del inventario

```
GET {{base_url}}/api/v1/resources/summary?inventory_run_id={{run_id}}
```

Devuelve totales por servicio, región, y métricas de etiquetas faltantes.

---

#### 6. Consultar errores de la ejecución

```
GET {{base_url}}/api/v1/inventory-runs/{{run_id}}/errors?limit=50&offset=0
```

---

#### 7. Comparar dos ejecuciones

```
GET {{base_url}}/api/v1/inventory-runs/{{run_id_actual}}/compare/{{run_id_baseline}}
```

Devuelve listas `added`, `removed` y `changed` con los recursos que cambiaron entre runs.

---

#### 8. Exportar los resultados

Abrir directamente en el navegador o usar Postman con **Send and Download**:

```
GET {{base_url}}/api/v1/resources/export.csv?inventory_run_id={{run_id}}
GET {{base_url}}/api/v1/resources/export.json?inventory_run_id={{run_id}}
```

---

#### 9. Cancelar una ejecución en curso

```
POST {{base_url}}/api/v1/inventory-runs/{{run_id}}/cancel
```

---

### Variables de colección sugeridas en Postman

| Variable | Valor inicial |
|---|---|
| `base_url` | `http://localhost:8000` |
| `run_id` | _(se completa tras el POST de inicio)_ |
| `account_id` | `123456789012` |

---

## Hardening para producción

Para un despliegue productivo en AWS: ejecutar la API detrás de ALB/WAF, usar Secrets Manager para los secretos de la aplicación, aplicar OIDC/RBAC en el edge, usar SQS/EventBridge para tareas asíncronas durables, y desplegar las imágenes en ECS Fargate o EKS. La base de código mantiene esas responsabilidades fuera del dominio y la lógica de colectores, de modo que el adaptador de runtime puede reemplazarse sin modificar el comportamiento del inventario.
# aws-cloud-inventory
