# Plano de la aplicación

**Estado:** borrador vivo. Se itera hasta tener el plano completo.
**Marcadores:** [DECIDIDO] acordado por el equipo · [PROPUESTA] sugerencia pendiente de validar · [ABIERTO] sin decidir · [PENDIENTE] sección por escribir.

## 1. Visión

Resolvemos el reto de forma general. El reto describe un proceso concreto (pagar o no las facturas de Alberto). Ese proceso tiene tres partes:

1. **Entradas y fuentes de verdad:** PDFs de facturas, el Excel de proveedores y pedidos, y el ERP.
2. **Reglas deterministas** que hay que cumplir: la norma de pagos.
3. **Una decisión final**, en parte subjetiva: PAGAR, NO_PAGAR o ESCALAR.

La aplicación sirve para este proceso y para cualquier otro con la misma forma. El proceso de facturas es la primera instancia, no el producto. [DECIDIDO]

La aplicación mejora con el uso. Cada decisión humana sobre un caso no cubierto por las reglas se convierte en una regla nueva. Así el sistema es cada vez más autónomo y escala menos. [DECIDIDO]

## 2. Conceptos

| Concepto | Qué es | Ejemplo en el reto |
|---|---|---|
| Proceso | Definición completa: fuentes, símbolos, reglas y tipos de decisión | "Pago de facturas" |
| Fuente de verdad | Datos de referencia contra los que se valida | Excel de proveedores y pedidos, ERP |
| Instancia | Cada caso que el proceso decide | Una factura PDF |
| Símbolo | Dato con nombre que usan las reglas | `nif`, `iban`, `pedido`, `importe`, `estado_erp` |
| Regla | Condición determinista sobre símbolos que produce una decisión o un motivo | "IBAN de la factura ≠ IBAN del maestro" |
| Tipo de decisión | Salidas posibles del proceso | PAGAR, NO_PAGAR, ESCALAR |
| Responsable | Persona que decide lo que las reglas no cubren | Manager / Alberto |

## 3. Ciclo de vida de un proceso

### 3.1 Crear el proceso [DECIDIDO]
1. El usuario sube todos los datos relevantes: documentos, hojas de cálculo, acceso a sistemas.
2. Opcionalmente añade texto en lenguaje natural para lo que no esté en los datos.
3. El sistema deriva de todo ello:
   - los **símbolos** necesarios,
   - las **reglas**,
   - los **tipos de decisión**.

### 3.2 Ejecutar
Para cada instancia, el sistema extrae los símbolos, evalúa las reglas y decide. Si ninguna regla resuelve el caso, o una regla dice escalar, la instancia va al responsable. [PENDIENTE: detalle; ver `.artifacts/specs/2026-09-18-reglas-sistema.md` para extracción, ERP y resiliencia]

### 3.3 Escalado asistido [DECIDIDO]
Cuando una instancia se escala, el responsable ve:
- el caso y por qué se escaló,
- **la decisión que tomaría el agente y su razonamiento**,
- **la regla nueva que propone el agente** para resolver solo los casos similares futuros.

El responsable tiene dos opciones:
- **Aceptar:** toma la misma decisión que el agente y añade la regla propuesta.
- **Rechazar:** toma su propia decisión y escribe su propia regla.

En los dos casos entra una regla nueva en el proceso. Por eso el proceso aprende de forma continua.

### 3.4 Autocorrección por revisión [DECIDIDO]
El manager puede revisar cualquier instancia ya decidida, no solo las escaladas. Si encuentra un error, explica por qué ocurrió. El proceso se corrige a sí mismo a partir de esa explicación.
[PROPUESTA] Usar el mismo mecanismo que el escalado: el agente convierte la explicación en un cambio de regla y el manager lo aprueba.

## 4. Preguntas abiertas (con recomendación)

**P1. ¿Qué forma tiene una regla nueva?** [ABIERTO]
Recomendación: el agente propone la regla en dos formas, texto legible y condición estructurada sobre símbolos (por ejemplo, `iva_aplicado = 0.16 → NO_PAGAR`). En ejecución solo se evalúa la forma estructurada, sin LLM. Así la regla es determinista y reproducible. El LLM propone; nunca decide en ejecución.

**P2. ¿Una regla nueva se aplica también al pasado?** [ABIERTO]
Recomendación: antes de activarla, se ejecuta contra todas las instancias ya decididas y se muestra qué decisiones cambiarían. El manager confirma viendo ese impacto. Sirve para detectar reglas demasiado amplias y es barato de hacer.

**P3. ¿Qué pasa si la regla nueva contradice otra?** [ABIERTO]
Recomendación: el sistema detecta el conflicto al proponerla y no la activa hasta que el manager elige cuál gana. Nunca hay dos reglas activas que den decisiones distintas para el mismo caso.

**P4. Tensión con el filtro del reto.** [ABIERTO, crítico]
En la solución de referencia, ESCALAR es una salida correcta. Si el sistema aprende a resolver casos escalados, podría devolver PAGAR donde la referencia espera ESCALAR, y eso descalifica.
Recomendación:
- Separar la **salida del proceso** (lo que dice la norma, incluido ESCALAR) de la **resolución posterior** del responsable.
- `outcomes.jsonl` exporta la salida del proceso con una versión de reglas congelada (norma v3 para el lote 1, v4 para el lote 2).
- Las reglas aprendidas se aplican solo a casos que la norma deja sin definir, nunca por encima de una regla explícita de la norma.

**P5. ¿Quién valida el proceso generado al crearlo?** [ABIERTO]
Recomendación: el usuario revisa los símbolos, las reglas y los tipos de decisión extraídos antes de la primera ejecución. Cada regla muestra de dónde sale (hoja del Excel, frase del texto). Si un error de lectura pasa aquí, se repite en todas las instancias.

**P6. ¿Cómo se representan los símbolos que requieren sistemas externos (ERP)?** [ABIERTO]
Recomendación: cada fuente de verdad es un conector con un contrato fijo (qué símbolos da y cómo falla). El ERP del reto es el primer conector. Esto es lo que permite reutilizar el sistema en otros procesos.

## 5. Secciones por escribir [PENDIENTE]
- Funcionalidades de la primera iteración.
- Arquitectura (componentes, datos, flujo).
- Interfaz del responsable (cola de escalados, revisión, historial de reglas).
- Trazabilidad: qué se guarda de cada decisión y de cada regla.
- Encaje con la rúbrica (ADRs, escalabilidad y coste, resiliencia).
- Relación con los documentos existentes en `.artifacts/`.
