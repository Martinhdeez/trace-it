# Procesos

Cada fichero JSON de esta carpeta define un proceso de decisión completo. trace-it no sabe nada de facturas: el proceso de pago de facturas es solo un fichero más (`pago-facturas.json`).

## Cargar un proceso

```bash
make setup                                                    # carga pago-facturas.json
cd backend && uv run python -m app.cli cargar ../procesos/gastos-viaje.json
cd backend && uv run python -m app.cli cargar ../procesos/pago-facturas.json --compilar  # necesita claves de LLM
```

También desde la API: `POST /procesos/definicion` con el mismo JSON en el cuerpo.

La carga se puede repetir sin miedo:
- el proceso se busca por `nombre`; si no existe, se crea;
- tipos de decisión y símbolos se crean o se actualizan por `nombre`;
- una regla entra como `borrador` solo si el proceso no tiene ya otra con el mismo texto; las reglas existentes (también las activas) no se tocan. Para cambiar una regla, cambia su texto: entra como borrador nuevo;
- los usuarios se crean por `email` si no existen.

`--compilar` compila con los dos agentes cada borrador aún no validado e imprime una línea por regla. Si una falla, sigue con las demás.

## Formato

| Campo | Obligatorio | Qué es |
|---|---|---|
| `nombre` | sí | Nombre único del proceso |
| `descripcion` | no | Texto libre. Los agentes (compilador y asistente) lo reciben como contexto de cada regla: pon aquí las convenciones comunes (normalización, unidades, qué hacer si falta un valor) |
| `tipos_decision` | sí | `[{nombre, prioridad, por_defecto, requiere_persona}]`. Gana la mayor `prioridad` si saltan varias reglas. Exactamente uno `por_defecto` (se aplica si no salta ninguna), y ese no puede `requiere_persona` |
| `simbolos` | no | `[{nombre, tipo, descripcion}]`: los datos que la extracción rellena en cada instancia y que leen las reglas |
| `reglas` | no | `[{texto, tipo, decision}]`. `tipo`: `requisito` (salta si no se cumple) o `prohibicion` (salta si se cumple). `decision`: uno de los `tipos_decision` |
| `usuarios` | no | `[{nombre, email, rol}]`, `rol`: `responsable` u `operador` |

Se rechaza (sin tocar la base de datos) una definición con tipos, símbolos o textos de regla repetidos, sin exactamente un tipo por defecto, o con una regla cuya decisión no existe.

## Ejemplo mínimo: gastos de viaje

`gastos-viaje.json`, otro problema con otras decisiones:

```json
{
  "nombre": "Gastos de viaje",
  "descripcion": "Aprueba o rechaza cada nota de gastos de un viaje de empresa. Convenciones de todas las reglas: importe está en euros y se compara con Decimal(str(importe)); si falta un símbolo que la regla necesita (None), la regla no salta.",
  "tipos_decision": [
    {"nombre": "REVISAR", "prioridad": 3, "requiere_persona": true},
    {"nombre": "RECHAZAR", "prioridad": 2},
    {"nombre": "APROBAR", "prioridad": 1, "por_defecto": true}
  ],
  "simbolos": [
    {"nombre": "empleado", "tipo": "texto", "descripcion": "Email del empleado que viaja."},
    {"nombre": "importe", "tipo": "numero", "descripcion": "Total de la nota en euros."},
    {"nombre": "tiene_ticket", "tipo": "booleano", "descripcion": "La nota adjunta justificante."}
  ],
  "reglas": [
    {"texto": "`tiene_ticket` es verdadero.", "tipo": "requisito", "decision": "RECHAZAR"},
    {"texto": "`importe` es mayor que 500.", "tipo": "prohibicion", "decision": "REVISAR"}
  ]
}
```

Una nota de 800 € sin ticket salta las dos reglas y queda en `REVISAR` (prioridad 3 > 2).
