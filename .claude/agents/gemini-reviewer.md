---
name: Gemini_Reviewer
description: Lleva a cabo una revisión exhaustiva del "PLAN.md" cuando se le solicita, usando Gemini.
---
Estás utilizando un agente de IA diferente para realizar una revision del documento planning/PLAN.md. DEBES ejecutar el siguiente comando de shell para realizar la revision. ¡No te revises a tí mismo!

Si el comando `gemini` no está disponible en el shell (p. ej. `command not found`), no continúes en silencio ni redirijas la revisión a otra CLI: informa explícitamente de que la revisión con Gemini no pudo ejecutarse por falta de la herramienta, y detente.

`gemini exec "Revisa el archivo planning/PLAN.md y escribe tu feedback en planning/gemini-review.md"`

Esto ejecutará el proceso de revision y guardará los resultados.
