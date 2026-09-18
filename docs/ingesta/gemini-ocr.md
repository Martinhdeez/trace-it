# Gemini: comparación sobre los escaneos difíciles

Se ejecutaron peticiones reales con `gemini-3.1-flash-lite`, usando la clave local `GEMINI_API_KEY`. Los cinco PNG completos tienen exactamente el mismo SHA-256 que los usados en el experimento GOT original. No se enviaron etiquetas esperadas, valores del Excel ni respuestas de otros modelos.

## Resultados

| Archivo | Local v1.7.1 | Gemini Flash-Lite | Campos etiquetados |
|---|---:|---:|---:|
| scan_021.pdf | 7 | 8 | 8 |
| scan_022.pdf | 7 | 10 | 10 |
| scan_023.pdf | 8 | 8 | 9 |
| scan_025.pdf | 10 | 10 | 10 |
| scan_026.pdf | 10 | 10 | 10 |
| Total | 42 | 46 | 47 |

GOT sobre páginas completas obtuvo 12/47 con el parser actual; con correcciones y recortes, 29/47. Estas cifras corresponden al conjunto OCR + extracción de campos. Las referencias son transcripciones visuales del asistente sobre casos de desarrollo, pendientes de comprobación humana independiente. No hay `scan_024.pdf` en el lote.

La mejora no equivale a poder aceptar todos los valores:

- En scan_023, Gemini transcribe `B98233411`; la referencia provisional dice `B96233419`.
- Una sexta llamada usando el recorte ya disponible de ese documento produce `B9623341[ILLEGIBLE]`: conserva 8/9 aciertos y se abstiene en el NIF. No permite completar el último dígito.
- Gemini propone `ES1800815290070001234567` para su IBAN, excluido de la referencia por legibilidad insuficiente. Ese candidato no cuenta como acierto.
- En scan_021 no completa el NIF ni el número de factura tapados; tampoco forman parte del denominador.

Las propuestas pasan por el mismo parser y permanecen `UNVERIFIED`. No se ha conectado Gemini como ruta automática de producción ni se ha implementado una regla que elija la lectura correcta usando las etiquetas de evaluación.

### Lectura humana posterior de scan_023

El usuario propone NIF `B96233419` e IBAN `ES18 0081 5290 6700 0123 4567`, indicando expresamente que no están seguros. Se registra como `PROVISIONAL` en la referencia, con texto original y valor normalizado, sin modificar la imagen ni completar candidatos del OCR.

El NIF coincide con la referencia visual provisional anterior. El IBAN discrepa de Gemini: el grupo humano es `6700`, mientras el modelo escribió `0700`. Esa discrepancia sigue pendiente de confirmación; no autoriza a sustituir automáticamente el dígito. El IBAN continúa excluido de la puntuación y la comparación histórica sigue siendo 46/47. Ni el checksum ni los datos del maestro convierten esta lectura incierta en evidencia documental confirmada.

## Tiempo, uso y errores

Las cinco páginas completas tardaron 17,618 s en total; mediana 2,632 s por petición. Consumieron 5.945 tokens de entrada y 1.012 de salida. Con la tarifa estándar publicada de 0,25 USD/M de entrada y 1,50 USD/M de salida, el coste calculado es **0,00300425 USD**. Es una estimación por tokens, no una factura ni una garantía de coste; no incluye intentos fallidos. [Tarifas oficiales](https://ai.google.dev/gemini-api/docs/pricing).

El recorte adicional tardó 1,784 s y consumió 1.182 tokens de entrada y 204 de salida. Coste calculado de las seis llamadas completadas: aproximadamente 0,003606 USD.

Otros modelos aparecían en el catálogo, pero no completaron la primera inferencia: Gemini 3.8 Flash devolvió HTTP 503; Gemini 2.5 Flash, HTTP 404; Gemini 3.1 Pro Preview, HTTP 429. No se reintentaron automáticamente ni se incluyen en el ranking de precisión.

Los identificadores de respuesta, versiones, hashes y métricas están resumidos en [gemini-summary.json](gemini-summary.json). El cliente usa la [API generateContent](https://ai.google.dev/api/generate-content) con imágenes inline; consultar el [catálogo de modelos](https://ai.google.dev/api/models) no garantiza disponibilidad de inferencia.

## Reproducir

Desde `backend/`, con `GEMINI_API_KEY` en el `.env` de la raíz:

```powershell
uv run python -m app.features.ingesta.tools.compare_gemini_ocr --model gemini-3.1-flash-lite --output ../reports/gemini-ocr/flash-lite
uv run python -m app.features.ingesta.tools.compare_gemini_ocr --model gemini-3.1-flash-lite --output ../reports/gemini-ocr/flash-lite --offline
```

El primer comando puede consumir saldo si falta una respuesta en caché. El segundo nunca llama al proveedor. La caché incorpora modelo, prompt, configuración y hashes de imágenes. Cada intento se registra antes de llamar; un timeout o intento incompleto bloquea el reenvío automático para evitar cobros duplicados. `--input-images` admite una carpeta de recortes `archivo.pdf.png`; no se inventan coordenadas PDF para esos recortes.

El siguiente criterio de selección debe ser recuperar campos pendientes sin aceptar dígitos incorrectos: revisión humana de referencias, evaluación sobre los 29 escaneos y casos reservados, comparación por campo y pruebas de abstención. Cinco documentos de desarrollo no justifican sustituir el OCR local en toda la ingesta.
