# Requirements Document

## Introduction

Este documento formaliza las mejoras de calidad, corrección de bugs y deuda técnica
identificadas durante la auditoría del proyecto **aws-cloud-inventory-final**.
El sistema es una aplicación de inventario AWS de solo lectura compuesta por un
backend FastAPI (Python 3.12) con arquitectura hexagonal, un frontend React/TypeScript
y persistencia PostgreSQL desplegados mediante Docker Compose.

Los requisitos se organizan en cinco grupos:

1. Seguridad y configuración
2. Corrección de colectores AWS
3. Rendimiento y gestión de recursos
4. Calidad del código backend
5. Calidad del frontend y documentación

---

## Glossary

- **API**: La aplicación FastAPI que expone los endpoints REST del inventario.
- **CORS_Origins**: Lista de orígenes HTTP permitidos para las peticiones cross-origin hacia la API.
- **ResourceRepository**: Clase de infraestructura que encapsula el acceso a la base de datos PostgreSQL/SQLite.
- **InventoryRunModel**: Modelo SQLAlchemy que representa una ejecución de inventario en la tabla `inventory_runs`.
- **MVPInventoryService**: Servicio de aplicación que orquesta la recolección de recursos AWS entre cuentas y regiones.
- **OrganizationDiscovery**: Clase de infraestructura que descubre cuentas mediante AWS Organizations.
- **AwsSessionFactory**: Fábrica de sesiones boto3 que gestiona credenciales y retries.
- **LambdaCollector**: Colector que enumera funciones AWS Lambda.
- **RDSCollector**: Colector que enumera instancias de Amazon RDS.
- **EBSCollector**: Colector que enumera volúmenes EBS, snapshots y AMIs mediante la API EC2.
- **S3Collector**: Colector que enumera buckets de Amazon S3.
- **ConfigHash**: Función sha256 que calcula el hash de configuración de un recurso a partir de su `raw_data`.
- **BotoConfig**: Objeto `botocore.config.Config` que establece timeouts y reintentos para clientes boto3.
- **RateLimiter**: Mecanismo que controla la tasa de peticiones entrantes a un endpoint.
- **App**: El componente raíz de la aplicación React/TypeScript del frontend.
- **README**: Archivo de documentación raíz del proyecto (`README.md`).

---

## Requirements

### Requisito 1: Restricción de CORS

**User Story:** Como operador de seguridad, quiero que la API solo acepte peticiones
cross-origin desde orígenes explícitamente configurados, para que el frontend no pueda
ser llamado desde dominios arbitrarios.

#### Criterios de Aceptación

1. WHEN la **API** arranca y la variable de entorno `ALLOWED_ORIGINS` no está definida,
   THE **API** SHALL configurar el middleware CORS con la lista por defecto
   `["http://localhost:3000"]`.
2. WHEN la **API** arranca y `ALLOWED_ORIGINS` contiene una cadena que es un array
   JSON válido de orígenes, THE **API** SHALL configurar el middleware CORS con
   exactamente esos orígenes. Un origen válido tiene esquema `http` o `https`, host
   no vacío y longitud máxima de 253 caracteres; las entradas inválidas dentro del
   array se ignoran silenciosamente.
3. IF `ALLOWED_ORIGINS` está vacía, no es parseable como array JSON o no contiene
   ningún origen válido, THEN THE **API** SHALL registrar una advertencia de nivel
   WARNING en el log de arranque y usar la lista por defecto `["http://localhost:3000"]`.
4. WHEN la **API** recibe una petición HTTP cuyo encabezado `Origin` no está en la
   lista de orígenes permitidos, THE **API** SHALL omitir el encabezado
   `Access-Control-Allow-Origin` en la respuesta.

---

### Requisito 2: Ciclo de vida del ResourceRepository

**User Story:** Como desarrollador backend, quiero que el `ResourceRepository` se
instancie una sola vez por ciclo de vida de la aplicación, para evitar la creación
redundante de pools de conexiones en cada petición HTTP.

#### Criterios de Aceptación

1. WHEN la **API** arranca, THE **ResourceRepository** SHALL ser instanciado una
   única vez (incluyendo la llamada a `create_schema()`) mediante el mecanismo
   `lifespan` de FastAPI, antes de que la aplicación acepte peticiones.
2. WHEN múltiples peticiones HTTP concurrentes llegan a la **API**, THE
   **ResourceRepository** SHALL ser el mismo objeto Python para todas las peticiones
   (misma identidad de objeto, verificable con `id()`).
3. WHEN la **API** recibe una petición HTTP, THE `repository()` dependency SHALL
   devolver la instancia singleton creada en el arranque en lugar de construir un
   objeto nuevo.
4. IF la conexión a la base de datos o la creación del esquema falla durante el
   arranque, THEN THE **API** SHALL terminar con código de salida distinto de cero
   e imprimir un mensaje que incluya la razón del fallo antes de aceptar peticiones.
5. WHEN la **API** se detiene (shutdown del lifespan), THE **ResourceRepository**
   SHALL liberar el pool de conexiones de SQLAlchemy llamando a `engine.dispose()`.

---

### Requisito 3: Consultas SQL agregadas en summary y compare_runs

**User Story:** Como administrador de la plataforma, quiero que los endpoints de resumen
y comparación de runs ejecuten agregaciones directamente en la base de datos, para que
el sistema no cargue hasta 100 000 recursos en memoria.

#### Criterios de Aceptación

1. WHEN el endpoint `GET /api/v1/resources/summary` es invocado (con o sin
   `inventory_run_id`), THE **ResourceRepository** SHALL calcular `resource_count`,
   `accounts`, `services`, `regions`, `by_service`, `by_region`, `missing_owner` y
   `missing_environment` mediante sentencias SQL con `GROUP BY` o `COUNT`, sin cargar
   objetos `AWSResource` completos en memoria Python.
2. WHEN el endpoint `GET /api/v1/inventory-runs/{current}/compare/{baseline}` es
   invocado, THE **ResourceRepository** SHALL obtener únicamente las columnas
   `(account_id, resource_type, resource_id, configuration_hash)` para cada run
   mediante una proyección SQL. Las entradas `added` y `removed` en la respuesta
   contienen `(account_id, resource_type, resource_id)`; las entradas `changed`
   contienen adicionalmente `configuration_hash`.
3. THE **ResourceRepository** SHALL eliminar toda llamada a `list_resources()` con
   `limit=100000` dentro de los métodos `summary()` y `compare_runs()`.
4. WHILE la base de datos contiene más de 10 000 recursos para un run dado, THE
   **ResourceRepository** SHALL completar `summary()` sin lanzar `MemoryError` y
   sin cargar simultáneamente todas las filas coincidentes como objetos Python.

---

### Requisito 4: Corrección del bug de creation_time en LambdaCollector

**User Story:** Como operador de inventario, quiero que la fecha de creación de las
funciones Lambda se almacene correctamente, para que los reportes muestren información
fidedigna.

#### Criterios de Aceptación

1. WHEN el **LambdaCollector** recopila una función Lambda cuyo campo `LastModified`
   está presente en la respuesta de la API de Lambda, THE **LambdaCollector** SHALL
   asignar ese valor convertido a `datetime` al atributo `creation_time` del recurso
   resultante (`LastModified` llega como cadena ISO 8601 y debe parsearse al tipo
   `datetime` que espera `AWSResource.creation_time`).
2. WHEN el **LambdaCollector** convierte `LastModified` a `datetime`, THE
   **LambdaCollector** SHALL producir un valor `datetime` con información de timezone
   (timezone-aware).
3. IF `LastModified` no está presente en la respuesta de la API, THEN THE
   **LambdaCollector** SHALL asignar `None` al atributo `creation_time`.

---

### Requisito 5: Eliminación del N+1 en RDSCollector

**User Story:** Como operador de inventario, quiero que el colector RDS recupere las
etiquetas de todas las instancias sin hacer una llamada API separada por cada una,
para reducir la latencia de la recolección y el riesgo de throttling.

#### Criterios de Aceptación

1. WHEN el **RDSCollector** recopila instancias de RDS, THE **RDSCollector** SHALL
   realizar como máximo una llamada a `list_tags_for_resource` por instancia, y solo
   si el campo `TagList` no está embebido en la respuesta de `describe_db_instances`.
   Si `TagList` está presente y vacío, se trata como sin etiquetas (sin llamada
   adicional).
2. WHEN el **RDSCollector** necesita obtener etiquetas y `TagList` no está disponible
   en la respuesta paginada, THE **RDSCollector** SHALL llamar a
   `list_tags_for_resource` con el ARN de cada instancia de forma individual; no se
   asume soporte de consulta multi-ARN ya que la API de RDS no lo ofrece.
3. THE **RDSCollector** SHALL producir el mismo conjunto de pares clave-valor de
   etiquetas por instancia que el comportamiento anterior basado en llamadas
   individuales a `list_tags_for_resource`.

---

### Requisito 6: Coherencia de tipos en OrganizationDiscovery

**User Story:** Como desarrollador backend, quiero que `OrganizationDiscovery` acepte
`AwsSessionFactory` en lugar de `Session`, para que el tipo declarado coincida con el
objeto que realmente recibe en tiempo de ejecución.

#### Criterios de Aceptación

1. THE **OrganizationDiscovery** SHALL declarar el parámetro de su constructor como
   `session_factory: AwsSessionFactory` y almacenarlo en el atributo de instancia
   `_session_factory`.
2. WHEN `OrganizationDiscovery.list_accounts()` o `OrganizationDiscovery.organization_id()`
   son invocados, THE **OrganizationDiscovery** SHALL crear el cliente boto3 llamando
   a `self._session_factory.client("organizations", region="us-east-1")`.
3. THE **MVPInventoryService** SHALL pasar `self.session_factory` al constructor de
   `OrganizationDiscovery` sin envolver ni convertir el objeto en ningún otro tipo
   antes de la llamada.
4. IF al constructor de **OrganizationDiscovery** se le pasa un objeto que no sea
   instancia de `AwsSessionFactory` (ni subclase), THEN THE **OrganizationDiscovery**
   SHALL lanzar `TypeError` sin crear el objeto.

---

### Requisito 7: Eliminación de lógica de negocio duplicada en inventory.py

**User Story:** Como desarrollador backend, quiero que el router de inventario delegue
toda la orquestación al `MVPInventoryService`, para que la lógica de negocio no esté
duplicada entre el router y el servicio.

#### Criterios de Aceptación

1. WHEN el endpoint `POST /api/v1/inventory-runs` lanza la tarea en background, THE
   tarea SHALL delegar la ejecución completa a `MVPInventoryService.run_accounts()`
   en lugar de reimplementar el bucle sobre cuentas y la persistencia.
2. THE router de inventario SHALL eliminar el método privado `_execute()` que está
   definido en el módulo pero nunca referenciado.
3. WHEN `MVPInventoryService.run_accounts()` lanza una excepción no controlada, THE
   tarea en background SHALL actualizar el run con `status="failed"`,
   `finished_at=<ahora UTC>` y `metadata={"error": <mensaje truncado a 500 caracteres>}`.
4. WHEN el endpoint `POST /api/v1/inventory-runs` recibe una petición válida, THE
   **API** SHALL persistir el run con `status="queued"` y retornar inmediatamente
   `{"run_id": <uuid>, "status": "queued"}` con HTTP 200 antes de que la tarea
   en background comience.
5. WHEN la tarea en background comienza su ejecución, THE tarea SHALL actualizar
   el run a `status="running"` antes de invocar `MVPInventoryService.run_accounts()`.

---

### Requisito 8: Paginación completa en list_errors

**User Story:** Como operador de inventario, quiero que el endpoint de errores soporte
desplazamiento (offset), para poder paginar a través de listas de errores largas.

#### Criterios de Aceptación

1. THE **API** endpoint `GET /api/v1/inventory-runs/{run_id}/errors` SHALL aceptar
   los parámetros de consulta `limit` (entero, mínimo 1, máximo 2000, por defecto 500)
   y `offset` (entero, mínimo 0, por defecto 0).
2. IF `limit` o `offset` reciben un valor fuera del rango permitido, THEN THE **API**
   SHALL responder con HTTP 422.
3. THE **ResourceRepository** método `list_errors()` SHALL aceptar el parámetro
   `offset: int = 0` y aplicar el desplazamiento en la consulta SQL.
4. THE **API** endpoint SHALL devolver un objeto con las claves `items`, `total`,
   `limit` y `offset`, donde `total` es el número total de errores para el
   `run_id` dado (sin aplicar paginación).
5. IF `run_id` no existe en la base de datos, THEN THE **API** SHALL responder con
   HTTP 404 y `{"detail": "Inventory run not found"}`.

---

### Requisito 9: Corrección del mapeo run_metadata en InventoryRunModel

**User Story:** Como desarrollador backend, quiero que el campo `metadata` de
`InventoryRunModel` se lea y escriba correctamente, para que los metadatos de cada run
no se pierdan silenciosamente.

#### Criterios de Aceptación

1. WHEN `ResourceRepository.create_run()` recibe un diccionario con la clave
   `"metadata"`, THE **ResourceRepository** SHALL escribir ese valor en la columna
   `metadata` de la tabla `inventory_runs` (atributo ORM `run_metadata`), de forma
   que una lectura posterior con `get_run()` devuelva ese valor bajo la clave
   `"metadata"`.
2. WHEN `ResourceRepository.update_run()` recibe el argumento clave `metadata=<valor>`,
   THE **ResourceRepository** SHALL actualizar el atributo `run_metadata` del modelo
   con ese valor, de forma que una llamada posterior a `get_run()` devuelva el nuevo
   valor bajo la clave `"metadata"`.
3. WHEN `ResourceRepository._run_dict()` serializa un `InventoryRunModel`, THE método
   SHALL leer `row.run_metadata` y exponerlo bajo la clave `"metadata"` en el
   diccionario de salida; si `run_metadata` es `None`, SHALL usar `{}`.
4. IF el diccionario pasado a `create_run()` contiene la clave `"run_metadata"` en
   lugar de `"metadata"`, THEN THE **ResourceRepository** SHALL usar ese valor como
   si la clave fuera `"metadata"`, sin lanzar excepción.
5. IF el diccionario pasado a `create_run()` contiene ambas claves `"metadata"` y
   `"run_metadata"`, THEN THE **ResourceRepository** SHALL dar precedencia al valor
   de `"metadata"`.

---

### Requisito 10: Corrección del service en EBSCollector para AMIs

**User Story:** Como operador de inventario, quiero que las AMIs se clasifiquen bajo
el servicio `"ec2"` en lugar de `"ebs"`, para que los filtros y resúmenes muestren
la taxonomía correcta.

#### Criterios de Aceptación

1. WHEN el **EBSCollector** recopila imágenes AMI mediante `describe_images`, THE
   **EBSCollector** SHALL asignar `service="ec2"` a cada recurso resultante de tipo
   `"ec2:ami"`.
2. THE **EBSCollector** SHALL mantener `service="ebs"` para los recursos de tipo
   `"ebs:volume"` y `"ebs:snapshot"`.
3. WHEN `ResourceRepository.summary()` calcula `by_service`, THE método SHALL
   contabilizar los recursos `"ec2:ami"` bajo la clave `"ec2"`. Si en el mismo run
   existen también volúmenes o snapshots EBS, la clave `"ebs"` SHALL seguir presente
   en `by_service`. El campo `services` SHALL reflejar ambas claves cuando
   corresponda.

---

### Requisito 11: Rate limiting en el endpoint de inventario

**User Story:** Como operador de seguridad, quiero que el endpoint de inicio de
inventario tenga protección ante solicitudes excesivas, para evitar que actores
maliciosos o errores en automatización saturen el sistema.

#### Criterios de Aceptación

1. WHEN el endpoint `POST /api/v1/inventory-runs` recibe peticiones, THE **API** SHALL
   limitar las solicitudes a un máximo configurable por ventana fija de 60 segundos
   por IP de origen. El límite se lee de la variable de entorno `INVENTORY_RATE_LIMIT`
   (entero entre 1 y 10 000, por defecto `10`).
2. WHEN una IP supera el límite configurado dentro de la ventana activa, THE **API**
   SHALL responder con HTTP 429, cuerpo JSON `{"detail": "Too many requests"}` y el
   encabezado `Retry-After` con el número de segundos hasta que la ventana se reinicie.
3. WHEN `INVENTORY_RATE_LIMIT` no está definida, THE **API** SHALL aplicar el límite
   por defecto de 10 peticiones por ventana de 60 segundos.
4. IF `INVENTORY_RATE_LIMIT` contiene un valor no numérico o fuera del rango 1–10 000,
   THEN THE **API** SHALL usar el valor por defecto de 10 y registrar una advertencia
   de nivel WARNING en el log de arranque.

---

### Requisito 12: Hash de configuración canónico

**User Story:** Como desarrollador backend, quiero que `config_hash` use serialización
JSON canónica en lugar de `repr()`, para que hashes de diccionarios con el mismo
contenido sean siempre iguales independientemente del orden de las claves.

#### Criterios de Aceptación

1. WHEN **ConfigHash** recibe un diccionario `raw_data`, THE función SHALL calcular
   el sha256 sobre la serialización JSON del diccionario con claves ordenadas
   (`sort_keys=True`) y un serializador por defecto que convierte valores no
   serializables a cadena, produciendo una cadena hexadecimal de 64 caracteres.
2. WHEN dos diccionarios `a` y `b` contienen las mismas claves y valores (incluyendo
   diccionarios anidados) en cualquier orden, THE **ConfigHash** función SHALL
   producir el mismo hash para ambos.
3. IF **ConfigHash** recibe un diccionario con valores no serializables por JSON
   (p. ej. `datetime`, `set`), THEN THE función SHALL convertirlos a cadena mediante
   `default=str` en lugar de lanzar `TypeError`.
4. FOR ALL pares de diccionarios `a` y `b` donde `a == b`, THE **ConfigHash** función
   SHALL satisfacer `config_hash(a) == config_hash(b)` (propiedad de determinismo).

---

### Requisito 13: Recuperación de etiquetas en S3Collector

**User Story:** Como operador de inventario, quiero que el colector S3 recupere las
etiquetas de cada bucket, para que los campos `owner`, `environment` y `cost_center`
se poblen correctamente en los recursos S3.

#### Criterios de Aceptación

1. WHEN el **S3Collector** recopila un bucket, THE **S3Collector** SHALL llamar a
   `get_bucket_tagging` para ese bucket e incorporar las etiquetas devueltas al
   recurso resultante.
2. IF `get_bucket_tagging` lanza `ClientError` con código `"NoSuchTagSet"`, THEN THE
   **S3Collector** SHALL incluir el bucket en los resultados con `tags={}` y los
   campos semánticos `owner`, `environment` y `cost_center` como `None`, sin propagar
   el error.
3. IF `get_bucket_tagging` lanza `ClientError` con cualquier código distinto de
   `"NoSuchTagSet"`, THEN THE **S3Collector** SHALL registrar el error en el log con
   nivel WARNING e incluir el bucket con `tags={}` y campos semánticos `None`.
4. IF las etiquetas del bucket están disponibles, THEN THE **S3Collector** SHALL
   poblar `owner`, `environment`, `cost_center` y `tags` en el recurso `s3:bucket`
   resultante con los valores correspondientes de las etiquetas AWS.

---

### Requisito 14: Timeouts en clientes boto3

**User Story:** Como operador de la plataforma, quiero que todos los clientes boto3
tengan timeouts de conexión y lectura configurados, para que una región o servicio
AWS lento no bloquee indefinidamente un hilo del inventario.

#### Criterios de Aceptación

1. WHEN **AwsSessionFactory** es instanciado, THE fábrica SHALL leer
   `AWS_CONNECT_TIMEOUT` y `AWS_READ_TIMEOUT` del entorno. Si ambos son enteros
   positivos, SHALL usarlos; en cualquier otro caso SHALL usar los valores por defecto
   (10 segundos y 30 segundos respectivamente) y registrar una advertencia de nivel
   WARNING por cada variable inválida.
2. WHEN `AwsSessionFactory.client()` crea un cliente boto3, THE cliente SHALL tener
   configurados `connect_timeout` y `read_timeout` en su `BotoConfig` con los valores
   determinados en la instanciación de la fábrica.
3. WHEN `AwsSessionFactory.retry_config` es accedido, THE propiedad SHALL devolver
   un objeto `Config` que incluya tanto los parámetros de retry existentes como los
   nuevos `connect_timeout` y `read_timeout`.

---

### Requisito 15: Refactorización del frontend en componentes separados

**User Story:** Como desarrollador frontend, quiero que `main.tsx` esté dividido en
componentes React reutilizables y con manejo de errores adecuado, para facilitar el
mantenimiento y las pruebas unitarias del frontend.

#### Criterios de Aceptación

1. THE **App** SHALL separar la lógica de presentación en al menos los siguientes
   componentes independientes, cada uno definido en su propio archivo dentro de
   `src/components/`: `InventoryLauncher`, `SummaryCards`, `ResourceTable`,
   `RunHistoryTable` y `ResourceFilters`.
2. WHEN cualquier llamada a la API (GET o POST) retorna un error HTTP, THE componente
   que originó la llamada SHALL renderizar un mensaje de error visible dentro de su
   propia sección del DOM que persista hasta que la siguiente llamada tenga éxito o
   el usuario lo descarte.
3. WHEN una consulta a la API está en curso, THE sección correspondiente del DOM SHALL
   contener al menos un elemento renderizado que indique estado de carga.
4. THE **App** SHALL conservar toda la funcionalidad existente: lanzador de inventario,
   historial de runs, filtros (run, servicio, búsqueda libre), tabla de recursos y
   enlaces de exportación CSV/JSON.
5. WHERE TypeScript está habilitado con `strict: true`, THE **App** SHALL compilar
   sin errores de tipo en las interfaces de props de los componentes y en las
   interfaces de respuesta de la API, eliminando el uso de `any`.

---

### Requisito 16: README en español con sección de prerrequisitos

**User Story:** Como nuevo colaborador del equipo, quiero que el README esté en español
y contenga una sección de prerrequisitos detallada, para poder configurar y ejecutar el
proyecto sin necesidad de consultar fuentes externas.

#### Criterios de Aceptación

1. THE **README** SHALL estar completamente redactado en español.
2. THE **README** SHALL incluir una sección `## Prerrequisitos` que liste: Docker ≥ 24
   y Docker Compose v2, AWS CLI v2 con credenciales activas, Python 3.12 (desarrollo
   local), Node.js ≥ 20 (desarrollo local del frontend) y acceso a una cuenta AWS con
   el rol `AWSInventoryReadOnlyRole` y sus políticas de solo lectura.
3. THE **README** SHALL incluir los permisos IAM mínimos para `AWSInventoryReadOnlyRole`
   listando al menos una acción de solo lectura representativa por servicio:
   `ec2:Describe*`, `elasticloadbalancing:Describe*`, `s3:ListAllMyBuckets` +
   `s3:GetBucketTagging`, `rds:Describe*` + `rds:ListTagsForResource`,
   `lambda:ListFunctions`, `iam:ListUsers` + `iam:ListRoles`,
   `ecs:ListClusters` + `ecs:Describe*`, `eks:ListClusters` + `eks:Describe*`,
   `organizations:ListAccounts`.
4. THE **README** SHALL incluir instrucciones de instalación donde cada paso contenga
   el comando exacto a ejecutar, tanto para entorno local (backend con venv, frontend
   con npm, PostgreSQL local) como para Docker Compose.
5. THE **README** SHALL incluir una tabla o lista de variables de entorno donde cada
   entrada especifique: nombre, descripción, valor por defecto y formato/rango
   aceptado. Las variables documentadas SHALL incluir al menos `DATABASE_URL`,
   `ALLOWED_ORIGINS`, `INVENTORY_RATE_LIMIT`, `AWS_CONNECT_TIMEOUT` y
   `AWS_READ_TIMEOUT`.
6. THE **README** SHALL listar todos los endpoints de la API con su método HTTP y
   ruta, y SHALL incluir una sección que describa explícitamente que los colectores
   solo realizan operaciones de lectura y no modifican recursos AWS.
