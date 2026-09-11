# Home audit — foto diaria de Antena3, laSexta, Telecinco, Cuatro y RTVE.es

Toma una "foto" diaria de las cinco portadas, clasifica sus enlaces (propio /
streaming del grupo página / streaming reproductor autoplay / otras marcas)
y detecta qué vídeos son reproducibles sin salir de la portada. Todo se
acumula en `history.json` y se renderiza en `home-audit-comparativa.html`
(pestaña Resumen = promedio de todas las fotos; una pestaña por canal con
selector de día).

## Puesta en marcha (GitHub Actions)

1. Crea un repo nuevo en GitHub y sube esta carpeta tal cual (incluyendo
   `.github/workflows/daily-snapshot.yml`).
2. En **Settings → Actions → General → Workflow permissions**, marca
   "Read and write permissions" (para que el workflow pueda hacer commit).
3. Ve a la pestaña **Actions**, elige "Daily home audit snapshot" →
   **Run workflow** → marca `force: true` → Run. Esto hace la primera foto
   ya mismo, sin esperar a la hora aleatoria del día. Revisa que
   `history.json` y `home-audit-comparativa.html` se han actualizado y
   commiteado.
4. A partir de ahí, el workflow se dispara solo cada hora en `:07`; el
   script `random_hour_gate.py` decide, mirando la fecha, cuál de esas 24
   ejecuciones es "la foto de hoy" — así cada día cae a una hora distinta
   (0-23 UTC), sin gastar minutos de Action el resto de horas (esos runs se
   paran en el primer paso).
5. Para ver el dashboard: activa GitHub Pages sobre la rama principal (o
   simplemente descarga `home-audit-comparativa.html` y ábrelo local — es
   autocontenido, no necesita servidor).

## Uso local / pruebas

```bash
pip install -r requirements.txt
playwright install chromium

python scrape.py --dry-run     # prueba sin tocar history.json
python scrape.py --force       # toma la foto de hoy aunque ya exista una
python generate_dashboard.py   # sólo regenerar el HTML desde history.json
```

## Cosas a vigilar

- **No he podido ejecutar este scraper contra las webs reales** (mi sandbox
  no tiene salida a internet fuera de una lista corta de dominios). El
  código está revisado y sintácticamente correcto, pero *tienes que hacer
  tú la primera ejecución de prueba* (paso 3 de arriba) antes de fiarte del
  cron diario.
- Los selectores (`sites_config.py` → `CONTAINER_JS`) están basados en la
  estructura de cada web en septiembre de 2026. Si alguna rediseña su home,
  ese sitio empezará a devolver 0 módulos — el workflow no fallará
  ruidosamente por eso, así que conviene revisar `history.json` de vez en
  cuando para confirmar que los 5 canales siguen apareciendo cada día.
- Las reglas de clasificación (qué es "propio", qué cuenta como reproductor
  vs página, qué se excluye por publicidad/afiliación) replican el
  análisis manual que hicimos, pero de forma más genérica/mecánica —
  puede haber pequeñas diferencias con los números exactos vistos en el
  chat. Para el propósito de esto (ver tendencia día a día), es más
  importante la consistencia interna que el calce exacto con el análisis manual.
- El tamaño de cada casilla (héroe/imagen/texto) se infiere automáticamente
  (primer ítem del módulo = héroe, con imagen = medio, sin imagen = texto),
  sin el juicio visual caso por caso que aplicamos a mano.
