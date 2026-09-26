```markdown
# Ébanon // Motor de Supervivencia

Juego de supervivencia 2D escrito en **Python + Pygame**.  
Incluye mundo procedural, ciclo día/noche, recolección con respawn, crafteo de armas, construcción de refugio y combate contra zombis.

---

## 🚀 Requisitos
- Python 3.12
- Pygame (`pip install pygame`)

---

## ▶️ Ejecución
Clona el repositorio y ejecuta:

```bash
git clone https://github.com/radhanat3031-dot/ebanon
cd ebano-survival
python ebanon.py
```

---

## Controles
- **WASD** → moverse  
- **Mouse** → apuntar (dirección de ataque y construcción)  
- **Espacio / Clic** → atacar / disparar  
- **E** → recolectar / interactuar (recursos, munición, pistola, cofres, puertas)  
- **Q** → abrir mochila (usar comida/vendas, craftear y equipar armas)  
- **TAB** → cambiar arma equipada  
- **B** → menú de construcción (teclas 1–5 para elegir)  
- **Shift** → correr (consume stamina)  
- **Esc** → cerrar menús  

---

## Características
- Mundo procedural con ruido perlin-like.
- Ciclo día/noche con iluminación dinámica (fogatas alumbran).
- Recursos con respawn: madera, piedra, chatarra, comida.
- Sistema de hambre, stamina y salud.
- Crafteo de armas: hacha, pico, bate con clavos.
- Construcción: muros, muros de piedra, puertas, cofres y fogatas.
- Combate cuerpo a cuerpo y a distancia (pistola + munición).
- Zombis con IA básica y anti-tunneling.

---

## Estructura del proyecto
- `ebano_survival.py` → código principal del juego.
- `README.md` → documentación del proyecto.
- `assets/` → sonidos, imágenes y recursos

---

## Contribuciones
Las contribuciones son bienvenidas:
1. Haz un fork del repositorio.
2. Crea una rama (`git checkout -b feature-nueva`).
3. Haz tus cambios y commit (`git commit -m "Agrega nueva característica"`).
4. Haz push a tu rama (`git push origin feature-nueva`).
5. Abre un Pull Request.

---

## Licencia
Este proyecto se distribuye bajo la licencia MIT.  
Puedes usarlo, modificarlo y compartirlo libremente, siempre citando al autor original.
```
