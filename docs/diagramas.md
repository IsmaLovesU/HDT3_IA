# Organización de agentes por arquitectura

Los tres programas usan los mismos especialistas (`agente_faq`, `agente_clima`, `agente_citas`)
y las mismas herramientas (`herramientas/tools.py`). Sólo cambia cómo se conectan.

## 1. Centralizada (`centralizada.py`)

Un supervisor llama a los especialistas como herramientas (`as_tool()`).

```mermaid
flowchart LR
    U([Usuario]) --> S[supervisor_centralizado]
    S -- as_tool: consultar_informacion --> F[agente_faq]
    S -- as_tool: consultar_pronostico --> C[agente_clima]
    S -- as_tool: gestionar_cita --> K[agente_citas]
    F --> T1[(consultar_faq)]
    C --> T2[(consultar_clima)]
    K --> T3[(consultar_clima + agendar_cita)]
```

## 2. Jerárquica (`jerarquica.py`)

Un supervisor general delega en dos gerentes; cada gerente controla a sus especialistas (`as_tool()` en cada nivel).

```mermaid
flowchart TD
    U([Usuario]) --> G[supervisor_general]
    G -- as_tool: gerente_informacion --> GI[gerente_informacion]
    G -- as_tool: gerente_operaciones --> GO[gerente_operaciones]
    GI -- as_tool: buscar_en_faq --> F[agente_faq]
    GO -- as_tool: consultar_pronostico --> C[agente_clima]
    GO -- as_tool: gestionar_cita --> K[agente_citas]
    F --> T1[(consultar_faq)]
    C --> T2[(consultar_clima)]
    K --> T3[(consultar_clima + agendar_cita)]
```

## 3. Descentralizada (`descentralizada.py`)

No hay supervisor. Cada agente transfiere la conversación a otro con `handoff`.

```mermaid
flowchart LR
    U([Usuario]) --> E[agente_entrada]
    E -- handoff --> F[agente_faq]
    E -- handoff --> C[agente_clima]
    E -- handoff --> K[agente_citas]
    K -- handoff --> C
    F -- handoff --> E
    C -- handoff --> K
    C -- handoff --> E
    K -- handoff --> E
```

## Integraciones compartidas

```mermaid
flowchart LR
    F[consultar_faq] --> PG[(PostgreSQL + pgvector)]
    C[consultar_clima] --> OM[[Open-Meteo API]]
    K[agendar_cita] --> C
    K --> JSON[(data/citas.json)]
```

Las tres arquitecturas usan las mismas funciones de `herramientas/integraciones.py`. Para añadir un requerimiento
nuevo basta con crear una herramienta en `herramientas/tools.py` y asignarla a un especialista.
